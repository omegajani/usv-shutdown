#!/usr/bin/env python3
"""USV Client Menüleiste — zeigt ob der lokale Shutdown-Agent läuft.

Installieren: ./install-client-menubar.sh
"""
from __future__ import annotations

import socket
import urllib.request

import rumps

PORT = 47777

ICON_OK   = "🖥"
ICON_WARN = "⚠️"


def check_agent() -> tuple[bool, str]:
    """Gibt (läuft, hostname) zurück."""
    try:
        import json
        with urllib.request.urlopen(f"http://localhost:{PORT}/", timeout=2) as r:
            data = json.loads(r.read())
            return True, data.get("hostname", socket.gethostname().split(".")[0])
    except Exception:
        return False, socket.gethostname().split(".")[0]


class USVClientApp(rumps.App):
    def __init__(self) -> None:
        super().__init__(ICON_OK, quit_button=None)
        self._build_menu()
        self._refresh(None)

    def _build_menu(self) -> None:
        self.menu = [
            rumps.MenuItem("…"),
            None,
            rumps.MenuItem("Beenden", callback=rumps.quit_application),
        ]

    @rumps.timer(10)
    def _refresh(self, _) -> None:
        ok, host = check_agent()

        self.title = ICON_OK if ok else ICON_WARN

        # Status-Zeile aktualisieren
        for key in list(self.menu.keys()):
            del self.menu[key]

        status = f"  ●  {host}  –  Agent läuft" if ok else f"  ⚠  {host}  –  Agent nicht erreichbar!"
        self.menu.update([
            rumps.MenuItem(status),
            rumps.MenuItem(f"  Port {PORT}"),
            None,
            rumps.MenuItem("Beenden", callback=rumps.quit_application),
        ])


if __name__ == "__main__":
    USVClientApp().run()
