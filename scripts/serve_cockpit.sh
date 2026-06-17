#!/usr/bin/env bash
# Serve the cockpit for multi-user access (you + director) over LAN / Tailscale.
# Builds the Next.js app and serves it on 0.0.0.0:3000, keeping the Mac awake.
# Postgres must already be running (./start.sh). The cockpit is gated by a shared
# password — see docs/cockpit-multi-user-access.md.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/web/.env.local"
PORT="${PORT:-3000}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE (needs DATABASE_URL + COCKPIT_PASSWORD + COCKPIT_AUTH_TOKEN)."
  exit 1
fi

if ! grep -q '^COCKPIT_AUTH_TOKEN=.\+' "$ENV_FILE" || ! grep -q '^COCKPIT_PASSWORD=.\+' "$ENV_FILE"; then
  echo "############################################################"
  echo "# WARNING: COCKPIT_PASSWORD / COCKPIT_AUTH_TOKEN not set.   #"
  echo "# The cockpit will be UNPROTECTED — anyone on the network   #"
  echo "# could read all contact data. Set them in web/.env.local  #"
  echo "# before exposing this. Ctrl-C to abort.                    #"
  echo "############################################################"
  sleep 4
fi

echo "Building cockpit…"
npm --prefix "$PROJECT_ROOT/web" run build

# Show the addresses the director can use.
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
TS_IP="$( (command -v tailscale >/dev/null 2>&1 && tailscale ip -4 2>/dev/null | head -1) || true)"
echo
echo "Cockpit will be available at:"
[ -n "$LAN_IP" ] && echo "  LAN:       http://$LAN_IP:$PORT/cockpit"
echo "  Bonjour:   http://$(scutil --get LocalHostName 2>/dev/null || echo this-mac).local:$PORT/cockpit"
[ -n "$TS_IP" ] && echo "  Tailscale: http://$TS_IP:$PORT/cockpit   (works from anywhere on your tailnet)"
echo

# caffeinate keeps the Mac awake while the server runs (so the director never loses access).
exec caffeinate -i npm --prefix "$PROJECT_ROOT/web" run start -- -H 0.0.0.0 -p "$PORT"
