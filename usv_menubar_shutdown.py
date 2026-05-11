#!/usr/bin/env python3
"""USV Shutdown — Menüleisten-App für den Master-Mac (mit USVs).

Installieren: ./install-menubar.sh
Manuell:      python3 usv_menubar_shutdown.py
"""
from __future__ import annotations

import json
import os
import pty
import queue
import re
import select
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

import shutil

import rumps

PORT = 47777
_LOCAL_NAME = socket.gethostname().split(".")[0].lower()
_CONFIG_FILE = os.path.expanduser(
    "~/Library/Application Support/usv-shutdown/config.json"
)


def _load_delay() -> int:
    try:
        with open(_CONFIG_FILE) as f:
            return int(json.load(f).get("delay", 60))
    except Exception:
        return 60


def _save_delay(val: int) -> None:
    try:
        with open(_CONFIG_FILE, "w") as f:
            json.dump({"delay": val}, f)
    except Exception:
        pass
# Bevorzugt lokale Entwicklungsversion, fällt auf installierten Pfad zurück
USV_BIN = (
    shutil.which("usv")
    or "/usr/local/bin/usv"
)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


# ── Discovery ─────────────────────────────────────────────────────────────────

def _run_dnssd_pty(cmd: list[str], timeout: float, on_line) -> None:
    """Führt ein dns-sd Kommando über ein PTY aus (verhindert Pipe-Buffering).

    on_line(line: str) wird für jede Zeile aufgerufen, bis timeout abläuft
    oder on_line gibt False zurück.
    """
    master, slave = pty.openpty()
    proc = subprocess.Popen(cmd, stdout=slave, stderr=slave)
    os.close(slave)
    buf = b""
    end = time.monotonic() + timeout
    try:
        while time.monotonic() < end:
            left = end - time.monotonic()
            r, _, _ = select.select([master], [], [], min(0.2, left))
            if r:
                try:
                    buf += os.read(master, 4096)
                except OSError:
                    break
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.decode(errors="replace").strip()
                    if on_line(line) is False:
                        return
    finally:
        proc.kill()
        proc.wait()
        os.close(master)


def _browse_mdns(timeout: float) -> list[str]:
    """Gibt deduplizierte Liste der gefundenen Bonjour-Instanznamen zurück."""
    seen: set[str] = set()
    instances: list[str] = []

    def on_line(line: str):
        if "Add" in line:
            parts = line.split()
            if len(parts) >= 7:
                name = parts[-1]
                if name not in seen:
                    seen.add(name)
                    instances.append(name)

    _run_dnssd_pty(["dns-sd", "-B", "_usv-agent._tcp"], timeout, on_line)
    return instances


def _resolve_mdns(instance: str, timeout: float) -> tuple[str, int] | None:
    """Löst Bonjour-Instanzname → (host, port) auf."""
    result: list[tuple[str, int] | None] = [None]

    def on_line(line: str):
        m = re.search(r"reached at (.+?):(\d+)", line)
        if m:
            result[0] = (m.group(1).rstrip("."), int(m.group(2)))
            return False  # fertig

    _run_dnssd_pty(["dns-sd", "-L", instance, "_usv-agent._tcp", "local"], timeout, on_line)
    return result[0]


def discover_agents() -> list[tuple[str, str, int]]:
    """Gibt [(name, host, port), ...] via mDNS zurück — ohne den lokalen Rechner."""
    instances = _browse_mdns(timeout=2.5)
    results = []
    for inst in instances:
        if inst.lower() == _LOCAL_NAME:
            continue  # Master-Mac nie als Client behandeln
        resolved = _resolve_mdns(inst, timeout=1.5)
        if resolved:
            host, port = resolved
            results.append((inst, host, port))
    return results


