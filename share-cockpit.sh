#!/usr/bin/env bash
# Publish the locally-running cockpit to your tailnet over HTTPS, and print the URL +
# a paste-ready note for the other person. Run AFTER you've installed Tailscale and signed in.
#
#   ./share-cockpit.sh            # publish the cockpit (:3000) at https://<your-mac>.<tailnet>.ts.net
#   ./share-cockpit.sh --with-db  # also publish NocoDB (:8080) at https://<your-mac>.<tailnet>.ts.net:8443
#   ./share-cockpit.sh stop       # stop publishing everything
#
# It does NOT touch your Tailscale login or device sharing — those stay in the menu bar / admin console.
set -euo pipefail

COCKPIT_PORT=3000
DB_PORT=8080
DB_HTTPS_PORT=8443

# Find the CLI whether or not "Install CLI" symlinked it onto PATH.
TS="$(command -v tailscale || true)"
[ -z "$TS" ] && [ -x "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ] && TS="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
if [ -z "$TS" ]; then
  echo "✗ tailscale CLI not found. Install Tailscale (brew install --cask tailscale), then in the menu bar choose 'Install CLI…'." >&2
  exit 1
fi

die() { echo "✗ $*" >&2; exit 1; }

# --- stop mode -------------------------------------------------------------
if [ "${1:-}" = "stop" ]; then
  "$TS" serve reset
  echo "✓ Stopped publishing. The other person's URL will no longer resolve."
  exit 0
fi

# --- preflight -------------------------------------------------------------
# Logged in? Self.DNSName is empty until you've signed in. Also grab the tailnet + IP.
read -r DNS IP TAILNET < <("$TS" status --json 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin); s=d.get('Self') or {}
dns=s.get('DNSName','').rstrip('.')
ip=next((x for x in (s.get('TailscaleIPs') or []) if x.startswith('100.')), '')
print(dns, ip, d.get('MagicDNSSuffix',''))
" 2>/dev/null || true)
[ -z "${DNS:-}" ] && die "Tailscale isn't signed in yet. Open Tailscale in the menu bar and sign in, then re-run."

# Is the cockpit actually up? ponytail: a TCP check beats guessing; serve would publish a dead port otherwise.
if ! nc -z 127.0.0.1 "$COCKPIT_PORT" 2>/dev/null; then
  die "Nothing is listening on :$COCKPIT_PORT. Start the cockpit (npm run dev) and Docker first, then re-run."
fi

# --- publish ---------------------------------------------------------------
# </dev/null so serve can NEVER block on an interactive cert prompt (that's the "hangs silently"
# trap); if HTTPS certs aren't enabled it fails fast and we print the fix instead of hanging.
"$TS" serve --bg "$COCKPIT_PORT" </dev/null \
  || die "serve failed — in the admin console → DNS, enable MagicDNS and HTTPS Certificates, then re-run.  (https://login.tailscale.com/admin/dns)"
URL="https://${DNS}"

DB_LINE=""
if [ "${1:-}" = "--with-db" ]; then
  if nc -z 127.0.0.1 "$DB_PORT" 2>/dev/null; then
    "$TS" serve --bg --https="$DB_HTTPS_PORT" "$DB_PORT" </dev/null \
      && DB_LINE="  • NocoDB:  https://${DNS}:${DB_HTTPS_PORT}" \
      || echo "⚠ couldn't publish NocoDB (:$DB_PORT) — skipping." >&2
  else
    echo "⚠ NocoDB (:$DB_PORT) isn't up — skipping --with-db." >&2
  fi
fi

# --- output ----------------------------------------------------------------
echo
echo "✓ Published. Live while this Mac is awake, Docker + the cockpit are running, and Tailscale stays connected."
echo
echo "  • Cockpit: ${URL}"
echo "  • Fallback (if the name won't resolve): http://${IP}:${COCKPIT_PORT}"
[ -n "$DB_LINE" ] && echo "$DB_LINE"
echo
echo "⚠ The other person MUST be on THIS tailnet (${TAILNET:-your tailnet}) — either signed into the"
echo "  same Tailscale account, or you've shared this machine to their account. A different account"
echo "  = different tailnet = 'server not found'."
echo
echo "────────── paste this to the other person ──────────"
cat <<NOTE
To access the housing cockpit:
1. Install Tailscale: https://tailscale.com/download/mac  (or: brew install --cask tailscale)
2. Open it, approve the network extension, and sign in to the SAME account I told you
   (or accept the device-share invite I sent), so we're on the same tailnet.
3. Make sure Tailscale says "Connected", then open: ${URL}
   (if that says "server not found", use: http://${IP}:${COCKPIT_PORT})
4. Log in with the password I'll send you separately.
Keep Tailscale running while you use it — the link only works through the tunnel.
NOTE
echo "─────────────────────────────────────────────────────"
echo
echo "Stop sharing later with:  ./share-cockpit.sh stop"
