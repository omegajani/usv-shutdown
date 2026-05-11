#!/usr/bin/env python3
"""USV Shutdown Agent — läuft als root LaunchDaemon auf Client-Macs.

Installieren: sudo ./install-agent.sh
Manuell:      sudo python3 usv_agent.py
Test:         curl http://localhost:47777/
"""

import http.server
import json
import logging
import os
import socket
import subprocess
import sys
import threading

PORT = 47777
SERVICE_TYPE = "_usv-agent._tcp"
LOG_FILE = "/var/log/usv-agent.log"


def setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    try:
        fh = logging.FileHandler(LOG_FILE)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except PermissionError:
        pass
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)


def get_hostname() -> str:
    return socket.gethostname().split(".")[0]


def advertise_bonjour() -> None:
    """Registriert diesen Agent via Bonjour (blockiert bis zum Kill)."""
    name = get_hostname()
    cmd = ["dns-sd", "-R", name, SERVICE_TYPE, ".", str(PORT)]
    logging.info("Bonjour: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=False)
    except Exception as exc:
        logging.error("Bonjour-Fehler: %s", exc)


def do_shutdown() -> None:
    logging.info("Shutdown wird ausgeführt")
    os.execv("/sbin/shutdown", ["/sbin/shutdown", "-h", "now"])


class AgentHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args) -> None:
        logging.info("%s %s", self.client_address[0], fmt % args)

    def do_GET(self) -> None:
        if self.path == "/":
            self._reply(200, {"hostname": get_hostname(), "ready": True, "port": PORT})
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path == "/shutdown":
            logging.info("Shutdown angefordert von %s", self.client_address[0])
            self._reply(200, {"ok": True, "message": "shutdown initiated"})
            threading.Timer(0.3, do_shutdown).start()
        else:
            self._reply(404, {"error": "not found"})

    def _reply(self, code: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    setup_logging()
    host = get_hostname()
    logging.info("USV Agent startet | Port %d | Host: %s", PORT, host)

    threading.Thread(target=advertise_bonjour, daemon=True).start()

    server = http.server.HTTPServer(("0.0.0.0", PORT), AgentHandler)
    logging.info("Bereit auf 0.0.0.0:%d", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    logging.info("USV Agent beendet")


if __name__ == "__main__":
    main()
