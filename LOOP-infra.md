# DLF Email Drip — INFRA LOOP
Track technical setup here. Exit when all gates pass and Wave 1 sends clean.

---

## PHASE 0 — Pre-flight Audit

- [ ] Count sendable emails in DB:
  ```sql
  SELECT COUNT(DISTINCT normalized_value)
  FROM contact_methods
  WHERE method_type='email' AND validation_status='valid';
  ```
- [ ] Count contacts with any email (any status):
  ```sql
  SELECT COUNT(DISTINCT contact_id) FROM contact_methods WHERE method_type='email';
  ```
- [ ] Confirm n8n healthy: `curl http://localhost:5678/healthz`
- [ ] Confirm Resend account exists at resend.com (free, no CC)
- [ ] Add Resend API key to `docker/.env`: `RESEND_API_KEY=re_xxxxxxx`
- [ ] Verify sending domain in Resend (or use `onboarding@resend.dev` for initial test — no DNS needed)

**DONE when:** sendable count known, RESEND_API_KEY in .env.

---

## PHASE 1 — React Email Build

Dependencies already installed (from prior session):
```bash
# in web/
resend @react-email/components react-email
```

Templates written:
- `web/emails/drip-1-variant-a.tsx` ✅
- `web/emails/drip-1-variant-b.tsx` ✅

Test render locally:
```bash
cd /Volumes/RDH\ 5TB/Real\ Deal\ Housing\ OS/web
npx email preview
# → http://localhost:3000
```

Render to HTML for spot-check:
```bash
npx tsx -e "
  import { render } from '@react-email/render';
  import Email from './emails/drip-1-variant-a';
  import fs from 'fs';
  fs.writeFileSync('/tmp/va.html', render(Email({ firstName: 'Test' })));
"
open /tmp/va.html
```

