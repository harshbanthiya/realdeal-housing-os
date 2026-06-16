/**
 * Cockpit outreach data layer (Phase 8.0 — Lane A assisted WhatsApp).
 *
 * READ-ONLY: every query runs through db.ts (READ ONLY transaction). All writes
 * go through the guarded Python scripts via server actions in actions.ts.
 *
 * This is the operator's working surface, so the queue getter intentionally
 * returns the REAL resolved message + wa.me link + first name — the director
 * cannot send a WhatsApp without them. It stays behind the cockpit (localhost,
 * the operator's own DB). The activity timeline uses the masked view.
 */
import { isDbConfigured, readQuery } from "@/lib/db";

const live = isDbConfigured;
const num = (v: unknown) => Number(v ?? 0) || 0;

export interface OutreachOverview {
  live: boolean;
  sendEnabled: boolean;
  activeSequences: number;
  directorName: string;
  dailyCap: number;
  sentToday: number;
  pendingToday: number;
  remainingToday: number;
  eligibleOwners: number;
  readyToEnroll: number;
  suppressed: number;
  optedOut: number;
  inCooldown: number;
  whatsappPermissionsAllowed: number;
  optinsRecorded: number;
  tiers: { tier: string; count: number; flagged: number }[];
}

export interface QueueRow {
  queueId: string;
  contactId: string;
  firstName: string;
  status: string;
  step: number;
  message: string;
  waLink: string;       // https://wa.me/<e164>  (client appends ?text=)
  trackedUrl: string | null;
  sentAt: string | null;
}

export interface TimelineRow {
  contactMasked: string;
  channel: string;
  eventType: string;
  direction: string;
  occurredAt: string;
}

export async function getOutreachOverview(): Promise<OutreachOverview> {
  const empty: OutreachOverview = {
    live: false, sendEnabled: false, activeSequences: 0, directorName: "[DIRECTOR_NAME]",
    dailyCap: 10, sentToday: 0, pendingToday: 0, remainingToday: 10,
    eligibleOwners: 0, readyToEnroll: 0, suppressed: 0, optedOut: 0, inCooldown: 0,
    whatsappPermissionsAllowed: 0, optinsRecorded: 0, tiers: [],
  };
  if (!live()) return empty;

  const gate = (await readQuery<{
    send_enabled_setting: string; active_sequences: string;
    whatsapp_permissions_allowed: string; optins_recorded: string;
  }>(`select send_enabled_setting, active_sequences, whatsapp_permissions_allowed, optins_recorded
      from vw_whatsapp_assisted_readiness`))[0];

  const budget = (await readQuery<{ daily_cap: string; sent_today: string; pending_today: string; remaining_today: string }>(
    `select daily_cap, sent_today, pending_today, remaining_today from vw_outreach_daily_send_status`))[0];

  const funnel = (await readQuery<{ eligible: string; ready: string; suppressed: string; opted_out: string; cooldown: string }>(
    `select count(*) eligible,
            count(*) filter (where has_number and not is_suppressed and not is_opted_out and not in_cooldown) ready,
            count(*) filter (where is_suppressed) suppressed,
            count(*) filter (where is_opted_out) opted_out,
            count(*) filter (where in_cooldown) cooldown
     from vw_owner_outreach_eligibility`))[0];

  const director = (await readQuery<{ v: string }>(
    `select setting_value v from outreach_settings where setting_key='director_display_name'`))[0]?.v ?? "[DIRECTOR_NAME]";

  const tiers = await readQuery<{ engagement_tier: string; n: string; flagged: string }>(
    `select engagement_tier, count(*) n, count(*) filter (where do_not_spam_flag) flagged
     from vw_contact_engagement_score group by engagement_tier order by 1`);

  return {
    live: true,
    sendEnabled: gate?.send_enabled_setting === "true",
    activeSequences: num(gate?.active_sequences),
    directorName: director,
    dailyCap: num(budget?.daily_cap),
    sentToday: num(budget?.sent_today),
    pendingToday: num(budget?.pending_today),
    remainingToday: num(budget?.remaining_today),
    eligibleOwners: num(funnel?.eligible),
    readyToEnroll: num(funnel?.ready),
    suppressed: num(funnel?.suppressed),
    optedOut: num(funnel?.opted_out),
    inCooldown: num(funnel?.cooldown),
    whatsappPermissionsAllowed: num(gate?.whatsapp_permissions_allowed),
    optinsRecorded: num(gate?.optins_recorded),
    tiers: tiers.map((t) => ({ tier: t.engagement_tier, count: num(t.n), flagged: num(t.flagged) })),
  };
}

