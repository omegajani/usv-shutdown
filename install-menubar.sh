#!/usr/bin/env bash
# USV Shutdown Menüleiste – Installer für den Master-Mac (mit USVs)
# Lokal:   ./install-menubar.sh
# Via URL: curl -fsSL https://raw.githubusercontent.com/omegajani/usv-shutdown/main/install-menubar.sh | bash
set -euo pipefail

AGENT_ID="local.usv-shutdown-menubar"
APP_DIR="$HOME/Library/Application Support/usv-shutdown"
PLIST="$HOME/Library/LaunchAgents/${AGENT_ID}.plist"
LOG="$HOME/Library/Logs/usv-shutdown.log"
REPO_RAW="https://raw.githubusercontent.com/omegajani/usv-shutdown/main"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
PYTHON="$(which python3)"

echo ""
echo "🔧  USV Shutdown Menüleiste – Installer"
echo "────────────────────────────────────────"

# ── 1. Python-Abhängigkeit ────────────────────────────────────────────────────
echo "→  Installiere rumps …"
"$PYTHON" -m pip install --user --quiet rumps
echo "✓  rumps OK"

# ── 2. App-Datei installieren ─────────────────────────────────────────────────
mkdir -p "$APP_DIR"
if [[ -f "$SCRIPT_DIR/usv_menubar_shutdown.py" ]]; then
    cp "$SCRIPT_DIR/usv_menubar_shutdown.py" "$APP_DIR/usv_menubar_shutdown.py"
    echo "✓  App kopiert (lokal)"
else
    echo "→  Lade usv_menubar_shutdown.py von GitHub …"
    curl -fsSL "$REPO_RAW/usv_menubar_shutdown.py" -o "$APP_DIR/usv_menubar_shutdown.py"
    echo "✓  App heruntergeladen"
fi
chmod 755 "$APP_DIR/usv_menubar_shutdown.py"

# ── 3. sudoers für lokalen Shutdown ──────────────────────────────────────────
SUDOERS="/etc/sudoers.d/usv-shutdown"
if [[ ! -f "$SUDOERS" ]]; then
    echo "$USER ALL=(ALL) NOPASSWD: /sbin/shutdown" | sudo tee "$SUDOERS" > /dev/null
    sudo chmod 440 "$SUDOERS"
    echo "✓  sudoers: NOPASSWD für /sbin/shutdown"
else
    echo "✓  sudoers: bereits vorhanden"
fi

# ── 4. LaunchAgent schreiben ──────────────────────────────────────────────────
mkdir -p "$(dirname "$PLIST")"
cat > "$PLIST" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${AGENT_ID}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${APP_DIR}/usv_menubar_shutdown.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG}</string>
    <key>StandardErrorPath</key>
    <string>${LOG}</string>
</dict>
</plist>
PLIST_EOF

echo "✓  LaunchAgent: $PLIST"

# ── 5. Starten ────────────────────────────────────────────────────────────────
UID_VAL="$(id -u)"
if launchctl list "$AGENT_ID" &>/dev/null; then
    launchctl bootout "gui/${UID_VAL}" "$PLIST" 2>/dev/null || true
    sleep 1
fi
launchctl bootstrap "gui/${UID_VAL}" "$PLIST"
echo "✓  LaunchAgent gestartet"

echo ""
echo "✅  USV Shutdown Menüleiste läuft"
echo "   Das 🔌-Icon erscheint in der Menüleiste."
echo "   Log: tail -f $LOG"
echo ""
echo "   Update:      curl -fsSL $REPO_RAW/install-menubar.sh | bash"
echo "   Deinstall:   curl -fsSL $REPO_RAW/uninstall-menubar.sh | bash"
echo ""
