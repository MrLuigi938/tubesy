#!/bin/sh
# Install or update Tubesy without Docker – for Debian 12/13, Ubuntu 24.04+,
# Raspberry Pi OS (64-bit) and Proxmox LXC containers (systemd).
#
#   sh install.sh             install or update
#   sh install.sh uninstall   remove service and program (data and downloads are kept)
#
# Options via environment variables (only used for a new installation,
# afterwards everything is in /etc/default/tubesy):
#   TUBESY_PORT=8080                       port of the web interface
#   TUBESY_DOWNLOAD_DIR=/var/lib/tubesy/downloads   where videos are saved
#   TUBESY_VERSION=latest                  version to install, e.g. 1.0.0
#   TUBESY_UID=                            fixed user ID for the tubesy user (e.g. for shared folders)
#   TUBESY_PACKAGE=                        use a downloaded tubesy.tar.gz instead of GitHub
set -eu

REPO="MrLuigi938/tubesy"
VERSION="${TUBESY_VERSION:-latest}"
APP=/opt/tubesy
DATA=/var/lib/tubesy
ENVFILE=/etc/default/tubesy
UNIT=/etc/systemd/system/tubesy.service

say() { printf '\033[1m%s\033[0m\n' "$*"; }
die() { printf '\033[31mError: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" = 0 ] || die "please run as root (e.g. with sudo)"
command -v systemctl >/dev/null 2>&1 || die "systemd is required"

if [ "${1:-}" = uninstall ]; then
  systemctl disable --now tubesy 2>/dev/null || true
  rm -f "$UNIT"
  rm -rf "$APP"
  systemctl daemon-reload
  say "Tubesy has been removed. Your data is still in $DATA (settings in $ENVFILE)."
  exit 0
fi

case "$(uname -m)" in
  x86_64 | amd64) DENO_TARGET=x86_64-unknown-linux-gnu ;;
  aarch64 | arm64) DENO_TARGET=aarch64-unknown-linux-gnu ;;
  *) die "unsupported architecture: $(uname -m) (only amd64 and arm64)" ;;
esac

# ---- System packages: Python, ffmpeg, Deno ----

say "Installing system packages (Python, ffmpeg) …"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv ffmpeg curl ca-certificates unzip tar >/dev/null
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' ||
  die "Python 3.11 or newer is needed (found $(python3 -V 2>&1)). Use Debian 12+, Ubuntu 24.04+ or Docker."

# yt-dlp needs a JavaScript runtime for YouTube.
if ! command -v deno >/dev/null 2>&1; then
  say "Installing Deno (JavaScript runtime for YouTube) …"
  tmp=$(mktemp -d)
  curl -fsSL "https://github.com/denoland/deno/releases/latest/download/deno-$DENO_TARGET.zip" -o "$tmp/deno.zip"
  unzip -q -o "$tmp/deno.zip" -d "$tmp"
  install -m 755 "$tmp/deno" /usr/local/bin/deno
  rm -rf "$tmp"
fi

# ---- Program ----

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
if [ -n "${TUBESY_PACKAGE:-}" ]; then
  cp "$TUBESY_PACKAGE" "$tmp/tubesy.tar.gz"
else
  if [ "$VERSION" = latest ]; then
    url="https://github.com/$REPO/releases/latest/download/tubesy.tar.gz"
  else
    url="https://github.com/$REPO/releases/download/v${VERSION#v}/tubesy.tar.gz"
  fi
  say "Downloading Tubesy ($VERSION) …"
  curl -fsSL "$url" -o "$tmp/tubesy.tar.gz" || die "download failed: $url"
fi
mkdir "$tmp/pkg"
tar -xzf "$tmp/tubesy.tar.gz" -C "$tmp/pkg"
[ -d "$tmp/pkg/app" ] && [ -d "$tmp/pkg/static" ] || die "the package does not look like Tubesy"

update=0
[ -f "$UNIT" ] && update=1
[ "$update" = 1 ] && systemctl stop tubesy

