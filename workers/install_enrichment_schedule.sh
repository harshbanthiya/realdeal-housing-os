#!/bin/bash
# Install the always-on media-enrichment loop (launchd, macOS).
# Every 30 minutes while the Mac is awake: caption 15 photos (Gemini free tier,
# capped at 200/day inside the worker), transcribe 3 videos (whisper, local),
# reconcile a batch of drive contact sheets, and top up the Shorts draft shelf.
# Runs whether or not Claude is open. Pairs with the 07:30 com.rdh.workers job.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.rdh.media-enrichment.plist"
LOG="$HOME/Library/Logs/rdh-media-enrichment.log"
PY="$(command -v python3)"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.rdh.media-enrichment</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>[ -d "${ROOT}/workers" ] || exit 0; export PATH="/usr/local/bin:/opt/homebrew/bin:\$HOME/miniforge3/bin:\$PATH"; "${PY}" "${ROOT}/workers/photo_captioner.py"; "${PY}" "${ROOT}/workers/video_transcriber.py"; "${PY}" "${ROOT}/workers/contact_reconcile.py"; "${PY}" "${ROOT}/workers/shorts_scout.py"</string>
  </array>
  <key>StartInterval</key><integer>1800</integer>
  <key>StandardOutPath</key><string>${LOG}</string>
  <key>StandardErrorPath</key><string>${LOG}</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Installed: com.rdh.media-enrichment (every 30 min while awake). Log: $LOG"
echo "Run now:   launchctl start com.rdh.media-enrichment"
echo "Remove:    launchctl unload $PLIST && rm $PLIST"
