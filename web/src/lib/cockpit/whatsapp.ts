/**
 * Cockpit WhatsApp-ingest data layer (migration 066, docs/BEEPER-ASSISTANT-PLAN.md).
 * READ-ONLY — writes go through scripts/update_wa_item.py via wa-actions.ts.
 */
import { readQuery } from "@/lib/db";

const num = (v: unknown) => Number(v ?? 0) || 0;
const str = (v: unknown) => (v == null ? "" : String(v));

export interface WaTask {
  id: string; title: string; taskType: string; dueAt: string | null;
  contactId: string | null; contactName: string; contactPhone: string; overdue: boolean;
}
export interface WaQuiet {
  chatId: string; title: string; contactId: string | null; contactName: string;
  contactPhone: string; quietDays: number;
}
export interface WaActivityRow {
  id: string; occurredAt: string; direction: string; chatTitle: string; kind: string;
  isGroup: boolean; sender: string; contactId: string | null; contactName: string;
  messageType: string; body: string; rdhCode: string | null;
}
export interface WaGroup {
  chatId: string; title: string; kind: string; ingestEnabled: boolean;
  memberCount: number; rosterMembers: number; matchedMembers: number;
  buildingId: string | null; buildingName: string; lastActivity: string | null;
}
export interface WaConfirmRow {
  phone: string; waName: string; seenCount: number; firstSeenChat: string;
  proposedContactId: string | null; proposedName: string;
}
export interface WaTimelineRow {
  id: string; occurredAt: string; direction: string; channel: string; chatTitle: string;
  isGroup: boolean; sender: string; messageType: string; body: string;
  hasMedia: boolean; rdhCode: string | null;
}

export async function getWaToday(): Promise<{ tasks: WaTask[]; quiet: WaQuiet[] }> {
  const [tasks, quiet] = await Promise.all([
    readQuery(`SELECT id, title, task_type, due_at, contact_id, contact_name, contact_phone, overdue
               FROM vw_wa_today_tasks ORDER BY due_at NULLS LAST LIMIT 50`),
    readQuery(`SELECT beeper_chat_id, title, contact_id, full_name, contact_phone, quiet_days
               FROM vw_wa_gone_quiet ORDER BY quiet_days DESC LIMIT 30`),
  ]);
  return {
    tasks: tasks.map((r) => ({
      id: str(r.id), title: str(r.title), taskType: str(r.task_type),
      dueAt: r.due_at ? str(r.due_at) : null, contactId: r.contact_id ? str(r.contact_id) : null,
      contactName: str(r.contact_name), contactPhone: str(r.contact_phone), overdue: !!r.overdue,
    })),
    quiet: quiet.map((r) => ({
      chatId: str(r.beeper_chat_id), title: str(r.title),
      contactId: r.contact_id ? str(r.contact_id) : null, contactName: str(r.full_name),
      contactPhone: str(r.contact_phone), quietDays: num(r.quiet_days),
    })),
  };
}

export async function getWaActivity(limit = 80): Promise<WaActivityRow[]> {
  const res = await readQuery(
    `SELECT id, occurred_at, direction, chat_title, kind, is_group_msg,
            sender_display_name, contact_id, contact_name, message_type, body, rdh_code
     FROM vw_wa_recent_activity ORDER BY occurred_at DESC LIMIT $1`, [limit]);
  return res.map((r) => ({
    id: str(r.id), occurredAt: str(r.occurred_at), direction: str(r.direction),
    chatTitle: str(r.chat_title), kind: str(r.kind), isGroup: !!r.is_group_msg,
    sender: str(r.sender_display_name), contactId: r.contact_id ? str(r.contact_id) : null,
    contactName: str(r.contact_name), messageType: str(r.message_type),
    body: str(r.body), rdhCode: r.rdh_code ? str(r.rdh_code) : null,
  }));
}

export async function getWaGroups(): Promise<WaGroup[]> {
  const res = await readQuery(
    `SELECT beeper_chat_id, title, kind, ingest_enabled, member_count, roster_members,
            matched_members, building_id, building_name, last_activity
     FROM vw_wa_group_directory ORDER BY last_activity DESC NULLS LAST LIMIT 200`);
  return res.map((r) => ({
    chatId: str(r.beeper_chat_id), title: str(r.title), kind: str(r.kind),
    ingestEnabled: !!r.ingest_enabled, memberCount: num(r.member_count),
    rosterMembers: num(r.roster_members), matchedMembers: num(r.matched_members),
    buildingId: r.building_id ? str(r.building_id) : null,
    buildingName: str(r.building_name),
    lastActivity: r.last_activity ? str(r.last_activity) : null,
  }));
}

export async function getWaConfirmQueue(limit = 60): Promise<WaConfirmRow[]> {
  const res = await readQuery(
    `SELECT phone, wa_name, seen_count, first_seen_chat, proposed_contact_id, proposed_name
     FROM vw_wa_confirm_queue LIMIT $1`, [limit]);
  return res.map((r) => ({
    phone: str(r.phone), waName: str(r.wa_name), seenCount: num(r.seen_count),
    firstSeenChat: str(r.first_seen_chat),
    proposedContactId: r.proposed_contact_id ? str(r.proposed_contact_id) : null,
    proposedName: str(r.proposed_name),
  }));
}

