#!/bin/bash
# Install the daily worker schedule (launchd, macOS). Runs run_all.py at 07:30
# daily; launchd also fires missed runs on wake, so a sleeping Mac catches up.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.rdh.workers.plist"
LOG="$HOME/Library/Logs/rdh-workers.log"   # local disk — launchd can't always create files on the external volume at spawn time

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.rdh.workers</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>/usr/bin/python3 "${ROOT}/workers/run_all.py"</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
  <key>StandardOutPath</key><string>${LOG}</string>
  <key>StandardErrorPath</key><string>${LOG}</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Installed: com.rdh.workers (daily 07:30). Log: $LOG"
echo "Run now:   launchctl start com.rdh.workers"
echo "If runs fail with permission errors, grant Full Disk Access to /bin/bash or python3 (System Settings → Privacy) — needed for the external volume."
