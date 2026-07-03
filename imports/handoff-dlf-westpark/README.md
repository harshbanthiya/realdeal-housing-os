# DLF Westpark Email v2 — handoff

Drop these into `web/emails/` in the Real Deal Housing OS repo.

## Files
- `dlf-westpark-send.html` — final, QA'd, self-contained email HTML. All images
  hosted on static.wixstatic.com. This is the simplest thing to send.
- `dlf-westpark-v2.tsx` — same design as a React Email component (replaces
  dlf-westpark.tsx). Use for personalized bulk sends. Changelog in the header.
- `send-test.ts` — Resend test script for the tsx path.

## Test send (HTML path — recommended first)
1. Read dlf-westpark-send.html as a string.
2. Replace merge tokens:
   - "Dear {{firstName}}," -> "Hello,"
   - href="{{unsubscribe}}" -> href="https://realdealhousing.com"
3. resend.emails.send({
     from: <verified realdealhousing.com sender>,
     to: "hbanthiya@gmail.com",
     subject: "[TEST] Phase 2 is open — DLF Westpark, Andheri West",
     html,
   })
4. Do NOT otherwise modify the HTML — it's QA'd for Gmail light/dark mode,
   375px mobile, and Outlook (table layout, bgcolor cells, baked-in crops).

## Test send (tsx path)
RESEND_API_KEY=re_xxx npx tsx emails/send-test.ts
(set RESEND_FROM to the verified realdealhousing.com sender)

## What to check in the inbox
- Inbox snippet reads the baked preheader, not garbled body text
- Gmail dark mode: hero + CTA stay teal with white text; logo icon not inverted
- "Phase 2 · Andheri West" is NOT auto-linked blue
- CTA button is one line on a phone; WhatsApp deep link pre-fills the message
