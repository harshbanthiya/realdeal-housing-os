#!/bin/sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DOCKER_DIR="$PROJECT_ROOT/docker"
PATH="/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PATH

pkill -f "resend_webhook_server.py" 2>/dev/null && echo "Stopped Resend webhook receiver." || true

cd "$DOCKER_DIR"
docker compose --env-file .env down

# Stop the media-enrichment loop with the stack (drive may be unplugged next).
launchctl unload "$HOME/Library/LaunchAgents/com.rdh.media-enrichment.plist" 2>/dev/null \
  && echo "Media-enrichment loop unloaded." || true
