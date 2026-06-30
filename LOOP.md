# DLF Westpark Email Drip — Audit → Build → Test → Fix Loop

Run this loop until every gate passes. Each phase has a DONE condition.
Repeat the Test → Fix cycle until Test passes clean before moving to Launch.

---

## PHASE 0 — Pre-flight Audit
**Goal:** Know what we're working with before touching anything.

- [ ] Count sendable emails: `SELECT COUNT(DISTINCT normalized_value) FROM contact_methods WHERE method_type='email' AND validation_status='valid'`
- [ ] Verify no duplicate emails per contact (same email on 2+ contacts)
- [ ] Confirm n8n is reachable: `curl http://localhost:5678/healthz`
- [ ] Confirm Resend account created at resend.com (free, no CC)
- [ ] Confirm Resend API key added to `docker/.env` as `RESEND_API_KEY`
- [ ] Confirm sending domain verified in Resend (or use `onboarding@resend.dev` for test)
- [ ] Confirm unsubscribe mechanism: updating `contact_methods.validation_status='invalid'` blocks future sends
- [ ] Read existing email template bodies from DB — note all `[VERIFY]` placeholders still present

**DONE when:** sendable count confirmed, Resend key in .env, n8n healthy, placeholders listed.

---

## PHASE 1 — Content: Fill the Templates
**Goal:** Replace every `[VERIFY]` placeholder with real copy. No send until this is clean.

### The 4-Email Drip Sequence

**Email 1 — Awareness (Day 0): "DLF's first Mumbai project — here's what we know"**
- Hook: DLF built Delhi's Cyber City, Gurgaon's DLF Avenue, made early investors 8-12x. Now Mumbai.
- Content: What is DLF Westpark. Andheri West location. Why this matters.
- CTA: "Get the project brief" → link to Wix landing page
- Tone: exclusive early look, not a sales pitch
- Subject line options:
  - "DLF just entered Mumbai — and we have early access"
  - "The name behind DLF City, now in Andheri West"

**Email 2 — Consideration (Day 5): "DLF Westpark: the numbers"**
- Hook: Andheri West micro-market analysis. What's happening to prices.
- Content: Project specs (RERA number, wings, carpet area ranges, price per sqft estimate)
- CTA: "Request the brochure" → WhatsApp deep link or form
- Tone: analyst, data-first

**Email 3 — Conversion (Day 12): "Site visit — limited slots"**
- Hook: urgency without fake scarcity — pre-launch pricing closes on possession booking
- Content: what a site visit includes, what questions to ask DLF
- CTA: "Book a slot" → calendar link or WhatsApp
- Tone: concise, action-focused

**Email 4 — Referral (Day 20): "Know someone who'd want to know?"**
- Hook: if this isn't right for you, it might be right for someone you know
- Content: one-line project summary, forwarding ask
- CTA: "Forward this email" or "Share on WhatsApp"
- Tone: warm, low-pressure

### Placeholder Resolution Checklist
- [ ] `[RERA_VERIFY]` → insert real RERA number from Phase 6.9 (P51800XXXXXX for DLF)
- [ ] `[PRICE_VERIFY]` → insert price range (confirm with DLF or use public listing data)
- [ ] `[BROCHURE_LINK_PENDING]` → Wix page URL or PDF link
- [ ] `[WIX_PAGE_PENDING]` → Wix staging URL from Phase 7.22
- [ ] Update `launch_message_templates.body` + `subject` + `cta` for all 4 email rows
- [ ] Update `launch_message_templates.template_status = 'ready'` when each is done

**DONE when:** all 4 templates have no `[VERIFY]` placeholders and status='ready'.

---

## PHASE 2 — Design: React Email Templates
**Goal:** HTML emails that look like the Gallery White site. Render in Outlook + Gmail.

### Design Language (match globals.css)
```
Background:  #ffffff
Primary text: #1a1a1a  (--color-ink)
Header bg:   #1f3d4d  (--color-teal)
Header text: #ffffff
Accent:      #b6862c  (--color-amber)  ← use for CTA buttons
Muted bg:    #eef1ef  (--color-mist)
Font:        Georgia for headings (email-safe serif), Arial/sans for body
Max width:   600px
```

### Files to create
- [ ] `web/emails/layout.tsx` — shared wrapper: logo, header bar (teal), footer (unsubscribe link, address)
- [ ] `web/emails/drip-1-awareness.tsx` — Email 1 template
- [ ] `web/emails/drip-2-consideration.tsx` — Email 2 template
- [ ] `web/emails/drip-3-conversion.tsx` — Email 3 template
- [ ] `web/emails/drip-4-referral.tsx` — Email 4 template
- [ ] `web/emails/preview.ts` — renders all 4 to `/tmp/email-previews/` as HTML for visual check

### Install
```bash
cd web && npm install resend @react-email/components
```

**DONE when:** `node web/emails/preview.ts` produces 4 HTML files that look correct in browser.

---

## PHASE 3 — Infrastructure: Send Pipeline
**Goal:** A script that can send one email to one contact. No bulk until this works.

### Architecture
```
contacts DB
    ↓ (query valid emails + consent)
scripts/send_email_drip.py
    ↓ (render template via node/react-email)
Resend API
    ↓ (webhook on open/click)
contact_activity_events (tracking)
    ↓
n8n workflow (optional: advance drip stage on open)
```

### Scripts to build
- [ ] `scripts/send_email_drip.py --contact-id <uuid> --template drip-1 --dry-run`
  - Fetches contact email from contact_methods
  - Checks suppression (validation_status != 'invalid')
  - Renders template (shell out to `node -e "require('./web/emails/drip-1').render(data)"`)
  - Calls Resend API
  - Logs to contact_activity_events (event_type='email_sent', metadata={template, subject})
  - `--dry-run` prints rendered HTML, does not send