def ping_agent(host: str, port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def shutdown_agent(host: str, port: int) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(
            f"http://{host}:{port}/shutdown", method="POST", data=b"",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return data.get("ok", False), data.get("message", "")
    except Exception as exc:
        return False, str(exc)


# ── USV Status ────────────────────────────────────────────────────────────────

def get_usv_list() -> list[tuple[str, int, str]]:
    """Gibt [(name, batterie_pct, status), ...] aus `usv list` zurück."""
    try:
        r = subprocess.run(
            [USV_BIN, "list"], capture_output=True, text=True, timeout=8,
        )
        usvs = []
        for raw in r.stdout.splitlines():
            line = ANSI.sub("", raw)
            # Verbunden: ✓  xanto1     OL+RB    85%  231V ...
            m = re.search(r"✓\s+(\S+)\s+(\S+)\s+(\d+)%", line)
            if m:
                usvs.append((m.group(1), int(m.group(3)), m.group(2)))
                continue
            # Offline: ✗  xanto1     offline
            m2 = re.search(r"✗\s+(\S+)", line)
            if m2 and "offline" in line:
                usvs.append((m2.group(1), 0, "offline"))
        return usvs
    except Exception:
        return []


# ── App ───────────────────────────────────────────────────────────────────────

class USVShutdownApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("🔌", quit_button=None)
        self._clients: list[tuple[str, str, int]] = []
        self._online: dict[str, bool] = {}
        self._usvs: list[tuple[str, int, str]] = []
        self._delay = _load_delay()
        self._lock = threading.Lock()
        self._needs_rebuild = False
        self._dialog_queue: queue.Queue = queue.Queue()

        self._init_menu()
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _init_menu(self) -> None:
        self.menu = [
            rumps.MenuItem("Verbundene Macs:"),
            rumps.MenuItem("  Suche …"),
            None,
            rumps.MenuItem("USVs:"),
            rumps.MenuItem("  Lade …"),
            None,
            rumps.MenuItem("🔴  Alles herunterfahren…", callback=self._confirm_shutdown),
            None,
            rumps.MenuItem("USV-Delay: 60s", callback=self._set_delay),
            rumps.MenuItem("Aktualisieren", callback=self._manual_refresh),
            None,
            rumps.MenuItem("Beenden", callback=rumps.quit_application),
        ]

    # ── Haupt-Tick (Main Thread) ──────────────────────────────────────────────

    @rumps.timer(0.2)
    def _tick(self, _) -> None:
        # Menu neubauen wenn Daten aktualisiert
        if self._needs_rebuild:
            self._needs_rebuild = False
            self._rebuild_menu()
        # Dialoge aus Background-Threads anzeigen
        try:
            title, msg, result_list, event = self._dialog_queue.get_nowait()
            r = rumps.alert(title=title, message=msg, ok="Fortfahren", cancel="Abbrechen")
            result_list[0] = r == 1
            event.set()
        except queue.Empty:
            pass

    # ── Daten-Refresh (Background) ────────────────────────────────────────────

    @rumps.timer(30)
    def _refresh_timer(self, _) -> None:
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _manual_refresh(self, _) -> None:
        self.title = "🔌 …"
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self) -> None:
        clients = discover_agents()
        online = {host: ping_agent(host, port) for _, host, port in clients}
        usvs = get_usv_list()
        with self._lock:
            self._clients = clients
            self._online = online
            self._usvs = usvs
        self._needs_rebuild = True

    # ── Menu neubauen (Main Thread) ───────────────────────────────────────────

    def _rebuild_menu(self) -> None:
        with self._lock:
            clients = list(self._clients)
            online = dict(self._online)
            usvs = list(self._usvs)
            delay = self._delay

        # Titel-Zusammenfassung
        n_online = sum(1 for _, h, _ in clients if online.get(h))
        n_total = len(clients)
        usv_ok = bool(usvs) and all(s not in ("offline", "OB") for _, _, s in usvs)
        self.title = f"🔌  {n_online}/{n_total} · {'✓' if usv_ok else '⚠'}"

        # Client-Zeilen
        client_items: list = []
        for name, host, _ in clients:
            ok = online.get(host, False)
            dot = "●" if ok else "⚠"
            suffix = "" if ok else "  (offline)"
            client_items.append(rumps.MenuItem(f"  {dot}  {name}{suffix}"))
        if not client_items:
            client_items = [rumps.MenuItem("  Keine Agents gefunden")]

        # USV-Zeilen
        usv_items: list = []
        for name, batt, status in usvs:
            ok_status = status not in ("offline", "OB")
            dot = "●" if ok_status else "⚠"
            batt_str = f"  {batt}%" if batt else ""
            usv_items.append(rumps.MenuItem(f"  {dot}  {name}{batt_str}  {status}"))
        if not usv_items:
            usv_items = [rumps.MenuItem("  usv nicht verfügbar")]

        # Altes Menu leeren (entfernt auch aus NSMenu)
        for key in list(self.menu.keys()):
            del self.menu[key]

        # Neu aufbauen
        new_items = (
            [rumps.MenuItem("Verbundene Macs:")]
            + client_items
            + [None, rumps.MenuItem("USVs:")]
            + usv_items
            + [
                None,
                rumps.MenuItem("🔴  Alles herunterfahren…", callback=self._confirm_shutdown),
                None,
                rumps.MenuItem(f"USV-Delay: {delay}s", callback=self._set_delay),
                rumps.MenuItem("Aktualisieren", callback=self._manual_refresh),
                None,
                rumps.MenuItem("Beenden", callback=rumps.quit_application),
            ]
        )
        self.menu.update(new_items)

    # ── Shutdown-Sequenz ──────────────────────────────────────────────────────

    def _confirm_shutdown(self, _) -> None:
        with self._lock:
            clients = list(self._clients)
            online = dict(self._online)
            delay = self._delay

        lines = ["Reihenfolge:\n"]
        lines.append("  1.  Clients herunterfahren + auf vollständiges Shutdown warten")
        lines.append("  2.  USV-Shutdown-Timer starten")
        lines.append("  3.  Dieser Mac\n")
        lines.append("Clients:")
        for name, host, _ in clients:
            ok = online.get(host, False)
            lines.append(f"  {'●' if ok else '⚠'}  {name}  ({'erreichbar' if ok else 'OFFLINE'})")

        if not clients:
            lines.append("  (keine Client-Macs gefunden)")

        lines.append(f"\nUSV-Delay nach Client-Shutdown: {delay}s")
        lines.append("\nDiese Aktion ist nicht rückgängig zu machen!")

        response = rumps.alert(
            title="⚠  Alles herunterfahren?",
            message="\n".join(lines),
            ok="Herunterfahren",
            cancel="Abbrechen",
        )
        if response == 1:
            threading.Thread(
                target=self._run_sequence,
                args=(clients, online, delay),
                daemon=True,
            ).start()

    def _run_sequence(
        self,
        clients: list[tuple[str, str, int]],
        online: dict[str, bool],
        delay: int,
    ) -> None:
        # ── Schritt 1: Shutdown-Befehl an alle Clients ────────────────────────
        errors: list[str] = []
        shutdown_sent: list[tuple[str, str, int]] = []
        for name, host, port in clients:
            if not online.get(host):
                continue
            ok, msg = shutdown_agent(host, port)
            if ok:
                shutdown_sent.append((name, host, port))
            else:
                errors.append(f"{name}: {msg}")

        if errors and not self._ask_main("Client-Shutdown fehlgeschlagen", "\n".join(errors)):
            return

        # ── Schritt 2: Warten bis alle Clients offline sind ───────────────────
        if shutdown_sent:
            TIMEOUT = 180
            POLL = 5
            deadline = time.monotonic() + TIMEOUT
            pending = {host: (name, port) for name, host, port in shutdown_sent}

            while pending and time.monotonic() < deadline:
                self.title = f"⏳  Warte auf {len(pending)} Mac(s)…"
                time.sleep(POLL)
                pending = {
                    h: (n, p) for h, (n, p) in pending.items()
                    if ping_agent(h, p)
                }

            self._needs_rebuild = True

            if pending:
                names = ", ".join(n for n, _ in pending.values())
                if not self._ask_main(
                    "Clients noch aktiv",
                    f"{names} ist nach {TIMEOUT}s noch erreichbar.\nTrotzdem fortfahren?",
                ):
                    return

        # ── Schritt 3: USV-Countdown ──────────────────────────────────────────
        try:
            r = subprocess.run(
                [USV_BIN, "shutdown", "--all", "--yes", str(delay)],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0:
                detail = (r.stderr.strip() or r.stdout.strip())[:300]
                if not self._ask_main("USV-Shutdown fehlgeschlagen", detail):
                    return
        except Exception as exc:
            if not self._ask_main("USV-Fehler", str(exc)):
                return

        # ── Schritt 4: Dieser Mac ─────────────────────────────────────────────
        time.sleep(1)
        subprocess.run(["sudo", "-n", "shutdown", "-h", "now"])

    def _ask_main(self, title: str, detail: str) -> bool:
        """Zeigt einen Fehler-Dialog auf dem Main Thread, wartet auf Antwort."""
        result: list[bool] = [False]
        event = threading.Event()
        self._dialog_queue.put((
            f"⚠  {title}",
            f"{detail}\n\nTrotzdem fortfahren?",
            result,
            event,
        ))
        event.wait(timeout=60)
        return result[0]

    # ── Einstellungen ─────────────────────────────────────────────────────────

    def _set_delay(self, _) -> None:
        win = rumps.Window(
            message="USV Shutdown-Delay in Sekunden (12 – 5940):",
            title="Delay einstellen",
            default_text=str(self._delay),
            ok="OK",
            cancel="Abbrechen",
            dimensions=(200, 24),
        )
        resp = win.run()
        if resp.clicked and resp.text.strip().isdigit():
            val = int(resp.text.strip())
            if 12 <= val <= 5940:
                self._delay = val
                _save_delay(val)
                self._needs_rebuild = True


if __name__ == "__main__":
    USVShutdownApp().run()
