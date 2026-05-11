# USV Shutdown

Ein-Klick-Notabschaltung für mehrere Macs + USVs via Menüleisten-App.

Läuft als Menüleisten-Icon (🔌) auf dem Master-Mac. Findet alle Client-Macs **automatisch per Bonjour** — kein SSH, keine IP-Konfiguration nötig.

Voraussetzung: Das [usv_control_fsp](https://github.com/omegajani/usv_control_fsp) Paket muss auf dem Master-Mac installiert sein.

---

## Architektur

```
Master-Mac (mit USVs)              Client-Mac(s)
┌────────────────────────┐         ┌─────────────────────┐
│  🔌 Menüleisten-App    │  HTTP   │  usv-agent          │
│  usv_menubar_shutdown  │ ──────→ │  (LaunchDaemon,     │
│                        │ ←────── │   Port 47777)       │
│  Bonjour-Discovery     │  mDNS   │  Bonjour-Advertise  │
│  usv shutdown --all    │         │                     │
│  sudo shutdown -h now  │         │  🖥 Client-Icon     │
└────────────────────────┘         │  (zeigt Agent-Status│
                                   │   in Menüleiste)    │
                                   └─────────────────────┘
```

**Shutdown-Reihenfolge:**
1. Alle Client-Macs via HTTP herunterfahren
2. Warten bis alle Clients offline sind (Save-Dialoge werden abgewartet, max. 3 Min.)
3. USV-Shutdown-Timer setzen (`usv shutdown --all --yes <delay>`)
4. Dieser Mac fährt runter

---

## Installation

### Master-Mac (mit USVs)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-menubar.sh | bash
```

→ Installiert die Menüleisten-App (🔌), startet sie automatisch bei Login.

### Client-Macs — Shutdown-Agent (Pflicht)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-agent.sh | sudo bash
```

→ Installiert den Shutdown-Agent als root-LaunchDaemon (Port 47777, startet automatisch).

### Client-Macs — Menüleisten-Icon (optional)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-client-menubar.sh | bash
```

→ Zeigt ein 🖥-Icon in der Menüleiste: grün wenn der Agent läuft, ⚠️ wenn nicht erreichbar.

---

## Update

Einfach den jeweiligen Installer erneut ausführen — er überschreibt die bestehende Installation.

```bash
# Master-Mac
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-menubar.sh | bash

# Client-Mac (Agent)
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-agent.sh | sudo bash

# Client-Mac (Menüleisten-Icon)
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-client-menubar.sh | bash
```

---

## Deinstallation

```bash
# Master-Mac
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/uninstall-menubar.sh | bash

# Client-Mac (Agent)
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/uninstall-agent.sh | sudo bash

# Client-Mac (Menüleisten-Icon)
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/uninstall-client-menubar.sh | bash
```

---

## Dateien

| Datei | Zweck |
|---|---|
| `usv_agent.py` | Shutdown-Agent (läuft auf Client-Macs als root-Daemon) |
| `usv_menubar_shutdown.py` | Menüleisten-App (läuft auf Master-Mac) |
| `usv_client_menubar.py` | Optionales Status-Icon für Client-Macs (🖥 / ⚠️) |
| `install-agent.sh` | Installer Shutdown-Agent (Client-Mac) |
| `install-menubar.sh` | Installer Menüleisten-App (Master-Mac) |
| `install-client-menubar.sh` | Installer Status-Icon (Client-Mac) |
| `uninstall-agent.sh` | Deinstallation Agent (Client-Mac) |
| `uninstall-menubar.sh` | Deinstallation Menüleisten-App (Master-Mac) |
| `uninstall-client-menubar.sh` | Deinstallation Status-Icon (Client-Mac) |