- [ ] `scripts/email_drip_queue.py` — builds send queue from contacts with email, no prior send for this template, not suppressed
- [ ] Unsubscribe endpoint: `web/src/app/unsubscribe/route.ts` — takes `?contact=<id>&sig=<hmac>` → sets validation_status='invalid', shows confirmation page

### DB additions needed (one migration)
```sql
-- Track drip state per contact
CREATE TABLE email_drip_state (
  contact_id UUID REFERENCES contacts(id),
  template_key TEXT,
  sent_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ,
  resend_id TEXT,
  PRIMARY KEY (contact_id, template_key)
);
```

**DONE when:** `--dry-run` on 1 contact prints correct HTML with real name + email, no placeholders.

---

## PHASE 4 — Test Send
**Goal:** Send all 4 emails to yourself (and optionally Padmini Jain) before any real contacts.

- [ ] Send drip-1 to `hbanthiya@gmail.com` — check inbox, spam folder, mobile render
- [ ] Send drip-1 to Padmini Jain test number's email — verify
- [ ] Check: subject line not clipped on mobile (< 50 chars)
- [ ] Check: CTA button renders and link works
- [ ] Check: unsubscribe link in footer works (sets DB status, shows confirmation)
- [ ] Check: Resend dashboard shows delivery + open tracking
- [ ] Send drip-2, drip-3, drip-4 to self — check each
- [ ] Verify contact_activity_events has a row per send with correct template_key

**DONE when:** all 4 emails land in inbox (not spam), render correctly, unsubscribe works, events logged.

---

## PHASE 5 — Segmentation
**Goal:** Send the right email to the right contact. Don't blast everyone with Email 1.

### Segments (from existing contact data)
| Segment | Criteria | Est. size | Angle |
|---|---|---|---|
| Kalpataru owners | unit_registration_records owner | ~800 | Investment angle — you've invested in premium before |
| Kalpataru tenants | unit_registration_records tenant | ~400 | Upgrade angle — own instead of rent |
| Broker contacts | contact_type='broker' or source file contains 'broker' | ~300 | Commission + early access angle |
| NRI / international | email domain patterns, source=Kalpataru Radiance International.csv | ~50 | NRI investment angle |

### Suppression (must pass before any send)
- [ ] `validation_status != 'invalid'` on contact_methods email row
- [ ] Not in outreach_suppression_list
- [ ] Has not already received this template (check email_drip_state)
- [ ] `send_enabled = true` in launch_readiness_checks (flip only after Phase 4 passes)

**DONE when:** segment query returns correct count, suppression logic tested dry-run.

---

## PHASE 6 — Wave 1 Launch
**Goal:** Send Email 1 to first 50 contacts. Monitor. Fix. Then expand.

- [ ] Set `send_enabled = true` in launch_projects for email channel only
- [ ] Run `scripts/email_drip_queue.py --segment kalpataru_owners --limit 50 --apply`
- [ ] Monitor Resend dashboard: delivery rate, open rate, bounce rate
- [ ] Hard bounces → update contact_methods.validation_status = 'invalid' immediately
- [ ] Soft bounces → retry once after 24h then suppress
- [ ] Monitor spam complaints (Resend shows this) → if > 0.1% rate, pause and review
- [ ] After 48h: check open rate (target > 25%), click rate (target > 3%)
- [ ] If metrics OK → send to remaining Kalpataru owners
- [ ] Day 5: queue Email 2 for contacts who opened Email 1

### Success Gates Before Full Rollout
- Delivery rate > 95%
- Spam complaint rate < 0.08%
- Open rate > 20%
- No broken links

**DONE when:** Wave 1 (50 contacts) delivered clean, metrics in range, no complaints.

---

## PHASE 7 — Content SEO (parallel track)
**Goal:** Rank for DLF Mumbai searches. Drive inbound to the same landing page.

### Target Keywords (DLF first Mumbai project angle)
| Keyword | Intent | Est. Volume | Priority |
|---|---|---|---|
| DLF Mumbai | Awareness | High | 1 |
| DLF Westpark Andheri West | Commercial | Medium | 1 |
| DLF first project Mumbai | Informational | Medium | 2 |
| DLF Mumbai investment 2025 | Commercial | Medium | 2 |
| luxury flats Andheri West | Commercial | High | 2 |
| DLF track record returns | Informational | Low | 3 |

### 3 Articles to Write (publish on Wix blog)
1. **"DLF enters Mumbai: what investors need to know about their first project"**
   - DLF history, Gurgaon returns data, why Mumbai now, Andheri West micro-market
   - CTA: download project brief
   
2. **"Andheri West real estate 2025: prices, projects, and why it's the next micro-market"**
   - Market data, metro connectivity, infrastructure projects nearby
   - CTA: compare DLF Westpark

3. **"DLF vs Mumbai developers: what the track record says"**
   - Data comparison: DLF project delivery, price appreciation vs Lodha/Godrej/Oberoi
   - CTA: get early access

- [ ] Publish article 1 on Wix
- [ ] Add internal links from articles → landing page
- [ ] Submit sitemap to Google Search Console
- [ ] Share articles in email drip (Email 2 links to article 1)

---

## FIX LOG
Track issues found during testing here. Format: `[date] issue → fix applied`

---

## LOOP EXIT CONDITIONS
The loop is done when ALL of the following are true:
- [ ] Wave 1 (50 contacts) delivered with metrics in range
- [ ] Unsubscribe mechanism live and tested
- [ ] email_drip_state table tracking all 4 stages
- [ ] At least 1 SEO article published
- [ ] Resend dashboard shows 0 spam complaints

Until then: Test → Fix → Repeat Phase 4.
