#!/usr/bin/env bash
# Build the production cockpit, start it locally, publish it through Tailscale,
# and print the URL/fallback details for another Mac.
#
#   ./share-cockpit.sh            # start prod + publish cockpit over Tailscale
#   ./share-cockpit.sh --with-db  # also publish NocoDB (:8080)
#   ./share-cockpit.sh stop       # stop Tailscale Serve + the managed prod server
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$PROJECT_ROOT/web"
ENV_FILE="$WEB_DIR/.env.local"
STATE_DIR="$WEB_DIR/.next"
PID_FILE="$STATE_DIR/cockpit-share.pid"
PORT_FILE="$STATE_DIR/cockpit-share-port"
LOG_FILE="${TMPDIR:-/tmp}/rdh-cockpit-share-next.log"
CAFFEINATE_PID_FILE="$STATE_DIR/cockpit-share-caffeinate.pid"

COCKPIT_PORT="${COCKPIT_PORT:-3000}"
DB_PORT=8080
DB_HTTPS_PORT=8443
HOST="0.0.0.0"
export COCKPIT_ENABLED="${COCKPIT_ENABLED:-true}"

# Prefer Codex's bundled modern Node when this repo is run from the desktop app.
BUNDLED_NODE_BIN="/Users/sheeed/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
if [ -x "$BUNDLED_NODE_BIN/node" ]; then
  PATH="$BUNDLED_NODE_BIN:$PATH"
  export PATH
fi

die() { echo "x $*" >&2; exit 1; }

find_tailscale() {
  local ts
  ts="$(command -v tailscale || true)"
  if [ -z "$ts" ] && [ -x "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ]; then
    ts="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
  fi
  [ -n "$ts" ] || die "tailscale CLI not found. Install Tailscale, then in the menu bar choose 'Install CLI...'."
  printf '%s\n' "$ts"
}

pid_is_running() {
  [ -n "${1:-}" ] && kill -0 "$1" >/dev/null 2>&1
}

stop_managed_server() {
  local pid
  if [ -f "$PID_FILE" ]; then
    pid="$(tr -d '[:space:]' < "$PID_FILE" || true)"
    if pid_is_running "$pid"; then
      echo "Stopping managed production cockpit server (pid $pid)..."
      kill "$pid" >/dev/null 2>&1 || true
      for _ in $(seq 1 30); do
        pid_is_running "$pid" || break
        sleep 0.2
      done
      if pid_is_running "$pid"; then
        kill -9 "$pid" >/dev/null 2>&1 || true
      fi
    fi
  fi

  if [ -f "$CAFFEINATE_PID_FILE" ]; then
    pid="$(tr -d '[:space:]' < "$CAFFEINATE_PID_FILE" || true)"
    if pid_is_running "$pid"; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  fi

  rm -f "$PID_FILE" "$PORT_FILE" "$CAFFEINATE_PID_FILE"
}

port_is_open() {
  nc -z 127.0.0.1 "$1" >/dev/null 2>&1
}

pick_port() {
  local requested="$1"
  local candidate="$requested"
  local max=$((requested + 50))

  while [ "$candidate" -le "$max" ]; do
    if ! port_is_open "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
    candidate=$((candidate + 1))
  done

  die "No open local port found from $requested to $max."
}

require_modern_node() {
  local version major minor
  version="$(node -p "process.versions.node" 2>/dev/null || true)"
  [ -n "$version" ] || die "Node.js was not found. Install Node.js 20.9+ and re-run."
  major="${version%%.*}"
  minor="${version#*.}"
  minor="${minor%%.*}"
  if [ "$major" -lt 20 ] || { [ "$major" -eq 20 ] && [ "$minor" -lt 9 ]; }; then
    die "Node.js $version found, but Next.js requires Node.js 20.9+. Install/use Node 20+ and re-run."
  fi
}

require_env() {
  if [ ! -f "$ENV_FILE" ]; then
    die "Missing $ENV_FILE (needs DATABASE_URL + COCKPIT_PASSWORD + COCKPIT_AUTH_TOKEN)."
  fi

  if ! grep -q '^COCKPIT_AUTH_TOKEN=.\+' "$ENV_FILE" || ! grep -q '^COCKPIT_PASSWORD=.\+' "$ENV_FILE"; then
    echo "############################################################"
    echo "# WARNING: COCKPIT_PASSWORD / COCKPIT_AUTH_TOKEN not set.   #"
    echo "# The cockpit will be UNPROTECTED. Anyone on the tailnet    #"
    echo "# could read contact data. Set them in web/.env.local.      #"
    echo "############################################################"
    sleep 4
  fi
}

wait_for_server() {
  local port="$1"
  local pid="$2"
  local deadline=$((SECONDS + 45))

  while [ "$SECONDS" -lt "$deadline" ]; do
    if port_is_open "$port"; then
      return 0
    fi
    if ! pid_is_running "$pid"; then
      echo "Production server exited early. Last log lines:" >&2
      tail -n 80 "$LOG_FILE" >&2 || true
      return 1
    fi
    sleep 1
  done

  echo "Timed out waiting for production server on :$port. Last log lines:" >&2
  tail -n 80 "$LOG_FILE" >&2 || true
  return 1
}

cleanup_running_share() {
  local status=$?
  trap - INT TERM EXIT
  echo
  echo "Stopping Tailscale publishing and production cockpit..."
  "$TS" serve reset >/dev/null 2>&1 || true
  stop_managed_server
  exit "$status"
}

tailscale_identity() {
  "$TS" status --json 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin); s=d.get('Self') or {}
dns=s.get('DNSName','').rstrip('.')
ip=next((x for x in (s.get('TailscaleIPs') or []) if x.startswith('100.')), '')
print(dns, ip, d.get('MagicDNSSuffix',''))
" 2>/dev/null || true
}

