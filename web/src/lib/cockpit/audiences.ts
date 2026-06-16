import crypto from "node:crypto";
import { isDbConfigured, readQuery } from "@/lib/db";

export interface AudienceFilters {
  building?: string;
  role?: string;
}

export interface AudienceOption {
  value: string;
  label: string;
}

export interface AudienceSummary {
  attached: number;
  usablePhones: number;
  emails: number;
  metaRows: number;
  suppressed: number;
  whatsappAllowed: number;
}

interface AudienceRawRow {
  contact_id: string;
  phone: string | null;
  email: string | null;
}

const ALLOWED_ROLES = new Set([
  "owner", "tenant", "broker", "agent", "buyer", "seller", "landlord",
  "business_lead", "interested_buyer", "interested_tenant", "unknown",
]);

function cleanFilter(value?: string | null) {
  const v = (value ?? "").trim();
  return v && v !== "all" ? v : undefined;
}

export function parseAudienceFilters(input: { building?: string | null; role?: string | null }): AudienceFilters {
  const building = cleanFilter(input.building);
  const role = cleanFilter(input.role);
  return {
    building,
    role: role && ALLOWED_ROLES.has(role) ? role : undefined,
  };
}

function buildWhere(filters: AudienceFilters) {
  const where = [
    "r.relationship_status = 'active'",
    "coalesce(c.is_test,false) = false",
    `NOT EXISTS (
      SELECT 1 FROM outreach_suppression_list s
      WHERE s.contact_id = c.id AND s.status = 'active'
    )`,
  ];
  const params: string[] = [];
  if (filters.building) {
    params.push(filters.building);
    where.push(`b.name = $${params.length}`);
  }
  if (filters.role) {
    params.push(filters.role);
    where.push(`r.relationship_type = $${params.length}`);
  }
  return { where: where.join(" AND "), params };
}

export function e164Indian(phone: string | null | undefined) {
  let digits = String(phone ?? "").replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (digits.length === 10) digits = `91${digits}`;
  else if (digits.length === 11 && digits.startsWith("0")) digits = `91${digits.slice(1)}`;
  if (digits.length !== 12 || !digits.startsWith("91")) return "";
  return `+${digits}`;
}

function sha256(value: string) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

export function metaCsvFromRows(rows: AudienceRawRow[]) {
  const lines = ["email,phone"];
  for (const row of rows) {
    const email = String(row.email ?? "").trim().toLowerCase();
    const phone = e164Indian(row.phone).replace(/^\+/, "");
    if (!email && !phone) continue;
    lines.push(`${email ? sha256(email) : ""},${phone ? sha256(phone) : ""}`);
  }
  return `${lines.join("\n")}\n`;
}

export async function getAudienceFilterOptions(): Promise<{ buildings: AudienceOption[]; roles: AudienceOption[] }> {
  if (!isDbConfigured()) return { buildings: [], roles: [] };
  const [buildingRows, roleRows] = await Promise.all([
    readQuery<{ name: string }>(
      `SELECT DISTINCT b.name
       FROM contact_property_relationships r
       JOIN buildings b ON b.id = r.building_id
       WHERE r.relationship_status = 'active'
       ORDER BY b.name`
    ),
    readQuery<{ relationship_type: string }>(
      `SELECT DISTINCT relationship_type
       FROM contact_property_relationships
       WHERE relationship_status = 'active'
       ORDER BY relationship_type`
    ),
  ]);
  return {
    buildings: buildingRows.map((r) => ({ value: r.name, label: r.name })),
    roles: roleRows.map((r) => ({ value: r.relationship_type, label: r.relationship_type.replace(/_/g, " ") })),
  };
}

