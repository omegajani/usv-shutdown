#!/usr/bin/env bash
# USV Client Menüleiste – Deinstallation
# Aufruf: ./uninstall-client-menubar.sh
# Via URL: curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/uninstall-client-menubar.sh | bash
set -euo pipefail

AGENT_ID="local.usv-client-menubar"
PLIST="$HOME/Library/LaunchAgents/${AGENT_ID}.plist"
APP_FILE="$HOME/Library/Application Support/usv-shutdown/usv_client_menubar.py"

echo ""
echo "🗑   USV Client Menüleiste – Deinstallation"
echo "────────────────────────────────────────────"

UID_VAL="$(id -u)"
if launchctl list "$AGENT_ID" &>/dev/null; then
    launchctl bootout "gui/${UID_VAL}" "$PLIST" 2>/dev/null || true
    echo "✓  LaunchAgent gestoppt"
fi

[[ -f "$PLIST" ]] && rm -f "$PLIST" && echo "✓  Plist entfernt"
[[ -f "$APP_FILE" ]] && rm -f "$APP_FILE" && echo "✓  Script entfernt"

echo ""
echo "✅  Client Menüleiste entfernt"
echo ""