publish_tailscale() {
  local port="$1"

  "$TS" serve --bg "$port" </dev/null \
    || die "tailscale serve failed. In the Tailscale admin console, enable MagicDNS and HTTPS Certificates, then re-run: https://login.tailscale.com/admin/dns"
}

TS="$(find_tailscale)"

if [ "${1:-}" = "stop" ]; then
  "$TS" serve reset >/dev/null 2>&1 || true
  stop_managed_server
  echo "Stopped Tailscale publishing and the managed production cockpit server."
  exit 0
fi

require_modern_node
require_env

read -r DNS IP TAILNET < <(tailscale_identity)
[ -z "${DNS:-}" ] && die "Tailscale is not signed in yet. Open Tailscale in the menu bar and sign in, then re-run."

mkdir -p "$STATE_DIR"
stop_managed_server
trap cleanup_running_share INT TERM EXIT

PORT="$(pick_port "$COCKPIT_PORT")"
echo "Building production cockpit..."
npm --prefix "$WEB_DIR" run build

printf '%s\n' "$PORT" > "$PORT_FILE"
echo "Starting production cockpit..."
rm -f "$LOG_FILE"
nohup npm --prefix "$WEB_DIR" run start -- -H "$HOST" -p "$PORT" >"$LOG_FILE" 2>&1 &
SERVER_PID="$!"
printf '%s\n' "$SERVER_PID" > "$PID_FILE"
if command -v caffeinate >/dev/null 2>&1; then
  nohup caffeinate -i -w "$SERVER_PID" >>"$LOG_FILE" 2>&1 &
  printf '%s\n' "$!" > "$CAFFEINATE_PID_FILE"
fi
wait_for_server "$PORT" "$SERVER_PID" || die "Could not start the production cockpit."

echo "Publishing through Tailscale..."
publish_tailscale "$PORT"

DB_LINE=""
if [ "${1:-}" = "--with-db" ]; then
  if port_is_open "$DB_PORT"; then
    "$TS" serve --bg --https="$DB_HTTPS_PORT" "$DB_PORT" </dev/null \
      && DB_LINE="  NocoDB:  https://${DNS}:${DB_HTTPS_PORT}" \
      || echo "Could not publish NocoDB (:$DB_PORT); skipping." >&2
  else
    echo "NocoDB is not listening on :$DB_PORT; skipping --with-db." >&2
  fi
fi

URL="https://${DNS}/cockpit"

echo
echo "Production cockpit is live through Tailscale."
echo
echo "  Cockpit:      ${URL}"
echo "  IP fallback:  http://${IP}:${PORT}/cockpit"
[ -n "$DB_LINE" ] && echo "$DB_LINE"
echo
echo "Send the Cockpit URL to the other Mac. It must be signed into the same tailnet (${TAILNET:-your tailnet})."
echo "Server log: $LOG_FILE"
echo "Keep this terminal open. Press Ctrl-C to stop sharing."

wait "$SERVER_PID"
