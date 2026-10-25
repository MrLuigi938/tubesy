<p align="center">
  <img src="frontend/static/favicon.svg" width="96" alt="Tubesy-Logo">
</p>

<h1 align="center">Tubesy</h1>

<p align="center">
  Ein selbst gehosteter Video-Downloader für deinen Heimserver – mit aufgeräumter Weboberfläche, Benutzerkonten und Rechteverwaltung.<br>
  YouTube-Videos, Playlists und Kanäle sowie über 1000 weitere Seiten, unter der Haube <a href="https://github.com/yt-dlp/yt-dlp">yt-dlp</a>.
</p>

<p align="center">
  <a href="README.md">English</a> · <b>Deutsch</b>
</p>

![Tubesy: Warteschlange mit Live-Fortschritt](docs/images/downloads.webp)
<p align="center"><sub>Screenshots mit Demodaten (englische Oberfläche; Tubesy gibt es auch auf Deutsch)</sub></p>

## Das kann Tubesy

- **Einfügen, prüfen, herunterladen** – erst Titel und Länge sehen, dann ein Preset wählen. Live-Fortschritt mit Geschwindigkeit und Restzeit, Abbrechen und Wiederholen.
- **Playlists und Kanäle** – einzelne Videos oder alle auswählen; jede Playlist bekommt einen eigenen nummerierten Ordner und lässt sich später als ZIP herunterladen.
- **Presets** – Auflösung, MP4/MKV/WebM, nur Audio (MP3, M4A, Opus, FLAC, WAV), Untertitel, Vorschaubild, Metadaten, Kapitel, SponsorBlock und Dateinamen-Vorlagen. Globale Presets plus eigene.
- **Bibliothek** – suchen, im Browser abspielen, aufs eigene Gerät laden.
- **Für den ganzen Haushalt** – Konten mit Rollen, Einladungslinks, ein Ordner pro Benutzer, Speicherkontingente und eine faire Warteschlange, damit eine große Playlist nicht alle anderen blockiert.
- **Sicher im Internet** – Argon2-Passwörter, HttpOnly-Session-Cookies, CSRF-Schutz, Login-Sperre bei Fehlversuchen, Sitzungsübersicht pro Konto und strenge Security-Header.
- **Läuft und läuft** – yt-dlp aktualisiert sich bei jedem Start; Tubesy sagt Bescheid, wenn es selbst eine neue Version gibt.
- **Deutsch und Englisch**, dunkler und heller Modus, smartphonetauglich und als App installierbar – unter Android mit *Teilen → Tubesy*.
- **API** für Dashboards wie [Heimdeck](https://github.com/MrLuigi938/heimdeck) und für Automatisierungen.

| | |
|---|---|
| ![Bibliothek](docs/images/library.webp) | ![Playlists](docs/images/playlists.webp) |
| ![Presets](docs/images/presets.webp) | ![Einstellungen](docs/images/admin.webp) |

<p align="center"><img src="docs/images/phone.webp" width="300" alt="Tubesy auf dem Smartphone"></p>

## Schnellstart (Docker Compose)

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
      PUID: 1000           # Besitzer des Download-Ordners (`id <benutzer>`)
      PGID: 1000
    volumes:
      - ./config:/config
      - ./downloads:/downloads
```

```sh
docker compose up -d
```

`http://<dein-server>:8080` öffnen, Sprache wählen und das Administrator-Konto anlegen. Weitere Personen lädst du unter **Verwaltung → Einladungen** ein.

## Installation

| | |
|---|---|
| 🐳 [Docker Compose](docs/de/docker-compose.md) | empfohlen für die meisten Heimserver |
| 🐳 [Docker](docs/de/docker.md) | `docker run`, Podman |
| 🗄️ [NAS und Container-Verwaltungen](docs/de/nas.md) | Synology, QNAP, Unraid, TrueNAS SCALE, Portainer |
| 🖥️ [Proxmox VE](docs/de/proxmox.md) | eigener LXC-Container mit einem Skript |
| 🐧 [Debian / Ubuntu / Raspberry Pi OS](docs/de/debian.md) | ohne Docker, als systemd-Dienst |

Läuft auf amd64 und arm64 (z. B. Raspberry Pi 4/5).

## Anleitungen

- [Installation im Überblick](docs/de/installation.md)
- [Einstellungen](docs/de/configuration.md)
- [Reverse Proxy und HTTPS](docs/de/reverse-proxy.md) – SWAG, Nginx Proxy Manager, Caddy, Traefik
- [Aktualisieren](docs/de/updating.md)
- [Benutzung](docs/de/usage.md)
- [API](docs/de/api.md)
- [Fehlerbehebung](docs/de/troubleshooting.md)
- [Entwicklung](docs/de/development.md)

## Bitte verantwortungsvoll herunterladen

Tubesy ist ein Werkzeug, um Videos zu speichern, die du behalten darfst – eigene Uploads, Creative-Commons-Inhalte oder was das Recht deines Landes für den privaten Gebrauch erlaubt. Achte das Urheberrecht und die Bedingungen der jeweiligen Seiten.

## Lizenz

[GNU Affero General Public License v3.0](LICENSE)

---

<p align="center">
  Erdacht mit <span title="Liebe">♥</span> von <a href="https://github.com/MrLuigi938">Luis Blum</a> · gebaut mit KI ✨
</p>
