# syntax=docker/dockerfile:1

# ---- frontend ---------------------------------------------------------------
# The static build is the same for every platform, so it runs natively (no QEMU).
FROM --platform=$BUILDPLATFORM node:22-trixie-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- runtime ----------------------------------------------------------------
FROM denoland/deno:bin-2.9.5 AS deno
FROM mwader/static-ffmpeg:9.0.2 AS ffmpeg

FROM python:3.13-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    YTDLP_PYTHON=/opt/venv/bin/python \
    CONFIG_DIR=/config \
    DOWNLOAD_DIR=/downloads \
    FRONTEND_DIR=/app/static \
    PUID=1000 \
    PGID=1000 \
    TZ=Etc/UTC

# Static binaries instead of apt packages: smaller image, identical on amd64 and arm64.
COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/
# yt-dlp needs a JavaScript runtime to solve YouTube's player challenges.
COPY --from=deno /deno /usr/local/bin/deno

COPY backend/requirements.txt /app/requirements.txt
RUN python -m venv /opt/venv \
 && pip install --no-cache-dir --disable-pip-version-check -r /app/requirements.txt

COPY backend/app /app/app
COPY --from=frontend /src/build /app/static
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/healthcheck.py /healthcheck.py
RUN chmod +x /entrypoint.sh

# The version shown in the footer: the release for tags, "edge-<commit>" for main.
ARG VERSION=dev
ENV TUBESY_VERSION=$VERSION

WORKDIR /app
EXPOSE 8080
VOLUME ["/config", "/downloads"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD ["python", "/healthcheck.py"]

ENTRYPOINT ["/entrypoint.sh"]