mkdir -p "$APP"
rm -rf "$APP/app" "$APP/static"
cp -R "$tmp/pkg/app" "$tmp/pkg/static" "$tmp/pkg/requirements.txt" "$tmp/pkg/VERSION" "$APP/"

if ! id tubesy >/dev/null 2>&1; then
  useradd --system ${TUBESY_UID:+--uid "$TUBESY_UID"} --user-group --home-dir "$DATA" --shell /usr/sbin/nologin tubesy
fi

say "Installing Python packages (this takes a minute) …"
[ -x "$APP/venv/bin/python" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --quiet --disable-pip-version-check --upgrade pip
"$APP/venv/bin/pip" install --quiet --disable-pip-version-check --upgrade -r "$APP/requirements.txt"
# The built-in yt-dlp updater writes into the venv.
chown -R tubesy:tubesy "$APP/venv"

if [ "$update" = 1 ]; then
  systemctl start tubesy
  say "Tubesy has been updated to version $(cat "$APP/VERSION")."
  exit 0
fi

# ---- Data, settings, service ----

downloads="${TUBESY_DOWNLOAD_DIR:-$DATA/downloads}"
mkdir -p "$DATA/config" "$downloads"
chown tubesy:tubesy "$DATA" "$DATA/config"
chmod 750 "$DATA"
# An empty download folder can be taken over; an existing one with files never is.
if [ -z "$(ls -A "$downloads" 2>/dev/null)" ]; then
  chown tubesy:tubesy "$downloads"
elif ! runuser -u tubesy -- test -w "$downloads"; then
  say "Note: $downloads is not writable for the user tubesy (UID $(id -u tubesy))."
  echo "      Give it to that user, e.g.: chown -R tubesy:tubesy $downloads"
fi

port="${TUBESY_PORT:-8080}"
if [ ! -f "$ENVFILE" ]; then
  cat >"$ENVFILE" <<EOF
# Tubesy settings – after changes: systemctl restart tubesy
PORT=$port
HOST=0.0.0.0
CONFIG_DIR=$DATA/config
DOWNLOAD_DIR=$downloads
FRONTEND_DIR=$APP/static
YTDLP_PYTHON=$APP/venv/bin/python
YTDLP_AUTO_UPDATE=true
TZ=$(cat /etc/timezone 2>/dev/null || echo UTC)
# Reverse proxy on this machine; add its address if it runs elsewhere.
FORWARDED_ALLOW_IPS=127.0.0.1
# auto = Secure cookie flag when the request came via https
COOKIE_SECURE=auto
# Optional: create the admin without the setup wizard
#ADMIN_USERNAME=
#ADMIN_PASSWORD=
EOF
fi
# shellcheck disable=SC1090
downloads=$(. "$ENVFILE" && echo "$DOWNLOAD_DIR")

cat >"$UNIT" <<EOF
[Unit]
Description=Tubesy – self-hosted video downloader
After=network-online.target
Wants=network-online.target

[Service]
User=tubesy
Group=tubesy
EnvironmentFile=$ENVFILE
Environment=HOME=$DATA PATH=/usr/local/bin:/usr/bin:/bin
WorkingDirectory=$APP
ExecStart=$APP/venv/bin/uvicorn app.main:app --host \${HOST} --port \${PORT} --proxy-headers --forwarded-allow-ips \${FORWARDED_ALLOW_IPS} --no-server-header
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=$DATA $APP/venv $downloads

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now tubesy >/dev/null 2>&1

for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:$port/api/health" >/dev/null 2>&1 && break
  sleep 1
done

ip=$(hostname -I 2>/dev/null | awk '{print $1}')
say "Tubesy is running: http://${ip:-localhost}:$port"
echo "Open it and create the administrator account."
echo "Downloads are saved in $downloads, settings are in $ENVFILE."
echo "Update: run this script again. Remove: sh install.sh uninstall"
echo "Forgot your password: sudo -u tubesy sh -c 'set -a; . $ENVFILE; cd $APP && venv/bin/python -m app.cli reset-password <user> <new-password>'"
