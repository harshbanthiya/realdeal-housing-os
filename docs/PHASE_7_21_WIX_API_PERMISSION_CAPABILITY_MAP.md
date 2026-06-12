# Phase 7.21 — Wix API Permission & Integration Capability Map

Phase 7.21 builds a **review-gated map** of Wix API permissions → Real Deal Housing OS capabilities,
defines **future** API-key profiles, and queues human review **before any key is created or used**.
It stores **no secrets and no API keys**.

It performs **no** Wix API call, **never** requests/reads/stores an API key, **never** inspects
`.env` for Wix secrets, and does not publish, send, or create leads/contacts.

## Why map permissions before using any key

Wix exposes a large permission surface — many scopes are powerful (publish to production, payments,
members, secrets, embedded scripts, marketing sends). Mapping each permission to a concrete OS
capability, a risk level, and a recommended posture **before** generating a key lets us request the
**minimum** scope for each task, keep risky scopes out, and stage everything behind human review.

## Permission categories (46 catalog rows)

**Useful now / staging (read-first):** Manage Site Branches, Read Site URLs, Wix Forms, Manage Form
Submissions, Wix Data, Wix Blog, Manage FAQ, Manage Site Media, List Marketing Tags. Recommended
`allow_staging_only` / `read_only_preferred`.

**Useful later / gated (`allow_later` / `defer`):** Manage Marketing Tags, Manage Cookie Consent
Banner, Consent Config, Manage Consent Policy, Manage Embedded Scripts, Custom Embeds, Wix CLI - Git
Integration, Business Info, Wix Analytics, Manage Reports, Wix Inbox, Wix Chat, Manage Email
Subscriptions, Manage Email Marketing, social post/channel scopes, and the ambiguous "Manage Tags".
These wait for staging QA plus consent/tracking/messaging review.

**Avoid / defer (`avoid`):** Publish Metasite, Wix Payments / Cashier / Pay Links / Invoices /
Connect Payments Account, Wix Members / Manage Members / Manage Roles / Server Sign On, Wix Secrets,
Invoke AI Models, Wix Restaurants / Loyalty / Donations / Forum / Reviews, Manage Your App, Manage
Notifications, Wixel Projects. Out of scope or high-risk.

Distribution: `allow_staging_only` 6, `read_only_preferred` 3, `allow_later` 14, `defer` 3, `avoid` 20.

## Key profiles (4, all `planned`)

All carry `secret_value_stored=false`, `external_call_allowed=false`, `secret_location='not_created'`.

1. **`wix_staging_discovery_key`** (staging) — read-first discovery: Read Site URLs, Manage Site
   Branches, Wix Data, Wix Forms, Wix Blog, Manage FAQ, Manage Site Media, List Marketing Tags.
   Forbidden: Publish Metasite, payments, members, secrets, email marketing, embedded scripts,
   marketing-tag writes.
2. **`wix_staging_build_key_later`** (staging) — staging write build: Wix Data, Wix Blog, Manage FAQ,
   Manage Site Media, Wix Forms, Manage Site Branches. Forbidden: Publish Metasite, payments,
   members, secrets, email marketing.
3. **`wix_tracking_key_later`** (staging first) — tracking/consent: List/Manage Marketing Tags,
   cookie/consent config + policy. Forbidden: Publish Metasite, form writes, email marketing,
   payments, members, secrets.
4. **`wix_production_key_future`** (production) — forbidden by default; **blocked** until the staging
   fake-lead test passes and the operator approves.

## How keys must be stored (when eventually created)

- **Never in prompts** — do not paste a Wix API key into Claude, Codex, or any chat.
- **Never in the repo** — no key in code, configs, fixtures, docs, or commits.
- **Allowed locations only:** a git-ignored local `.env`, macOS Keychain, 1Password, the n8n
  credential vault, or a connector vault. The capability map records the *location choice* only —
  never the secret value.
- `secret_value_stored` stays `false` in the OS until a key is created **externally**; the OS never
  ingests the secret itself.

## What should NOT be selected yet

Publish Metasite (production publish), any payments/billing scope, any members/roles scope, Wix
Secrets, embedded scripts / custom embeds, marketing-tag writes, email marketing sends, social
publishing, and the ambiguous "Manage Tags". Tracking/consent/email/social scopes wait for their
respective review gates; production publish waits for staging QA + fake-lead test + operator approval.

## Review gate & readiness

10 pending review items (permission, risk, staging-only, production-blocker, publish-permission,
secret-storage, and one per key profile). `vw_dlf_wix_api_readiness` keeps `active_key_profiles=0`,
`external_call_allowed_count=0`, `publish_permission_allowed_count=0`,
`send_permission_allowed_count=0`, `ready_for_api_key_creation=false`, and
`ready_for_api_call_test=false`.

## Cleanup (dry-run command)

```
python3 scripts/cleanup_wix_api_permission_capability_map.py
```

Dry-run by default. `--real-ok --apply` deletes only Phase 7.21 rows (`phase='7.21'`,
`source='wix_api_permission_capability_map_seed'`) and refuses if any key profile is active/external/
secret-bearing, any publish/send permission is allowed, or any review item is approved.

## Next phase

A **controlled API-key readiness check** (operator creates a minimal staging key *externally*, OS
records the profile as `approved_to_create` → `created_externally` with the secret stored only in an
ignored `.env`/vault, never in repo/prompt), **or** continue the **manual Wix staging build**. Any
actual Wix API call remains a separate, explicitly-gated phase.
