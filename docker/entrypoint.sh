#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

if [ "$(id -u)" = "0" ]; then
    # Run as the user that owns the files on the NAS share.
    mkdir -p "$CONFIG_DIR" "$DOWNLOAD_DIR"
    chown "$PUID:$PGID" "$CONFIG_DIR"
    find "$CONFIG_DIR" \! -user "$PUID" -exec chown "$PUID:$PGID" {} + 2>/dev/null || true
    # The venv must be writable for the built-in yt-dlp updater.
    [ "$(stat -c %u /opt/venv)" = "$PUID" ] || chown -R "$PUID:$PGID" /opt/venv
    # /downloads is not chowned recursively: it is usually an existing share.
    drop="setpriv --reuid=$PUID --regid=$PGID --clear-groups"
    if ! $drop test -w "$DOWNLOAD_DIR"; then
        echo "WARNUNG: $DOWNLOAD_DIR ist für UID $PUID/GID $PGID nicht beschreibbar. PUID/PGID prüfen." >&2
    fi
    export HOME="$CONFIG_DIR"
    exec $drop "$0" "$@"
fi

exec uvicorn app.main:app \
    --host 0.0.0.0 --port "${PORT:-8080}" \
    --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
    --no-server-header