export async function getAudienceSummary(filters: AudienceFilters): Promise<AudienceSummary> {
  if (!isDbConfigured()) return { attached: 0, usablePhones: 0, emails: 0, metaRows: 0, suppressed: 0, whatsappAllowed: 0 };
  const { where, params } = buildWhere(filters);
  const rows = await readQuery<{
    attached: string;
    usable_phones: string;
    emails: string;
    meta_rows: string;
    suppressed: string;
    whatsapp_allowed: string;
  }>(
    `WITH scoped AS (
       SELECT DISTINCT ON (c.id)
         c.id,
         COALESCE((
           SELECT coalesce(nullif(m.normalized_value,''), m.raw_value)
           FROM contact_methods m
           WHERE m.contact_id = c.id AND m.method_type IN ('mobile','phone','whatsapp')
           ORDER BY m.is_primary DESC, (m.method_type='mobile') DESC
           LIMIT 1
         ), '') AS phone,
         COALESCE((
           SELECT coalesce(nullif(m.normalized_value,''), m.raw_value)
           FROM contact_methods m
           WHERE m.contact_id = c.id AND m.method_type = 'email'
           ORDER BY m.is_primary DESC
           LIMIT 1
         ), '') AS email
       FROM contacts c
       JOIN contact_property_relationships r ON r.contact_id = c.id
       LEFT JOIN buildings b ON b.id = r.building_id
       WHERE ${where}
       ORDER BY c.id
     )
     SELECT
       (SELECT count(*) FROM scoped)::text AS attached,
       (SELECT count(*) FROM scoped WHERE regexp_replace(phone, '[^0-9]', '', 'g') <> '')::text AS usable_phones,
       (SELECT count(*) FROM scoped WHERE nullif(email, '') IS NOT NULL)::text AS emails,
       (SELECT count(*) FROM scoped WHERE nullif(phone, '') IS NOT NULL OR nullif(email, '') IS NOT NULL)::text AS meta_rows,
       (SELECT count(DISTINCT s.contact_id)::text FROM outreach_suppression_list s WHERE s.status = 'active') AS suppressed,
       (SELECT count(DISTINCT cp.contact_id)::text FROM channel_permissions cp WHERE cp.channel = 'whatsapp' AND cp.permission_status = 'allowed') AS whatsapp_allowed`,
    params
  );
  const r = rows[0];
  const num = (v: unknown) => Number(v ?? 0) || 0;
  return {
    attached: num(r?.attached),
    usablePhones: num(r?.usable_phones),
    emails: num(r?.emails),
    metaRows: num(r?.meta_rows),
    suppressed: num(r?.suppressed),
    whatsappAllowed: num(r?.whatsapp_allowed),
  };
}

export async function getMetaAudienceRows(filters: AudienceFilters): Promise<AudienceRawRow[]> {
  if (!isDbConfigured()) return [];
  const { where, params } = buildWhere(filters);
  return readQuery<AudienceRawRow>(
    `SELECT DISTINCT ON (c.id)
       c.id::text AS contact_id,
       COALESCE((
         SELECT coalesce(nullif(m.normalized_value,''), m.raw_value)
         FROM contact_methods m
         WHERE m.contact_id = c.id AND m.method_type IN ('mobile','phone','whatsapp')
         ORDER BY m.is_primary DESC, (m.method_type='mobile') DESC
         LIMIT 1
       ), '') AS phone,
       COALESCE((
         SELECT coalesce(nullif(m.normalized_value,''), m.raw_value)
         FROM contact_methods m
         WHERE m.contact_id = c.id AND m.method_type = 'email'
         ORDER BY m.is_primary DESC
         LIMIT 1
       ), '') AS email
     FROM contacts c
     JOIN contact_property_relationships r ON r.contact_id = c.id
     LEFT JOIN buildings b ON b.id = r.building_id
     WHERE ${where}
     ORDER BY c.id`,
    params
  );
}

export function audienceScope(filters: AudienceFilters) {
  const building = filters.building ? filters.building.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") : "all-buildings";
  return filters.role ? `${building}-${filters.role}` : building;
}
