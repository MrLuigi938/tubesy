# Tubesy

Selbst gehosteter Video-Downloader mit Weboberfläche, Benutzerkonten und Rechteverwaltung, eine Alternative zu MeTube. Unter der Haube arbeitet [yt-dlp](https://github.com/yt-dlp/yt-dlp): YouTube (Videos, Playlists, Kanäle) und über 1000 weitere Seiten.

## Funktionen

- **Login & Benutzerverwaltung**: Admin- und Benutzerrollen, Einrichtungsassistent beim ersten Start, Registrierung *geschlossen / nur mit Einladungslink / offen*
- **Datentrennung**: Jeder Benutzer hat seinen eigenen Ordner (`/downloads/<benutzer>/…`) und sieht nur seine Downloads, Admins sehen alles
- **Sicherheit für öffentliche Instanzen**: Argon2-Passwörter, HttpOnly-Session-Cookies, CSRF-Schutz, Login-Rate-Limit, Sitzungsübersicht mit Abmelden einzelner Geräte, Security-Header/CSP
- **Downloads**: Vorschau vor dem Laden, komplette Playlists und Kanäle mit Auswahl einzelner Videos, eigener nummerierter Ordner pro Playlist
- **Presets**: Auflösung, Container (MP4/MKV/WebM), Nur-Audio (MP3/M4A/Opus/FLAC/WAV), Untertitel, Thumbnail, Metadaten, Kapitel, SponsorBlock, Dateinamen-Vorlage; globale Presets plus eigene pro Benutzer
- **Warteschlange** mit Live-Fortschritt (WebSocket), Geschwindigkeit, Restzeit, Abbrechen, Wiederholen; Limits gesamt und pro Benutzer, damit niemand mit einer großen Playlist alle anderen blockiert
- **Bibliothek**: Suche, Abspielen im Browser, Herunterladen auf das eigene Gerät, Löschen
- **Speicherkontingente** pro Benutzer, Standard-Kontingent für neue Konten
- **yt-dlp-Update** automatisch beim Start und per Knopfdruck in der Verwaltung
- Dunkler/heller Modus, Smartphone-tauglich, als App installierbar (PWA, inkl. „Teilen mit Tubesy“ auf Android)

## Schnellstart (Docker Compose)

```yaml
services:
  tubesy:
    build: .                       # bzw. später ein veröffentlichtes Image
    container_name: tubesy
    ports:
      - "8080:8080"
    environment:
      - TZ=Europe/Berlin
      - PUID=1000                  # Besitzer des Download-Ordners auf der NAS (`id <user>`)
      - PGID=1000
      - YTDLP_AUTO_UPDATE=true
    volumes:
      - ./config:/config           # Datenbank, Cache
      - /volume1/downloads/tubesy:/downloads
    restart: unless-stopped
```

```sh
docker compose up -d --build
```

Dann `http://<nas-ip>:8080` öffnen und das Administrator-Konto anlegen. Weitere Personen lädst du unter **Verwaltung → Einladungen** per Link ein.

## Umgebungsvariablen

| Variable | Standard | Bedeutung |
|---|---|---|
| `PUID` / `PGID` | `1000` | Benutzer/Gruppe, unter der Tubesy läuft und Dateien schreibt |
| `TZ` | `Europe/Berlin` | Zeitzone |
| `PORT` | `8080` | Port im Container |
| `YTDLP_AUTO_UPDATE` | `true` | yt-dlp bei jedem Start aktualisieren |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | IP/Netz des Reverse-Proxys, dem `X-Forwarded-*` geglaubt wird |
| `COOKIE_SECURE` | `auto` | `auto` setzt das Secure-Flag bei HTTPS, `true` erzwingt es |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | – | Admin ohne Einrichtungsassistent anlegen (nur wenn noch kein Benutzer existiert) |

Alle übrigen Einstellungen (Registrierungsmodus, parallele Downloads, Kontingente, Sitzungsdauer, Playlist-Limit) werden in der Weboberfläche unter **Verwaltung → Einstellungen** gepflegt.

## Öffentlich erreichbar machen

Tubesy gehört hinter einen Reverse-Proxy mit HTTPS (Caddy, Traefik, Nginx Proxy Manager, Synology-Reverse-Proxy):

- **WebSockets** für `/api/ws` durchreichen (bei NPM: „Websockets Support“ aktivieren)
- `FORWARDED_ALLOW_IPS` auf die IP bzw. das Docker-Netz des Proxys setzen, z. B. `172.16.0.0/12`, sonst sieht Tubesy alle Logins als vom Proxy kommend (Rate-Limit) und erkennt HTTPS nicht
- Registrierung auf **Nur mit Einladung** lassen (Standard)

Beispiel Caddy:

```
tube.example.com {
    reverse_proxy tubesy:8080
}
```

## Projektstruktur

```
backend/        FastAPI-App (Python)
  app/routers/  REST-API: auth, account, downloads, presets, admin, ws
  app/services/ yt-dlp-Anbindung, Download-Queue, Live-Events, Einstellungen
  tests/        End-to-End-Tests mit echtem yt-dlp gegen einen lokalen Testserver
frontend/       SvelteKit-SPA (Svelte 5, Tailwind 4)
docker/         Entrypoint und Healthcheck
```

yt-dlp läuft immer als eigener Prozess: Ein hängender Download blockiert nichts, Abbrechen beendet den Prozess, Teil-Dateien liegen in einem temporären Ordner und werden aufgeräumt, und ein yt-dlp-Update wirkt ohne Neustart.

Presets werden in eine feste Auswahl an yt-dlp-Optionen übersetzt. Rohe yt-dlp-Argumente sind bewusst nicht möglich, weil Optionen wie `--exec` Befehle auf dem Server ausführen könnten.

## Entwicklung

```sh
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest httpx
CONFIG_DIR=./.data/config DOWNLOAD_DIR=./.data/downloads YTDLP_AUTO_UPDATE=false uvicorn app.main:app --reload
pytest                                # benötigt ffmpeg

# Frontend (zweites Terminal, Proxy auf :8000)
cd frontend
npm install
npm run dev
npm run check
```

API-Dokumentation: `http://localhost:8000/api/docs`

## Roadmap

- **Phase 2 – Abos**: Playlists/Kanäle abonnieren, Prüfung alle 12 h (einstellbar), nur neue Videos laden, Filter (Shorts/Livestreams/Datum/Titel), Benachrichtigungen (ntfy, Telegram, E-Mail via Apprise)
- **Phase 3 – Komfort**: Cookies pro Benutzer (altersbeschränkte/Mitglieder-Videos), API-Tokens für Browser-Erweiterung/iOS-Kurzbefehl, ZIP-Download ganzer Playlists
- **Phase 4 – Extras**: 2FA (TOTP), optional OIDC/SSO, Aufräumregeln, NFO-Dateien für Jellyfin/Plex
