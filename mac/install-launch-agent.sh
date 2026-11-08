#!/bin/bash
# Installs a macOS launch agent so the server starts at login and restarts if it
# crashes. Run from anywhere:  ./mac/install-launch-agent.sh
# Remove with:                 ./mac/install-launch-agent.sh --uninstall
set -euo pipefail

LABEL="com.personal-finance-mcp"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$HOME/Library/Logs/personal-finance-mcp"

if [[ "${1:-}" == "--uninstall" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $LABEL."
  exit 0
fi

[[ -x "$REPO/.venv/bin/python" ]] || { echo "No .venv found. Run the install steps in mac/README.md first."; exit 1; }
[[ -f "$REPO/.env" ]] || { echo "No .env found. Copy .env.example to .env and fill it in first."; exit 1; }

chmod +x "$REPO/mac/run-server.sh"
chmod 600 "$REPO/.env"   # bank tokens: readable by you only
mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$REPO/mac/run-server.sh</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG_DIR/server.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/server.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Running. MCP endpoint: http://127.0.0.1:8000/mcp"
echo "Logs: $LOG_DIR/server.log"
