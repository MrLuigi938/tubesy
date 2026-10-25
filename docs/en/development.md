# Development

[← Back to the README](../../README.md) · [Deutsch](../de/development.md)

```
backend/        FastAPI app (Python 3.11+)
  app/routers/  REST API: auth, account, downloads, presets, admin, stats (v1), ws
  app/services/ yt-dlp, download queue, live events, settings, update check
  tests/        end-to-end tests with real yt-dlp against a local test server
frontend/       SvelteKit SPA (Svelte 5, Tailwind 4), texts in German with English translations (src/lib/en.ts)
docker/         entrypoint, health check, SWAG sample
install/        install script (Debian/Ubuntu) and Proxmox LXC script
```

yt-dlp always runs as its own process: a hanging download blocks nothing, canceling ends the process, partial files go to a temporary folder and are cleaned up, and a yt-dlp update takes effect without a restart.

## Running locally

```sh
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest httpx
CONFIG_DIR=./.data/config DOWNLOAD_DIR=./.data/downloads YTDLP_AUTO_UPDATE=false uvicorn app.main:app --reload
pytest                                # needs ffmpeg

# Frontend (second terminal, proxies /api to :8000)
cd frontend
npm install
npm run dev
npm run check
```

## Translations

German is the source language: the interface calls `t('German text')`, and `frontend/src/lib/en.ts` holds the English text for it. Messages from the server are translated the same way (`tServer`). New text → add the English version to `en.ts`.

## Releases

1. Add the changes to `CHANGELOG.md` under a new `## [x.y.z]` heading.
2. Tag and push: `git tag v1.1.0 && git push origin v1.1.0`.

GitHub Actions then builds the Docker image (`1.1.0`, `1.1`, `latest`), the package `tubesy.tar.gz` for installs without Docker and the release with the notes from the changelog. Tags with a hyphen (`v1.1.0-beta.1`) become pre-releases and don't move `latest`. Pushes to `main` publish the image tag `edge`.