- [ ] Variant A renders without errors
- [ ] Variant B renders without errors
- [ ] No broken layouts in Gmail (use https://www.litmus.com or send to self)

**DONE when:** both variants render clean in browser + Gmail test.

---

## PHASE 2 — DB Schema

One migration needed. Run once:

```sql
-- migration 055: email drip state + unsubscribe token
CREATE TABLE IF NOT EXISTS email_drip_state (
  contact_id    UUID REFERENCES contacts(id),
  template_key  TEXT,                          -- 'drip-1-a', 'drip-1-b', 'drip-2', etc.
  sent_at       TIMESTAMPTZ,
  opened_at     TIMESTAMPTZ,
  clicked_at    TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ,
  resend_id     TEXT,
  PRIMARY KEY (contact_id, template_key)
);

-- HMAC token for unsubscribe links (so users can't guess others' unsubscribe URLs)
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS unsub_token TEXT
  DEFAULT encode(gen_random_bytes(16), 'hex');
```

Apply:
```bash
docker exec -i realdeal-postgres psql -U realdeal_admin -d realdeal_os < schemas/055_email_drip.sql
```

- [ ] Migration applied
- [ ] `email_drip_state` exists
- [ ] `contacts.unsub_token` exists

---

## PHASE 3 — Send Script

Build `scripts/send_email_drip.py`:

```bash
# Dry run — print HTML, don't send
python3 scripts/send_email_drip.py --contact-id <uuid> --template drip-1-a --dry-run

# Real test send (requires RESEND_API_KEY in docker/.env)
python3 scripts/send_email_drip.py --contact-id <uuid> --template drip-1-a --apply
```

Script responsibilities:
1. Fetch contact email from `contact_methods` (status = 'valid' or 'unverified')
2. Check suppression: `email_drip_state.unsubscribed_at IS NULL`
3. Check not already sent: `email_drip_state` no row for (contact_id, template_key)
4. Render template via:
   ```python
   import subprocess, json
   result = subprocess.run(
       ['npx', 'tsx', '-e', f'import Email from "./emails/{tpl}"; import {{ render }} from "@react-email/render"; console.log(render(Email({json.dumps(props)})))'],
       cwd=WEB_DIR, capture_output=True, text=True
   )
   html = result.stdout
   ```
5. Call Resend:
   ```python
   import urllib.request, json
   payload = {"from": "Padmini <padmini@realdealhousing.com>", "to": [email], "subject": subject, "html": html}
   req = urllib.request.Request("https://api.resend.com/emails", json.dumps(payload).encode())
   req.add_header("Authorization", f"Bearer {api_key}")
   req.add_header("Content-Type", "application/json")
   resp = json.loads(urllib.request.urlopen(req).read())
   ```
6. Log to `email_drip_state` and `contact_activity_events`
7. `--dry-run`: print rendered HTML, do NOT call Resend

- [ ] Script written at `scripts/send_email_drip.py`
- [ ] Dry run on contact `hbanthiya@gmail.com` prints correct HTML
- [ ] Real send to `hbanthiya@gmail.com` lands in inbox

---

## PHASE 4 — Unsubscribe Endpoint

Add `web/src/app/unsubscribe/route.ts`:

```typescript
// GET /unsubscribe?contact=<id>&token=<unsub_token>
// Sets contact_methods.validation_status = 'invalid' for all emails on that contact
// Returns a simple "You've been unsubscribed" HTML page
```

Security: verify `token` matches `contacts.unsub_token` before suppressing — prevents CSRF-style attacks.

- [ ] Endpoint written
- [ ] `/unsubscribe?contact=<id>&token=<tok>` → DB update + confirmation page
- [ ] Invalid token → 400 "Link expired or invalid"

---

## PHASE 5 — Test Sends

Send all 4 emails to self before any real contacts:

```bash
# Get your contact ID
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os \
  -c "SELECT id FROM contacts WHERE full_name ILIKE '%harsh%' LIMIT 1;"

python3 scripts/send_email_drip.py --contact-id <your-id> --template drip-1-a --apply
python3 scripts/send_email_drip.py --contact-id <your-id> --template drip-1-b --apply
```

Checklist:
- [ ] Email 1A lands in inbox (not spam)
- [ ] Email 1B lands in inbox (not spam)
- [ ] CTA button links work
- [ ] Unsubscribe link works (and suppresses in DB)
- [ ] `email_drip_state` row exists with `sent_at` + `resend_id`
- [ ] Resend dashboard shows delivery + open tracking
- [ ] Subject line not clipped on mobile (< 50 chars)
- [ ] Images load (or gracefully absent if no CDN yet)

**DONE when:** both variants land in Gmail inbox, all links work, tracking logged.

---

## PHASE 6 — Queue Builder

Build `scripts/email_drip_queue.py`:

```bash
# Show who would receive drip-1-a
python3 scripts/email_drip_queue.py --template drip-1-a --dry-run

# Build queue limited to Kalpataru owners
python3 scripts/email_drip_queue.py --template drip-1-a --segment kalpataru_owners --limit 50 --dry-run
```

Segments:
| Key | SQL |
|-----|-----|
| `kalpataru_owners` | contacts linked to Kalpataru unit via `unit_registration_records` as owner party |
| `kalpataru_tenants` | same but tenant party |
| `brokers` | `contact_type='broker'` or source_file ILIKE '%broker%' |
| `nri` | source_file ILIKE '%international%' OR phone starts 0 (international format) |

- [ ] Script written
- [ ] `--dry-run` returns correct counts per segment
- [ ] No contact without a valid/unverified email in queue
- [ ] No previously-sent contacts in queue

---

## PHASE 7 — Wave 1 Launch

Prerequisites (all must be true before flip):
- [ ] LOOP-content.md Email 1 approved
- [ ] Phase 5 test passes (inbox, links, tracking)
- [ ] Unsubscribe endpoint live
- [ ] RESEND_API_KEY confirmed in .env

Flip:
```sql
UPDATE launch_readiness_checks
SET check_status = 'passed', notes = 'Email pipeline tested 2026-XX-XX'
WHERE check_name = 'email_infrastructure_ready';
```

Wave 1 run:
```bash
python3 scripts/email_drip_queue.py --template drip-1-a \
  --segment kalpataru_owners --limit 50 --apply
```

Monitor (Resend dashboard):
- Delivery rate target: > 95%
- Bounce rate target: < 2%
- Spam complaint target: < 0.08%
- Open rate target (24h): > 20%

- [ ] 50 delivered clean
- [ ] 0 spam complaints
- [ ] Bounce addresses suppressed in DB
- [ ] Metrics in range → expand to full segment

---

## FIX LOG

`[date] issue → fix applied`

---

## LOOP EXIT

Exit when:
- [ ] Email 1 (A or B) delivered to 50 real contacts
- [ ] Delivery > 95%, spam < 0.08%
- [ ] Unsubscribe live and tested
- [ ] `email_drip_state` tracking all sends
- [ ] Day-5 queue (Email 2) ready to run on openers

Until then: fix → re-test Phase 5 → re-check metrics.
