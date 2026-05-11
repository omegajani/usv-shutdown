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
│  usv shutdown --all    │         └─────────────────────┘
│  sudo shutdown -h now  │
└────────────────────────┘
```

**Shutdown-Reihenfolge:**
1. Alle Client-Macs via HTTP herunterfahren
2. USV-Shutdown-Timer setzen (`usv shutdown --all --yes <delay>`)
3. Dieser Mac fährt runter

---

## Installation

### Master-Mac (mit USVs)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-menubar.sh | bash
```

→ Installiert die Menüleisten-App, startet sie automatisch bei Login.

### Client-Macs (alle anderen Macs die heruntergefahren werden sollen)

```bash
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-agent.sh | sudo bash
```

→ Installiert den Shutdown-Agent als LaunchDaemon (startet bei Systemstart automatisch).

---

## Update

Einfach den jeweiligen Installer erneut ausführen — er überschreibt die bestehende Installation.

```bash
# Master-Mac
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-menubar.sh | bash

# Client-Mac
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/install-agent.sh | sudo bash
```

---

## Deinstallation

```bash
# Master-Mac
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/uninstall-menubar.sh | bash

# Client-Mac
curl -fsSL https://cdn.jsdelivr.net/gh/omegajani/usv-shutdown@main/uninstall-agent.sh | sudo bash
```

---

## Dateien

| Datei | Zweck |
|---|---|
| `usv_agent.py` | Shutdown-Agent (läuft auf Client-Macs als root-Daemon) |
| `usv_menubar_shutdown.py` | Menüleisten-App (läuft auf Master-Mac) |
| `install-agent.sh` | Installer für Client-Macs |
| `install-menubar.sh` | Installer für Master-Mac |
| `uninstall-agent.sh` | Deinstallation Client-Mac |
| `uninstall-menubar.sh` | Deinstallation Master-Mac |
