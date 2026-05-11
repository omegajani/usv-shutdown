#!/usr/bin/env bash
# USV Agent – Installer für Client-Macs
# Lokal:   sudo ./install-agent.sh
# Via URL: curl -fsSL https://raw.githubusercontent.com/omegajani/usv-shutdown/main/install-agent.sh | sudo bash
set -euo pipefail

DAEMON_ID="local.usv-agent"
AGENT_DIR="/usr/local/lib/usv-agent"
PLIST="/Library/LaunchDaemons/${DAEMON_ID}.plist"
REPO_RAW="https://raw.githubusercontent.com/omegajani/usv-shutdown/main"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

if [[ $EUID -ne 0 ]]; then
    echo "❌  Bitte mit sudo ausführen: sudo $0"
    exit 1
fi

echo ""
echo "🔧  USV Agent – Installer"
echo "──────────────────────────"

# ── 1. Agent-Datei installieren ───────────────────────────────────────────────
mkdir -p "$AGENT_DIR"
if [[ -f "$SCRIPT_DIR/usv_agent.py" ]]; then
    cp "$SCRIPT_DIR/usv_agent.py" "$AGENT_DIR/usv_agent.py"
    echo "✓  Agent kopiert (lokal)"
else
    echo "→  Lade usv_agent.py von GitHub …"
    curl -fsSL "$REPO_RAW/usv_agent.py" -o "$AGENT_DIR/usv_agent.py"
    echo "✓  Agent heruntergeladen"
fi
chmod 755 "$AGENT_DIR/usv_agent.py"

# ── 2. LaunchDaemon-Plist schreiben ──────────────────────────────────────────
cat > "$PLIST" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${DAEMON_ID}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${AGENT_DIR}/usv_agent.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/usv-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/usv-agent.log</string>
</dict>
</plist>
PLIST_EOF

chmod 644 "$PLIST"
echo "✓  LaunchDaemon: $PLIST"

# ── 3. Daemon starten ─────────────────────────────────────────────────────────
if launchctl list "$DAEMON_ID" &>/dev/null; then
    launchctl bootout system "$PLIST" 2>/dev/null || true
    sleep 1
fi
launchctl bootstrap system "$PLIST"
echo "✓  Daemon gestartet"

# ── 4. Verifikation ───────────────────────────────────────────────────────────
sleep 2
if curl -sf "http://localhost:47777/" | grep -q "ready"; then
    AGENT_HOST=$(curl -sf "http://localhost:47777/" | \
        python3 -c "import sys,json; print(json.load(sys.stdin)['hostname'])" 2>/dev/null || hostname)
    echo ""
    echo "✅  USV Agent läuft"
    echo "   Host:  $AGENT_HOST"
    echo "   Port:  47777"
    echo "   Log:   tail -f /var/log/usv-agent.log"
    echo ""
    echo "   Dieser Mac wird vom Master-Mac per Bonjour gefunden."
else
    echo ""
    echo "⚠   Agent antwortet noch nicht. Prüfe:"
    echo "    sudo tail -20 /var/log/usv-agent.log"
    echo "    launchctl list $DAEMON_ID"
fi
echo ""
