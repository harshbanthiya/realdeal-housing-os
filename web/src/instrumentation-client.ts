// PostHog cloud (EU, free tier) — decision memo E.6 in docs/MEDIA-SOCIAL-FUNNEL-PLAN.md.
// No key set → no-op, so dev/preview environments send nothing.
import posthog from "posthog-js";

const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;

if (key) {
  posthog.init(key, {
    api_host: "https://eu.i.posthog.com",
    defaults: "2025-05-24", // auto pageviews + pageleaves incl. SPA navigations
    capture_exceptions: true,
    respect_dnt: true,
  });
}
