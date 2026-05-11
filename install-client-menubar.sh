#!/usr/bin/env bash
# USV Client Menüleiste – Installer
# Lokal:   ./install-client-menubar.sh
# Via URL: curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-client-menubar.sh | bash
set -euo pipefail

AGENT_ID="local.usv-client-menubar"
APP_DIR="$HOME/Library/Application Support/usv-shutdown"
VENV="$APP_DIR/venv"
PLIST="$HOME/Library/LaunchAgents/${AGENT_ID}.plist"
LOG="$HOME/Library/Logs/usv-shutdown.log"
REPO_RAW="https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

# Homebrew-Python bevorzugen
if [[ -x /opt/homebrew/bin/python3 ]]; then
    BASE_PYTHON="/opt/homebrew/bin/python3"
elif [[ -x /usr/local/bin/python3 ]]; then
    BASE_PYTHON="/usr/local/bin/python3"
else
    BASE_PYTHON="$(which python3)"
fi

echo ""
echo "🔧  USV Client Menüleiste – Installer"
echo "──────────────────────────────────────"

# ── 1. Script installieren ────────────────────────────────────────────────────
mkdir -p "$APP_DIR"
if [[ -f "$SCRIPT_DIR/usv_client_menubar.py" ]]; then
    cp "$SCRIPT_DIR/usv_client_menubar.py" "$APP_DIR/usv_client_menubar.py"
    echo "✓  Script kopiert (lokal)"
else
    echo "→  Lade usv_client_menubar.py von GitHub …"
    curl -fsSL "$REPO_RAW/usv_client_menubar.py" -o "$APP_DIR/usv_client_menubar.py"
    echo "✓  Script heruntergeladen"
fi
chmod 755 "$APP_DIR/usv_client_menubar.py"

# ── 2. Virtual Environment + rumps ───────────────────────────────────────────
if [[ ! -x "$VENV/bin/python3" ]]; then
    echo "→  Erstelle Python-Umgebung …"
    "$BASE_PYTHON" -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet rumps
    echo "✓  rumps installiert"
else
    echo "✓  Python-Umgebung bereits vorhanden"
fi

PYTHON="$VENV/bin/python3"

# ── 3. LaunchAgent schreiben ──────────────────────────────────────────────────
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
        <string>${APP_DIR}/usv_client_menubar.py</string>
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

# ── 4. Starten ────────────────────────────────────────────────────────────────
REAL_UID="${SUDO_UID:-$(id -u)}"
REAL_USER="${SUDO_USER:-$(whoami)}"

if launchctl list "$AGENT_ID" &>/dev/null; then
    launchctl bootout "gui/${REAL_UID}" "$PLIST" 2>/dev/null || true
    sleep 1
fi
if [[ -n "${SUDO_USER:-}" ]]; then
    sudo -u "$REAL_USER" launchctl bootstrap "gui/${REAL_UID}" "$PLIST"
else
    launchctl bootstrap "gui/${REAL_UID}" "$PLIST"
fi
echo "✓  LaunchAgent gestartet"

echo ""
echo "✅  USV Client Menüleiste läuft"
echo "   Das 🖥-Icon erscheint in der Menüleiste."
echo "   Log: tail -f $LOG"
echo ""
