#!/bin/sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DOCKER_DIR="$PROJECT_ROOT/docker"
PATH="/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PATH

if [ ! -f "$DOCKER_DIR/.env" ]; then
  cp "$DOCKER_DIR/.env.example" "$DOCKER_DIR/.env"
  echo "Created docker/.env from docker/.env.example."
  echo "Edit docker/.env and replace all change_me values, then run ./start.sh again."
  exit 1
fi

CLEANER="$PROJECT_ROOT/scripts/clean_appledouble_junk.sh"

# Phase 3.9C: the live Postgres cluster now lives on an APFS sparsebundle, not
# the exFAT data/postgres bind mount. APFS stores xattrs natively, so no
# AppleDouble ._* sidecars are generated under the data dir and the old
# preflight-clean/retry workaround is no longer load-bearing for Postgres.
SPARSEBUNDLE='/Volumes/RDH 5TB/rdh-postgres-data.sparsebundle'
APFS_VOLUME='/Volumes/RDH_POSTGRES_DATA'
APFS_PG_DIR="$APFS_VOLUME/postgres"
ATTACH_LOG="${TMPDIR:-/tmp}/rdh-postgres-hdiutil-attach.log"
DETACH_LOG="${TMPDIR:-/tmp}/rdh-postgres-hdiutil-detach.log"
COMPOSE_LOG="${TMPDIR:-/tmp}/rdh-postgres-compose-up.log"

# Count macOS metadata junk (.DS_Store and AppleDouble ._*) under a directory, files only.
junk_count() {
  find "$1" -type f \( -name '.DS_Store' -o -name '._*' \) 2>/dev/null | wc -l | tr -d ' '
}

# Remove macOS metadata junk from the project tree. This still protects the rest
# of the repo (and the preserved data/postgres rollback copy); the live Postgres
# data dir is now on APFS (see ensure_apfs_postgres) and no longer depends on it.
preflight_clean() {
  if [ -x "$CLEANER" ]; then
    "$CLEANER" --apply
  else
    echo "Cleanup helper missing; running inline AppleDouble cleanup."
    echo "macOS metadata junk before: $(junk_count "$PROJECT_ROOT")"
    find "$PROJECT_ROOT" -type f \( -name '.DS_Store' -o -name '._*' \) ! -path "$DOCKER_DIR/.env" -delete 2>/dev/null || true
    echo "macOS metadata junk after: $(junk_count "$PROJECT_ROOT")"
  fi
}

is_apfs_postgres_mounted() {
  mount | grep -qF " on $APFS_VOLUME "
}

sparsebundle_attached() {
  hdiutil info | grep -qF "$SPARSEBUNDLE"
}

attached_sparsebundle_devices() {
  hdiutil info | awk -v image="$SPARSEBUNDLE" '
    /^================================================/ { inside = 0 }
    /^image-path[[:space:]]*:/ && index($0, image) { inside = 1; next }
    inside && /^\/dev\/disk[0-9]/ { print $1 }
  '
}

wait_for_apfs_postgres_mount() {
  tries="$1"
  while [ "$tries" -gt 0 ]; do
    if is_apfs_postgres_mounted; then
      return 0
    fi
    sleep 1
    tries=$((tries - 1))
  done
  return 1
}

wait_for_sparsebundle_detach() {
  tries="$1"
  while [ "$tries" -gt 0 ]; do
    if ! sparsebundle_attached; then
      return 0
    fi
    sleep 1
    tries=$((tries - 1))
  done
  return 1
}

clean_sparsebundle_appledouble() {
  # Clean AppleDouble junk that hdiutil can choke on when the bundle lives on exFAT.
  find "$SPARSEBUNDLE" -name "._*" -exec rm -f {} + 2>/dev/null || true
  find "$SPARSEBUNDLE/bands" -name "._*" -exec rm -f {} + 2>/dev/null || true
}

attach_sparsebundle() {
  clean_sparsebundle_appledouble
  if ! hdiutil attach "$SPARSEBUNDLE" -mountpoint "$APFS_VOLUME" >"$ATTACH_LOG" 2>&1; then
    echo "Explicit mountpoint attach did not complete; retrying default attach..."
    if ! hdiutil attach "$SPARSEBUNDLE" >>"$ATTACH_LOG" 2>&1; then
      echo "ERROR: failed to attach sparsebundle $SPARSEBUNDLE" >&2
      sed 's/^/  /' "$ATTACH_LOG" >&2
      return 1
    fi
  fi
}

detach_attached_sparsebundle() {
  devices="$(attached_sparsebundle_devices || true)"
  if [ -z "$devices" ]; then
    return 1
  fi

  root_dev=""
  for dev in $devices; do
    root_dev="$dev"
    break
  done

  if [ -z "$root_dev" ]; then
    return 1
  fi

  rm -f "$DETACH_LOG"
  echo "Detaching stale sparsebundle device $root_dev..."
  if ! hdiutil detach "$root_dev" >"$DETACH_LOG" 2>&1; then
    echo "Normal detach did not complete; retrying forced detach..."
    if ! hdiutil detach "$root_dev" -force >>"$DETACH_LOG" 2>&1; then
      sed 's/^/  /' "$DETACH_LOG" >&2
      return 1
    fi
  fi

  wait_for_sparsebundle_detach 10
}

