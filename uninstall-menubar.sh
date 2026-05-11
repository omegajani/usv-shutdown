#!/usr/bin/env bash
# USV Shutdown Menüleiste – Deinstallation
# Aufruf: ./uninstall-menubar.sh
# Via URL: curl -fsSL https://raw.githubusercontent.com/omegajani/usv-shutdown/main/uninstall-menubar.sh | bash
set -euo pipefail

AGENT_ID="local.usv-shutdown-menubar"
APP_DIR="$HOME/Library/Application Support/usv-shutdown"
PLIST="$HOME/Library/LaunchAgents/${AGENT_ID}.plist"
SUDOERS="/etc/sudoers.d/usv-shutdown"

echo ""
echo "🗑   USV Shutdown Menüleiste – Deinstallation"
echo "──────────────────────────────────────────────"

# LaunchAgent stoppen
UID_VAL="$(id -u)"
if launchctl list "$AGENT_ID" &>/dev/null; then
    launchctl bootout "gui/${UID_VAL}" "$PLIST" 2>/dev/null || true
    echo "✓  LaunchAgent gestoppt"
else
    echo "–  LaunchAgent lief nicht"
fi

# Plist entfernen
if [[ -f "$PLIST" ]]; then
    rm -f "$PLIST"
    echo "✓  LaunchAgent-Plist entfernt"
fi

# App-Dateien entfernen
if [[ -d "$APP_DIR" ]]; then
    rm -rf "$APP_DIR"
    echo "✓  Dateien entfernt: $APP_DIR"
fi

# sudoers entfernen
if [[ -f "$SUDOERS" ]]; then
    sudo rm -f "$SUDOERS"
    echo "✓  sudoers-Eintrag entfernt"
fi

# Log entfernen (optional)
LOG="$HOME/Library/Logs/usv-shutdown.log"
if [[ -f "$LOG" ]]; then
    rm -f "$LOG"
    echo "✓  Log entfernt"
fi

echo ""
echo "✅  USV Shutdown Menüleiste vollständig entfernt"
echo ""