export async function getWaContactTimeline(contactId: string, limit = 60): Promise<WaTimelineRow[]> {
  const res = await readQuery(
    `SELECT id, occurred_at, direction, channel, chat_title, is_group_msg,
            sender_display_name, message_type, body, has_media, rdh_code
     FROM vw_wa_contact_timeline WHERE contact_id = $1
     ORDER BY occurred_at DESC LIMIT $2`, [contactId, limit]);
  return res.map((r) => ({
    id: str(r.id), occurredAt: str(r.occurred_at), direction: str(r.direction),
    channel: str(r.channel), chatTitle: str(r.chat_title), isGroup: !!r.is_group_msg,
    sender: str(r.sender_display_name), messageType: str(r.message_type),
    body: str(r.body), hasMedia: !!r.has_media, rdhCode: r.rdh_code ? str(r.rdh_code) : null,
  }));
}

export interface WaSearchRow {
  id: string; occurredAt: string; direction: string; chatTitle: string; kind: string;
  isGroup: boolean; sender: string; senderPhone: string; contactId: string | null;
  contactName: string; messageType: string; snippet: string;
}

/**
 * Search every ingested message. FTS ('simple' config — Hinglish-safe) OR
 * trigram partial match, so "2bhk andheri" and "kalpat" both work.
 * Filters: kind (chat classification), direction, sinceDays.
 */
export async function searchWaMessages(qtext: string, opts?: {
  kind?: string; direction?: string; sinceDays?: number; limit?: number;
}): Promise<WaSearchRow[]> {
  const query = qtext.trim();
  if (!query) return [];
  const params: unknown[] = [query, `%${query}%`];
  let where = `(i.search_tsv @@ websearch_to_tsquery('simple', $1) OR i.body_text ILIKE $2)`;
  if (opts?.kind) { params.push(opts.kind); where += ` AND w.kind = $${params.length}`; }
  if (opts?.direction) { params.push(opts.direction); where += ` AND i.direction = $${params.length}`; }
  if (opts?.sinceDays) { params.push(opts.sinceDays); where += ` AND i.occurred_at > NOW() - ($${params.length} || ' days')::interval`; }
  params.push(opts?.limit ?? 60);
  const res = await readQuery(
    `SELECT i.id, i.occurred_at, i.direction, COALESCE(w.title,'') AS chat_title,
            COALESCE(w.kind,'') AS kind, i.is_group_msg, i.sender_display_name,
            COALESCE(i.sender_phone,'') AS sender_phone, i.contact_id,
            COALESCE(c.full_name,'') AS contact_name, i.message_type,
            ts_headline('simple', COALESCE(i.body_text,''),
                        websearch_to_tsquery('simple', $1),
                        'StartSel=⟦, StopSel=⟧, MaxWords=40, MinWords=15') AS snippet
     FROM interactions i
     LEFT JOIN wa_chats w ON w.beeper_chat_id = i.beeper_chat_id
     LEFT JOIN contacts c ON c.id = i.contact_id
     WHERE i.source = 'beeper' AND COALESCE(w.ingest_enabled, TRUE) AND ${where}
     ORDER BY i.occurred_at DESC LIMIT $${params.length}`, params);
  return res.map((r) => ({
    id: str(r.id), occurredAt: str(r.occurred_at), direction: str(r.direction),
    chatTitle: str(r.chat_title), kind: str(r.kind), isGroup: !!r.is_group_msg,
    sender: str(r.sender_display_name), senderPhone: str(r.sender_phone),
    contactId: r.contact_id ? str(r.contact_id) : null, contactName: str(r.contact_name),
    messageType: str(r.message_type), snippet: str(r.snippet),
  }));
}

export interface WaOffer {
  id: string; occurredAt: string; transaction: string; bhk: number | null;
  buildingName: string; buildingHit: string; priceText: string; areaText: string;
  furnished: string; locality: string; senderName: string; senderPhone: string;
  chatTitle: string; body: string; contactId: string | null;
}

function mapOffer(r: Record<string, unknown>): WaOffer {
  return {
    id: str(r.id), occurredAt: str(r.occurred_at), transaction: str(r.transaction),
    bhk: r.bhk == null ? null : Number(r.bhk), buildingName: str(r.building_name),
    buildingHit: str(r.building_hit), priceText: str(r.price_text),
    areaText: str(r.area_text), furnished: str(r.furnished), locality: str(r.locality),
    senderName: str(r.sender_name), senderPhone: str(r.sender_phone),
    chatTitle: str(r.chat_title), body: str(r.body),
    contactId: r.contact_id ? str(r.contact_id) : null,
  };
}

/** Offers mentioning OUR buildings (Ekta Tripolis / Imperial Heights / Kalpataru Radiance). */
export async function getOurBuildingOffers(days = 90): Promise<WaOffer[]> {
  const res = await readQuery(
    `SELECT *, NULL AS area_text, NULL AS furnished, NULL AS locality
     FROM vw_wa_offers_our_buildings
     WHERE occurred_at > NOW() - ($1 || ' days')::interval
     ORDER BY occurred_at DESC LIMIT 200`, [days]);
  return res.map(mapOffer);
}

/** The transaction × BHK matrix (rent 2BHK box, sale 3BHK box, …). */
export async function getOfferMatrix(days = 30): Promise<WaOffer[]> {
  const res = await readQuery(
    `SELECT *, NULL AS building_name FROM vw_wa_offers_matrix
     WHERE occurred_at > NOW() - ($1 || ' days')::interval
     ORDER BY occurred_at DESC LIMIT 500`, [days]);
  return res.map(mapOffer);
}

/** wa.me deep link with optional ⌂-code template prefix (send = official WhatsApp only). */
export function waLink(phone: string, text?: string): string {
  const p = phone.replace(/[^\d]/g, "");
  return `https://wa.me/${p}${text ? `?text=${encodeURIComponent(text)}` : ""}`;
}
