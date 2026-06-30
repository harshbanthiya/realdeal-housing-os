# DLF Email Drip — CONTENT LOOP
Iterate here until all emails are approved. Exit when every email is marked ✅ APPROVED below.

---

## STATUS

| Email | Variant A | Variant B | Approved |
|-------|-----------|-----------|----------|
| Email 1 — Awareness | `web/emails/drip-1-variant-a.tsx` | `web/emails/drip-1-variant-b.tsx` | ⏳ pending review |
| Email 2 — Consideration | not written | — | ⏳ waiting on Email 1 |
| Email 3 — Conversion | not written | — | ⏳ waiting on Email 1 |
| Email 4 — Referral | not written | — | ⏳ waiting on Email 1 |

---

## HOW TO REVIEW EMAIL 1

Preview both variants in browser:

```bash
cd /Volumes/RDH\ 5TB/Real\ Deal\ Housing\ OS/web
npx email preview
# opens at http://localhost:3000 — select drip-1-variant-a or drip-1-variant-b
```

Or render to HTML for quick check:

```bash
cd /Volumes/RDH\ 5TB/Real\ Deal\ Housing\ OS/web
npx tsx -e "
  import { render } from '@react-email/render';
  import Email from './emails/drip-1-variant-a';
  import fs from 'fs';
  fs.writeFileSync('/tmp/email-a.html', render(Email({})));
  console.log('Saved to /tmp/email-a.html');
"
open /tmp/email-a.html
```

---

## CONTENT CHECKLIST (per email)

Before approving any email, confirm:

- [ ] No `[VERIFY]` / `[PENDING]` placeholders remain
- [ ] RERA number real (DLF Westpark RERA) — **check before sending**, use `[RERA_PENDING]` if not confirmed
- [ ] Price range either confirmed or intentionally omitted
- [ ] Unsubscribe link present in footer
- [ ] From name = "Padmini Jain" or "Real Deal Housing"
- [ ] CTA link points to `/dlf-westpark-andheri-west`
- [ ] Renders on mobile (check in Gmail app + Apple Mail)
- [ ] Subject line < 50 chars (no clip on mobile)
- [ ] No spam trigger words (FREE, GUARANTEED, CLICK NOW, etc.)
- [ ] Disclaimer present on Variant B (not financial advice)

---

## PHOTOS / ASSETS NEEDED

Hero images — replace the `heroPlaceholder` section in each variant once available:

| Asset | Status | Source |
|-------|--------|--------|
| DLF Westpark render / exterior | MISSING | Request from DLF's marketing team; or use press image from dlf.in/media |
| RDH logo (hosted) | MISSING | Upload `/Volumes/RDH 5TB/RDH DATA 2024/RDH/LOGO/RDH logo 1.png` to Wix Media, paste CDN URL |
| Padmini photo | MISSING | Available locally — upload to Wix Media for email sig use |
| Imperial Heights photo (trust signal) | MISSING | Swimmer pool / elevation photos in RDH DATA 2024/Imperial heights photos/ |

**Ponytail note:** Don't block email sending on photos. Ship with teal placeholder block → swap CDN URL once asset is uploaded. One line change.

---

## ITERATION LOG

Use this section to track each round of edits. Format: `[date] what changed → why`

---

## EMAIL 1 — VARIANT COMPARISON

### Variant A — "The Inner Circle" (personal letter)
- Opens with "Dear [Name]"
- Padmini speaks directly, warm, advisory tone
- Pull quote with amber left border
- Facts strip at bottom (mist bg)
- Best for: owner contacts who know Padmini personally

### Variant B — "The Investment Brief" (editorial)
- Dark hero with headline + CTA in hero itself
- Stats bar: 57yrs DLF / 10-15× returns / Andheri W
- Structured sections: THE DEVELOPER / THE LOCATION / THE OPPORTUNITY
- Dark CTA panel with amber button
- Disclaimer footer (not financial advice)
- Best for: investor-type contacts, NRI, brokers

**Recommendation:** A/B test — send Variant A to warm owner contacts (Kalpataru), Variant B to broker + NRI segment.

---

## SUBJECT LINE OPTIONS (Email 1)

| Option | Chars | Notes |
|--------|-------|-------|
| DLF just entered Mumbai — we have early access | 48 | Best for Variant A |
| DLF Westpark: the first DLF project in Mumbai | 47 | Best for Variant B |
| The name behind DLF City is coming to Andheri | 48 | Alt |
| Before it's public: DLF Westpark Andheri West | 48 | Direct |

---

## SEQUENCE — AFTER EMAIL 1 APPROVED

**Email 2 — Consideration (Day 5)**
Topic: "DLF Westpark: the numbers behind the address"
- RERA details, carpet area, wings, price per sqft estimate
- Andheri West market data (rental yield, capital appreciation)
- CTA: "Request the brochure" → WhatsApp or form

**Email 3 — Conversion (Day 12)**
Topic: "Site visit — we're arranging limited slots"
- What a site visit includes
- Pre-launch pricing closes at possession booking
- CTA: "Book a slot" → WhatsApp or calendar

**Email 4 — Referral (Day 20)**
Topic: "Know someone who should see this?"
- Short, warm, forwarding ask
- CTA: "Forward this email" or share link

---

## LOOP EXIT

Exit this loop when:
- [ ] Email 1 approved (one of A or B, or both)
- [ ] Email 2 written and approved
- [ ] Email 3 written and approved
- [ ] Email 4 written and approved
- [ ] All photo assets replaced (or deliberately deferred with ticket)
- [ ] All LOOP-infra.md tests pass

Until then: revise → preview → re-check checklist → get approval.