mount_attached_sparsebundle_devices() {
  devices="$(attached_sparsebundle_devices || true)"
  if [ -z "$devices" ]; then
    return 1
  fi

  for dev in $devices; do
    hdiutil mountvol "$dev" >/dev/null 2>&1 || true
    if is_apfs_postgres_mounted; then
      return 0
    fi
  done

  if command -v diskutil >/dev/null 2>&1; then
    for dev in $devices; do
      diskutil mount "$dev" >/dev/null 2>&1 || true
      if is_apfs_postgres_mounted; then
        return 0
      fi
    done

    for dev in $devices; do
      diskutil mountDisk "$dev" >/dev/null 2>&1 || true
      if is_apfs_postgres_mounted; then
        return 0
      fi
    done
  fi

  return 1
}

print_apfs_mount_diagnostics() {
  devices="$(attached_sparsebundle_devices || true)"
  echo "ERROR: APFS volume still not mounted after attach attempts." >&2
  echo "Sparsebundle: $SPARSEBUNDLE" >&2
  if [ -n "$devices" ]; then
    echo "Attached devices found for this sparsebundle:" >&2
    for dev in $devices; do
      echo "  $dev" >&2
    done
    echo "Manual recovery to try:" >&2
    echo "  diskutil mount <one of the diskXsY devices above>" >&2
    echo "  hdiutil detach <top-level diskX above> && hdiutil attach '$SPARSEBUNDLE' -mountpoint '$APFS_VOLUME'" >&2
  else
    echo "No attached /dev/disk entries were found for this sparsebundle." >&2
    echo "Manual recovery to try:" >&2
    echo "  hdiutil attach '$SPARSEBUNDLE' -mountpoint '$APFS_VOLUME'" >&2
  fi
  if [ -s "$ATTACH_LOG" ]; then
    echo "Last hdiutil attach output:" >&2
    sed 's/^/  /' "$ATTACH_LOG" >&2
  fi
  if [ -s "$DETACH_LOG" ]; then
    echo "Last hdiutil detach output:" >&2
    sed 's/^/  /' "$DETACH_LOG" >&2
  fi
}

docker_host_mnt_stale_error() {
  [ -s "$COMPOSE_LOG" ] &&
    grep -q "error while creating mount source path '/host_mnt/" "$COMPOSE_LOG" &&
    grep -q ": file exists" "$COMPOSE_LOG"
}

wait_for_docker_unavailable() {
  tries="$1"
  while [ "$tries" -gt 0 ]; do
    if ! docker info >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    tries=$((tries - 1))
  done
  return 1
}

wait_for_docker_ready() {
  tries="$1"
  while [ "$tries" -gt 0 ]; do
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    tries=$((tries - 1))
  done
  return 1
}

repair_docker_host_mnt_bridge() {
  echo "Docker Desktop host mount bridge is stale after an external-disk eject."
  echo "Restarting Docker Desktop once to refresh /host_mnt file sharing..."
  docker compose --env-file .env down >/dev/null 2>&1 || true

  if command -v osascript >/dev/null 2>&1; then
    osascript -e 'quit app "Docker"' >/dev/null 2>&1 || true
    wait_for_docker_unavailable 45 || true
  fi

  if ! command -v open >/dev/null 2>&1; then
    echo "ERROR: cannot reopen Docker Desktop automatically; macOS open command not found." >&2
    return 1
  fi

  open -a Docker >/dev/null 2>&1 || {
    echo "ERROR: failed to reopen Docker Desktop with: open -a Docker" >&2
    return 1
  }

  echo "Waiting for Docker Desktop to become ready..."
  wait_for_docker_ready 90 || {
    echo "ERROR: Docker Desktop did not become ready after restart." >&2
    return 1
  }
}

