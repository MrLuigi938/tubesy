# NAS und Container-Verwaltungen

[← Installation](installation.md) · [English](../en/nas.md)

- [Synology (Container Manager)](#synology-container-manager)
- [QNAP (Container Station)](#qnap-container-station)
- [Unraid](#unraid)
- [TrueNAS SCALE](#truenas-scale)
- [Portainer](#portainer)

Alle nutzen dasselbe Image, `ghcr.io/mrluigi938/tubesy:latest`, und dieselben zwei Ordner: `/config` (Datenbank, klein) und `/downloads` (Videos).

## Synology (Container Manager)

1. In der **File Station** die Ordner `docker/tubesy/config` und z. B. `video/tubesy` anlegen.
2. Benutzer- und Gruppen-ID herausfinden: **Systemsteuerung → Terminal & SNMP** SSH aktivieren, anmelden und `id <dein-benutzer>` ausführen. Auf Synology ist das meist `uid=1026` und `gid=100`.
3. **Container Manager → Projekt → Erstellen**, Name `tubesy`, Pfad `docker/tubesy`, Quelle *docker-compose.yml erstellen*:

   ```yaml
   services:
     tubesy:
       image: ghcr.io/mrluigi938/tubesy:latest
       container_name: tubesy
       restart: unless-stopped
       ports:
         - "8080:8080"
       environment:
         TZ: Europe/Berlin
         PUID: 1026
         PGID: 100
       volumes:
         - /volume1/docker/tubesy/config:/config
         - /volume1/video/tubesy:/downloads
   ```

4. Assistenten abschließen – das Projekt startet von selbst. `http://<nas-ip>:8080` öffnen.

Meldet Tubesy fehlende Schreibrechte: in der File Station Rechtsklick auf den Download-Ordner → **Eigenschaften → Berechtigung** und deinem Benutzer *Lesen/Schreiben* geben. Ob es jetzt passt, zeigt **Verwaltung → Einstellungen → System → Schreibrechte**.

Aktualisieren: **Container Manager → Projekt → tubesy → Aktion → Erstellen** (holt das neue Image) oder per SSH `docker compose pull && docker compose up -d` in `/volume1/docker/tubesy`.

## QNAP (Container Station)

1. Einen freigegebenen Ordner für die Videos und einen für die Konfiguration anlegen, z. B. `/share/Container/tubesy`.
2. **Container Station → Anwendungen → Erstellen**, Name `tubesy`, und die Compose-Datei aus dem Synology-Abschnitt mit deinen Pfaden (`/share/…`) und IDs einfügen (`id <benutzer>` per SSH; oft `PUID=1000`, `PGID=100`).
3. `http://<nas-ip>:8080` öffnen.

## Unraid

**Docker → Add Container**, in die erweiterte Ansicht wechseln und ausfüllen:

| Feld | Wert |
|---|---|
| Repository | `ghcr.io/mrluigi938/tubesy:latest` |
| Network | `bridge` |
| Port | Container `8080` → Host `8080` |
| Pfad `/config` | `/mnt/user/appdata/tubesy` |
| Pfad `/downloads` | z. B. `/mnt/user/media/tubesy` |
| Variable `PUID` | `99` (nobody) |
| Variable `PGID` | `100` (users) |
| Variable `TZ` | deine Zeitzone, z. B. `Europe/Berlin` |
| WebUI | `http://[IP]:[PORT:8080]/` |

Übernehmen – Unraid holt das Image und startet den Container. Updates erscheinen auf der Docker-Seite als *update ready*.

## TrueNAS SCALE

**Apps → Discover Apps → Custom App** (oder bei neueren Versionen *Install via YAML* mit der Compose-Datei oben):

- Image `ghcr.io/mrluigi938/tubesy`, Tag `latest`
- Port 8080 → 8080
- Speicher: ein Dataset (Host-Pfad) für `/config` und eines für `/downloads`
- Umgebung: `PUID`/`PGID` des Dataset-Besitzers (der Benutzer `apps` ist `568`), `TZ`

## Portainer

**Stacks → Add stack**, Name `tubesy`, die Compose-Datei aus [Docker Compose](docker-compose.md) einfügen, Pfade anpassen und *Deploy*. Zum Aktualisieren den Stack öffnen und **Pull and redeploy** klicken.

Weiter: [Reverse Proxy](reverse-proxy.md) · [Aktualisieren](updating.md)