export async function getOutreachQueue(): Promise<QueueRow[]> {
  if (!live()) return [];
  const rows = await readQuery<{
    queue_id: string; contact_id: string; full_name: string; status: string;
    sequence_step: string; drafted_message: string; wa_link: string;
    tracked_url: string | null; sent_at: string | null;
  }>(
    `select q.id::text queue_id, q.contact_id::text, c.full_name, q.status,
            q.sequence_step, q.drafted_message, q.wa_link,
            (select setting_value from outreach_settings where setting_key='tracked_link_base_url') || l.token tracked_url,
            q.sent_at::text sent_at
     from whatsapp_assisted_queue q
     join contacts c on c.id = q.contact_id
     left join outreach_tracked_links l on l.id = q.tracked_link_id
     where q.queued_for_date = current_date
     order by case q.status when 'pending' then 0 when 'sent_by_human' then 1
                            when 'replied' then 2 else 3 end, q.created_at`);
  return rows.map((r) => ({
    queueId: r.queue_id,
    contactId: r.contact_id,
    firstName: (r.full_name || "").trim().split(/\s+/)[0] || "Contact",
    status: r.status,
    step: num(r.sequence_step),
    message: r.drafted_message,
    waLink: r.wa_link,
    trackedUrl: r.tracked_url,
    sentAt: r.sent_at,
  }));
}

export interface ContactGroup {
  groupId: string;
  slug: string;
  name: string;
  groupType: string;
  description: string | null;
  memberCount: number;
  reachableCount: number;
  suppressedCount: number;
}

export async function getContactGroups(): Promise<ContactGroup[]> {
  if (!live()) return [];
  const rows = await readQuery<{
    group_id: string; slug: string; name: string; group_type: string;
    description: string | null; member_count: string; reachable_count: string; suppressed_count: string;
  }>(`select group_id, slug, name, group_type, description, member_count, reachable_count, suppressed_count
      from vw_contact_group_summary`);
  return rows.map((r) => ({
    groupId: r.group_id, slug: r.slug, name: r.name, groupType: r.group_type,
    description: r.description, memberCount: num(r.member_count),
    reachableCount: num(r.reachable_count), suppressedCount: num(r.suppressed_count),
  }));
}

export interface ContactActivity {
  tier: string;
  outbound: number;
  opens: number;
  replies: number;
  optins: number;
  optouts: number;
  doNotSpam: boolean;
  events: { channel: string; eventType: string; direction: string; occurredAt: string; summary: string }[];
  queue: { queueId: string; status: string; step: number } | null;
}

export async function getContactActivity(contactId: string): Promise<ContactActivity> {
  const empty: ContactActivity = {
    tier: "untouched", outbound: 0, opens: 0, replies: 0, optins: 0, optouts: 0,
    doNotSpam: false, events: [], queue: null,
  };
  if (!live() || !/^[0-9a-f-]{36}$/i.test(contactId)) return empty;

  const score = (await readQuery<{
    engagement_tier: string; outbound_count: string; open_count: string;
    reply_count: string; optin_count: string; optout_count: string; do_not_spam_flag: boolean;
  }>(`select engagement_tier, outbound_count, open_count, reply_count, optin_count, optout_count, do_not_spam_flag
      from vw_contact_engagement_score where contact_id = $1`, [contactId]))[0];

  const events = await readQuery<{ channel: string; event_type: string; direction: string; occurred_at: string; summary: string }>(
    `select channel, event_type, direction, occurred_at::text, coalesce(safe_summary,'') summary
       from contact_activity_events where contact_id = $1
     union all
     select channel, 'interaction', direction, occurred_at::text, coalesce(summary,'')
       from interactions where contact_id = $1
     order by occurred_at desc limit 30`, [contactId]);

  const q = (await readQuery<{ id: string; status: string; sequence_step: string }>(
    `select id::text, status, sequence_step from whatsapp_assisted_queue
      where contact_id = $1 and queued_for_date = current_date order by created_at desc limit 1`, [contactId]))[0];

  return {
    tier: score?.engagement_tier ?? "untouched",
    outbound: num(score?.outbound_count),
    opens: num(score?.open_count),
    replies: num(score?.reply_count),
    optins: num(score?.optin_count),
    optouts: num(score?.optout_count),
    doNotSpam: Boolean(score?.do_not_spam_flag),
    events: events.map((e) => ({
      channel: e.channel, eventType: e.event_type, direction: e.direction,
      occurredAt: e.occurred_at, summary: e.summary,
    })),
    queue: q ? { queueId: q.id, status: q.status, step: num(q.sequence_step) } : null,
  };
}

export async function getActivityTimeline(limit = 12): Promise<TimelineRow[]> {
  if (!live()) return [];
  const rows = await readQuery<{
    contact_masked: string; channel: string; event_type: string; direction: string; occurred_at: string;
  }>(
    `select contact_masked, channel, event_type, direction, occurred_at::text
     from vw_contact_activity_timeline limit $1`, [limit]);
  return rows.map((r) => ({
    contactMasked: r.contact_masked, channel: r.channel, eventType: r.event_type,
    direction: r.direction, occurredAt: r.occurred_at,
  }));
}
