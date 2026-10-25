# Entwicklung

[← Zurück zur README](../../README.de.md) · [English](../en/development.md)

```
backend/        FastAPI-App (Python 3.11+)
  app/routers/  REST-API: auth, account, downloads, presets, admin, stats (v1), ws
  app/services/ yt-dlp, Download-Warteschlange, Live-Events, Einstellungen, Update-Prüfung
  tests/        End-to-End-Tests mit echtem yt-dlp gegen einen lokalen Testserver
frontend/       SvelteKit-SPA (Svelte 5, Tailwind 4), Texte deutsch mit englischer Übersetzung (src/lib/en.ts)
docker/         Entrypoint, Healthcheck, SWAG-Vorlage
install/        Installationsskript (Debian/Ubuntu) und Proxmox-LXC-Skript
```

yt-dlp läuft immer als eigener Prozess: Ein hängender Download blockiert nichts, Abbrechen beendet den Prozess, Teil-Dateien liegen in einem temporären Ordner und werden aufgeräumt, und ein yt-dlp-Update wirkt ohne Neustart.

## Lokal starten

```sh
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest httpx
CONFIG_DIR=./.data/config DOWNLOAD_DIR=./.data/downloads YTDLP_AUTO_UPDATE=false uvicorn app.main:app --reload
pytest                                # benötigt ffmpeg

# Frontend (zweites Terminal, leitet /api an :8000 weiter)
cd frontend
npm install
npm run dev
npm run check
```

## Übersetzungen

Deutsch ist die Quellsprache: Die Oberfläche ruft `t('deutscher Text')` auf, und `frontend/src/lib/en.ts` enthält den englischen Text dazu. Meldungen des Servers werden genauso übersetzt (`tServer`). Neuer Text → englische Fassung in `en.ts` ergänzen.

## Releases

1. Änderungen in `CHANGELOG.md` unter einer neuen Überschrift `## [x.y.z]` eintragen.
2. Tag setzen und pushen: `git tag v1.1.0 && git push origin v1.1.0`.

GitHub Actions baut dann das Docker-Image (`1.1.0`, `1.1`, `latest`), das Paket `tubesy.tar.gz` für Installationen ohne Docker und das Release mit den Notizen aus dem Changelog. Tags mit Bindestrich (`v1.1.0-beta.1`) werden Vorabversionen und verschieben `latest` nicht. Pushes auf `main` veröffentlichen das Image-Tag `edge`.
