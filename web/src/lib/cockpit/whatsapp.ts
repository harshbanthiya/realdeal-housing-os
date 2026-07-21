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

/** wa.me deep link with optional ⌂-code template prefix (send = official WhatsApp only). */
export function waLink(phone: string, text?: string): string {
  const p = phone.replace(/[^\d]/g, "");
  return `https://wa.me/${p}${text ? `?text=${encodeURIComponent(text)}` : ""}`;
}
