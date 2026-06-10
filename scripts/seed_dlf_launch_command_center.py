#!/usr/bin/env python3
"""Phase 7.0: seed ONE review-gated DLF launch command center workspace (no sends/publishing).

Creates a launch_projects row plus its channels, lead SEGMENTS (counts only — never raw
contacts), readiness gates, operator checklist, a 30-day campaign calendar of PLACEHOLDERS, and
a few campaign_drafts / ai_agent_tasks placeholders. EVERYTHING is send/publish disabled and
review-gated: no WhatsApp/SMS/email/social send, no Wix publish, no external API call, no scrape,
no contact import, no contact create/merge, no inbound lead creation, no raw-contact selection.

Naming guard: the user says "DLF Westend"; public sources may say "DLF The Westpark /
Westpark Phase-I, Andheri West". These are NOT assumed equal — the seed records both, sets
raw_context.name_confirmation_required=true, and adds a BLOCKER readiness check
project_name_confirmed=pending so an operator must confirm before any launch push.

All rows tagged raw_context: phase='7.0', source='dlf_launch_command_center_seed',
send_enabled=false, publish_enabled=false, communication_sent=false, external_calls_made=false.
Dry-run by default; --real-ok required; --apply to write. Prints counts only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.0"
SOURCE = "dlf_launch_command_center_seed"
BASE_TAG = {
    "phase": PHASE, "source": SOURCE,
    "send_enabled": False, "publish_enabled": False,
    "communication_sent": False, "external_calls_made": False,
}

CHANNELS = ["wix", "seo", "blog", "instagram", "youtube_shorts", "whatsapp",
            "email", "phone_call", "referral", "listing_portal"]

SEGMENTS = [
    ("high_budget_buyers", "High-budget buyers", "Buyers with budget fit for a DLF premium launch."),
    ("investor_buyers", "Investor buyers", "Investor-profile buyers seeking appreciation/rental."),
    ("andheri_west_buyers", "Andheri West buyers", "Buyers focused on the Andheri West micro-market."),
    ("nri_buyers", "NRI buyers", "Non-resident buyers (extra consent/compliance care)."),
    ("old_real_estate_contacts_needs_permission_review", "Legacy contacts (permission review)",
     "Older real-estate contacts that REQUIRE a permission/consent review before any outreach."),
    ("owner_network_referrals", "Owner-network referrals", "Referrals via existing owner relationships."),
]

# (check_type, severity, status, summary)
READINESS_CHECKS = [
    ("project_name_confirmed", "blocker", "pending",
     "Confirm 'DLF Westend' vs public 'DLF The Westpark / Westpark Phase-I' before any push."),
    ("rera_checked", "high", "pending", "Confirm/locate the RERA registration for the confirmed project."),
    ("wix_landing_page_ready", "high", "pending", "Landing page built and reviewed (not published)."),
    ("lead_capture_form_ready", "high", "pending", "Lead-capture form wired to inbound intake (no live send)."),
    ("whatsapp_template_approved", "blocker", "pending", "WhatsApp copy approved + template/consent compliant."),
    ("email_template_approved", "high", "pending", "Email copy approved before any send."),
    ("consent_ready", "blocker", "pending", "Consent/permission basis confirmed per segment."),
    ("suppression_checked", "high", "pending", "Suppression list checked before any outreach."),
    ("seo_briefs_ready", "normal", "pending", "SEO briefs drafted and reviewed."),
    ("social_calendar_ready", "normal", "pending", "Social calendar drafted and reviewed."),
    ("n8n_workflow_ready", "normal", "pending", "n8n lead-intake workflow designed (not yet live)."),
]

# (task_type, priority, summary)
OPERATOR_TASKS = [
    ("verify_project_name", "blocker", "Verify the real project name/identity before anything else."),
    ("confirm_rera", "high", "Confirm RERA registration for the verified project."),
    ("build_wix_page", "high", "Build the Wix landing page (draft, do not publish)."),
    ("draft_blog", "normal", "Draft launch blog/SEO content."),
    ("draft_reel", "normal", "Draft reel/short scripts."),
    ("approve_whatsapp_copy", "high", "Review/approve WhatsApp copy (no send)."),
    ("approve_email_copy", "high", "Review/approve email copy (no send)."),
    ("check_permissions", "blocker", "Run permission/consent review for each segment."),
    ("upload_creatives", "normal", "Prepare/upload creatives."),
    ("review_leads", "normal", "Review inbound leads as they arrive (none yet)."),
    ("follow_up_hot_leads", "normal", "Follow up hot leads (manual, post-launch)."),
]

# 30-day calendar rotation: (channel, campaign_type, title) — placeholders only.
CALENDAR_PATTERN = [
    ("instagram", "awareness", "Teaser reel — launch awareness"),
    ("blog", "seo_blog", "SEO blog — area + project overview"),
    ("whatsapp", "lead_capture", "WhatsApp broadcast (draft) — interest capture"),
    ("email", "email_newsletter", "Email newsletter (draft) — launch preview"),
    ("youtube_shorts", "reel", "Short — walkthrough teaser"),
    ("instagram", "story", "Story — countdown"),
    ("wix", "lead_capture", "Landing-page push (draft) — lead form"),
]


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def jsonb_lit(obj) -> str:
    return sql_literal(json.dumps(obj)) + "::jsonb"


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout.strip() or result.stderr.strip())


def tag(extra: dict | None = None) -> str:
    obj = dict(BASE_TAG)
    if extra:
        obj.update(extra)
    return jsonb_lit(obj)


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed a DLF launch command center (review-gated).")
    ap.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    ap.add_argument("--project-display-name", required=True)
    ap.add_argument("--internal-alias", default="")
    ap.add_argument("--expected-launch-month", default="")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-existing", action="store_true")
    args = ap.parse_args()

    if not args.real_ok:
        print("Refusing: --real-ok is required (even for the dry-run plan).")
        return 1

    code, out = run_psql(
        f"SELECT count(*) FROM launch_projects WHERE launch_key = {sql_literal(args.launch_key)};")
    existing = int(out) if (code == 0 and out.isdigit()) else 0
    if existing and not args.allow_existing:
        print(f"Refusing: launch_key {args.launch_key!r} already exists. Use --allow-existing to add another.")
        return 1

    # Planned counts.
    n_channels = len(CHANNELS)
    n_segments = len(SEGMENTS)
    n_checks = len(READINESS_CHECKS)
    n_tasks = len(OPERATOR_TASKS)
    n_calendar = 30
    n_campaign_drafts = 4
    n_ai_tasks = 4

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Phase 7.0 DLF launch command center seed [{mode}] ===")
    print(f"launch_key={args.launch_key}")
    print(f"project_display_name={args.project_display_name}")
    print(f"internal_alias={args.internal_alias or '(none)'}  expected_launch_month={args.expected_launch_month or '(none)'}")
    print("naming: user_supplied='DLF Westend'  possible_public='DLF The Westpark / Westpark Phase-I'  "
          "name_confirmation_required=true")
    print(f"planned: launch_projects=1  channels={n_channels}  lead_segments={n_segments}  "
          f"readiness_checks={n_checks}  operator_tasks={n_tasks}  calendar_placeholders={n_calendar}  "
          f"campaign_drafts={n_campaign_drafts}  ai_agent_tasks={n_ai_tasks}")
    print("send_enabled=0  publish_enabled=0  communication_sent=0  contacts_selected=0  external_calls=0")

    if not args.apply:
        print("DRY-RUN only: no DB writes. Re-run with --apply to seed.")
        return 0

    pid = str(uuid.uuid4())
    today = date.today()
    sql = ["BEGIN;"]

    # launch_projects
    proj_ctx = {
        "name_confirmation_required": True,
        "possible_public_name": "DLF The Westpark / Westpark Phase-I",
        "user_supplied_name": "DLF Westend",
    }
    sql.append(
        "INSERT INTO launch_projects (id, launch_key, project_display_name, internal_alias, "
        "developer_name, area, city, launch_status, expected_launch_month, "
        "rera_verification_status, wix_page_status, seo_status, campaign_status, operator_priority, "
        "notes, raw_context) VALUES ("
        f"{sql_literal(pid)}, {sql_literal(args.launch_key)}, {sql_literal(args.project_display_name)}, "
        f"{sql_literal(args.internal_alias or None)}, 'DLF', 'Andheri West', 'Mumbai', 'planning', "
        f"{sql_literal(args.expected_launch_month or None)}, 'not_started', 'not_started', 'planning', "
        "'planning', 'high', "
        "'Review-gated launch workspace. Confirm project name/RERA before any push. No sends/publishing.', "
        f"{tag(proj_ctx)});")

    # channels
    for ch in CHANNELS:
        sql.append(
            "INSERT INTO launch_channels (launch_project_id, channel, channel_status, send_enabled, "
            "publish_enabled, human_review_required, raw_context) VALUES ("
            f"{sql_literal(pid)}, {sql_literal(ch)}, 'planned', false, false, true, {tag()});")

    # lead segments (counts only; estimates are 0 until a reviewed segmentation exists)
    for key, name, desc in SEGMENTS:
        perm = True
        sql.append(
            "INSERT INTO launch_lead_segments (launch_project_id, segment_key, segment_name, "
            "segment_description, estimated_contact_count, permission_required, whatsapp_allowed_count, "
            "email_allowed_count, suppressed_count, status, raw_context) VALUES ("
            f"{sql_literal(pid)}, {sql_literal(key)}, {sql_literal(name)}, {sql_literal(desc)}, "
            f"0, {str(perm).lower()}, 0, 0, 0, 'draft', {tag()});")

    # readiness checks
    for ctype, sev, status, summary in READINESS_CHECKS:
        sql.append(
            "INSERT INTO launch_readiness_checks (launch_project_id, check_type, check_status, "
            "severity, safe_summary, raw_context) VALUES ("
            f"{sql_literal(pid)}, {sql_literal(ctype)}, {sql_literal(status)}, {sql_literal(sev)}, "
            f"{sql_literal(summary)}, {tag()});")

    # operator tasks
    for ttype, prio, summary in OPERATOR_TASKS:
        sql.append(
            "INSERT INTO launch_operator_tasks (launch_project_id, task_type, task_status, priority, "
            "safe_summary, raw_context) VALUES ("
            f"{sql_literal(pid)}, {sql_literal(ttype)}, 'pending', {sql_literal(prio)}, "
            f"{sql_literal(summary)}, {tag()});")

    # 30-day calendar placeholders (status planned; send/publish disabled; no brief/draft links)
    for i in range(n_calendar):
        d = today + timedelta(days=i)
        ch, ctype, title = CALENDAR_PATTERN[i % len(CALENDAR_PATTERN)]
        sql.append(
            "INSERT INTO launch_campaign_calendar (launch_project_id, planned_date, channel, "
            "campaign_type, title, status, send_enabled, publish_enabled, raw_context) VALUES ("
            f"{sql_literal(pid)}, {sql_literal(d.isoformat())}, {sql_literal(ch)}, {sql_literal(ctype)}, "
            f"{sql_literal(title)}, 'planned', false, false, {tag()});")

    # campaign_drafts placeholders (send disabled, consent required, no message copy)
    drafts = [
        ("DLF launch — WhatsApp awareness (draft)", "awareness", "whatsapp", "high_budget_buyers"),
        ("DLF launch — WhatsApp launch-day (draft)", "launch_day_push", "whatsapp", "andheri_west_buyers"),
        ("DLF launch — Email preview (draft)", "email_newsletter", "email", "investor_buyers"),
        ("DLF launch — Email follow-up (draft)", "follow_up", "email", "nri_buyers"),
    ]
    for name, ctype, ch, seg in drafts:
        sql.append(
            "INSERT INTO campaign_drafts (campaign_name, campaign_type, target_segment, channel, "
            "status, message_template, consent_required, send_enabled, notes, raw_context) VALUES ("
            f"{sql_literal(name)}, {sql_literal(ctype)}, {sql_literal(seg)}, {sql_literal(ch)}, "
            "'draft', NULL, true, false, "
            "'Phase 7.0 placeholder — copy to be drafted/approved; no send.', "
            f"{tag({'launch_key': args.launch_key})});")

    # ai_agent_tasks placeholders (future content/research; human review required, not executed)
    ai_tasks = [
        ("launch_seo_research", "Research SEO keywords/intent for the confirmed DLF project."),
        ("launch_blog_outline", "Draft a launch blog outline (no publish)."),
        ("launch_landing_copy", "Draft Wix landing copy (no publish)."),
        ("launch_reel_script", "Draft reel/short scripts (no publish)."),
    ]
    for ttype, summary in ai_tasks:
        sql.append(
            "INSERT INTO ai_agent_tasks (task_type, entity_type, entity_id, status, priority, "
            "prompt_summary, human_review_required, raw_input) VALUES ("
            f"{sql_literal(ttype)}, 'launch_project', {sql_literal(pid)}, 'pending', 'high', "
            f"{sql_literal(summary)}, true, {tag({'launch_key': args.launch_key})});")

    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"DB write FAILED (rolled back): {out[:300]}")
        return 2
    print(f"APPLIED: launch_project {args.launch_key} seeded (tagged phase=7.0). "
          "send/publish disabled; no contacts selected; no messages sent; no external calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
