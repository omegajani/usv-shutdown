#!/usr/bin/env bash
# USV Agent – Deinstallation
# Aufruf: sudo ./uninstall-agent.sh
# Via URL: curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/uninstall-agent.sh | sudo bash
set -euo pipefail

DAEMON_ID="local.usv-agent"
AGENT_DIR="/usr/local/lib/usv-agent"
PLIST="/Library/LaunchDaemons/${DAEMON_ID}.plist"

if [[ $EUID -ne 0 ]]; then
    echo "❌  Bitte mit sudo ausführen: sudo $0"
    exit 1
fi

echo ""
echo "🗑   USV Agent – Deinstallation"
echo "─────────────────────────────────"

# Daemon stoppen
if launchctl list "$DAEMON_ID" &>/dev/null; then
    launchctl bootout system "$PLIST" 2>/dev/null || true
    echo "✓  Daemon gestoppt"
else
    echo "–  Daemon lief nicht"
fi

# Plist entfernen
if [[ -f "$PLIST" ]]; then
    rm -f "$PLIST"
    echo "✓  LaunchDaemon entfernt"
fi

# Dateien entfernen
if [[ -d "$AGENT_DIR" ]]; then
    rm -rf "$AGENT_DIR"
    echo "✓  Dateien entfernt: $AGENT_DIR"
fi

# Log entfernen (optional)
if [[ -f "/var/log/usv-agent.log" ]]; then
    rm -f "/var/log/usv-agent.log"
    echo "✓  Log entfernt"
fi

echo ""
echo "✅  USV Agent vollständig entfernt"
echo ""