# Ensure the APFS sparsebundle holding the live Postgres cluster is mounted and
# populated BEFORE Docker starts. Critical safety: if the volume is missing or
# empty, Docker would bind-mount an empty dir and Postgres would initialise a
# brand-new empty cluster (silent apparent data loss). Abort instead.
ensure_apfs_postgres() {
  if ! is_apfs_postgres_mounted; then
    echo "APFS Postgres volume not mounted; attaching sparsebundle..."
    if [ ! -e "$SPARSEBUNDLE" ]; then
      echo "ERROR: sparsebundle missing: $SPARSEBUNDLE" >&2
      echo "Cannot start Postgres without its APFS data volume. Aborting." >&2
      exit 1
    fi

    rm -f "$ATTACH_LOG"
    rm -f "$DETACH_LOG"
    if sparsebundle_attached; then
      echo "Sparsebundle is already attached; mounting its APFS volume..."
      mount_attached_sparsebundle_devices || true
      if ! wait_for_apfs_postgres_mount 3; then
        echo "Attached sparsebundle did not mount; detaching stale image and reattaching..."
        detach_attached_sparsebundle || {
          print_apfs_mount_diagnostics
          exit 1
        }
        attach_sparsebundle || exit 1
      fi
    else
      attach_sparsebundle || exit 1
    fi

    if ! wait_for_apfs_postgres_mount 5; then
      mount_attached_sparsebundle_devices || true
      wait_for_apfs_postgres_mount 5 || {
        print_apfs_mount_diagnostics
        exit 1
      }
    fi

    if ! is_apfs_postgres_mounted; then
      # Belt-and-suspenders guard; the wait block above should already exit.
      print_apfs_mount_diagnostics
      exit 1
    fi
  fi

  if [ ! -d "$APFS_PG_DIR" ]; then
    echo "ERROR: $APFS_PG_DIR is missing after mount; aborting before docker compose up." >&2
    exit 1
  fi
  if [ -z "$(ls -A "$APFS_PG_DIR" 2>/dev/null)" ]; then
    echo "ERROR: $APFS_PG_DIR is empty; refusing to start so Postgres cannot" >&2
    echo "initialise a fresh empty cluster over your data. Aborting." >&2
    exit 1
  fi
  if [ ! -f "$APFS_PG_DIR/PG_VERSION" ]; then
    echo "ERROR: $APFS_PG_DIR/PG_VERSION not found; this is not a valid Postgres" >&2
    echo "cluster directory. Aborting before docker compose up." >&2
    exit 1
  fi
  echo "APFS Postgres volume ready: $APFS_PG_DIR (cluster version $(cat "$APFS_PG_DIR/PG_VERSION"))."
}

# Mount + validate the APFS data volume before any docker compose call.
ensure_apfs_postgres

cd "$DOCKER_DIR"

# Stage the bring-up: start Postgres first and wait until it is healthy before
# launching the rest of the stack. On exFAT/external volumes Docker can
# re-materialise AppleDouble junk during a multi-container bring-up and race the
# Postgres entrypoint, so each attempt re-cleans from a stopped Postgres.
ATTEMPT=1
MAX_ATTEMPTS=3
DOCKER_HOST_MNT_REPAIRED=0
while : ; do
  docker compose --env-file .env rm -sf postgres >/dev/null 2>&1 || true
  preflight_clean
  echo "Starting Postgres (attempt $ATTEMPT of $MAX_ATTEMPTS)..."
  rm -f "$COMPOSE_LOG"
  set +e
  docker compose --env-file .env up -d --wait --wait-timeout 90 postgres >"$COMPOSE_LOG" 2>&1
  COMPOSE_STATUS=$?
  set -e
  cat "$COMPOSE_LOG"
  if [ "$COMPOSE_STATUS" -eq 0 ]; then
    break
  fi
  if docker_host_mnt_stale_error && [ "$DOCKER_HOST_MNT_REPAIRED" -eq 0 ]; then
    DOCKER_HOST_MNT_REPAIRED=1
    repair_docker_host_mnt_bridge || exit 1
    echo "Retrying Postgres after Docker Desktop host mount refresh..."
    continue
  fi
  if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
    echo "ERROR: Postgres did not become healthy after $MAX_ATTEMPTS attempts." >&2
    if docker_host_mnt_stale_error; then
      echo "Docker Desktop still has stale /host_mnt file-sharing entries." >&2
      echo "Quit Docker Desktop completely, reopen it, then run ./start.sh again." >&2
    else
      echo "This is usually exFAT AppleDouble junk regenerating under data/postgres." >&2
      echo "See README.md (AppleDouble / exFAT) for durable fix options." >&2
    fi
    exit 1
  fi
  echo "Postgres unhealthy; recreating and retrying after re-clean..."
  ATTEMPT=$((ATTEMPT + 1))
done

# Postgres is healthy: bring up the rest of the stack.
docker compose --env-file .env up -d
docker compose --env-file .env ps

# Resend bounce/complaint webhook receiver (plain python, not dockerized —
# it just needs to be up whenever the stack is). Idempotent: skip if already
# listening. The Cloudflare tunnel to it runs as its own separate launchd
# service (com.cloudflare.cloudflared) and is not managed here.
WEBHOOK_SECRET="$(grep '^RESEND_WEBHOOK_SECRET=' .env | cut -d= -f2-)"
if [ -n "$WEBHOOK_SECRET" ] && ! lsof -i :8787 >/dev/null 2>&1; then
  echo "Starting Resend webhook receiver on :8787..."
  nohup python3 "$PROJECT_ROOT/scripts/resend_webhook_server.py" \
    --port 8787 --secret "$WEBHOOK_SECRET" \
    > "$PROJECT_ROOT/data/resend-webhook.log" 2>&1 &
  disown
else
  echo "Resend webhook receiver already running (or no RESEND_WEBHOOK_SECRET set)."
fi

# Daily workers (worker_runs / worker_findings → /cockpit/inbox). launchd runs
# them at 07:30; this fallback guarantees a run on any day the stack starts.
bash "$PROJECT_ROOT/workers/run_if_due.sh" || echo "Workers run failed — check manually: python3 workers/run_all.py"
