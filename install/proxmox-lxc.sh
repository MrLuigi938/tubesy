#!/bin/sh
# Create Tubesy as its own LXC container on Proxmox VE.
# Run as root on the Proxmox host (shell of the node):
#
#   sh proxmox-lxc.sh
#
# Options via environment variables (defaults in brackets):
#   CTID (next free ID)  CT_HOSTNAME (tubesy)  CORES (2)  MEMORY (1024)
#   DISK (8, GB – downloads land here unless HOST_DOWNLOADS is set)
#   STORAGE (first container storage)  BRIDGE (vmbr0)
#   IP (dhcp, or e.g. 192.168.1.50/24)  GATEWAY (static IP only)
#   HOST_DOWNLOADS (none, e.g. /mnt/pve/nas/videos – a host folder mounted as download folder)
#   TUBESY_PORT (8080)
#   ROOT_PASSWORD (random, shown at the end)  SSH_KEY_FILE (none, e.g. ~/.ssh/id_ed25519.pub)
#
# The container is unprivileged, starts with the host and gets Tubesy via
# install.sh (next to this script, otherwise downloaded from INSTALL_URL).
set -eu

say() { printf '\033[1m%s\033[0m\n' "$*"; }
die() { printf '\033[31mError: %s\033[0m\n' "$*" >&2; exit 1; }

command -v pct >/dev/null 2>&1 || die "this script runs on the Proxmox host (pct not found)"
[ "$(id -u)" = 0 ] || die "please run as root"

CTID="${CTID:-$(pvesh get /cluster/nextid)}"
# The container's name in Proxmox (its host name). Asked for in a terminal, unless set.
if [ -z "${CT_HOSTNAME:-}" ] && [ -t 0 ]; then
  printf 'Container name [tubesy]: '
  read -r CT_HOSTNAME || CT_HOSTNAME=""
fi
CT_HOSTNAME="${CT_HOSTNAME:-tubesy}"
printf '%s' "$CT_HOSTNAME" | grep -Eq '^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$' ||
  die "invalid container name \"$CT_HOSTNAME\" – letters, digits and hyphens only (e.g. tubesy)"
CORES="${CORES:-2}"
MEMORY="${MEMORY:-1024}"
DISK="${DISK:-8}"
BRIDGE="${BRIDGE:-vmbr0}"
IP="${IP:-dhcp}"
PORT="${TUBESY_PORT:-8080}"
HOST_DOWNLOADS="${HOST_DOWNLOADS:-}"
# Fixed user ID inside the container, so a host folder can be given to it.
CT_UID=1000
ROOT_PASSWORD="${ROOT_PASSWORD:-$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)}"
[ "${#ROOT_PASSWORD}" -ge 8 ] || die "ROOT_PASSWORD needs at least 8 characters"
INSTALL_URL="${INSTALL_URL:-https://github.com/MrLuigi938/tubesy/releases/latest/download/install.sh}"
STORAGE="${STORAGE:-$(pvesm status -content rootdir 2>/dev/null | awk 'NR > 1 && $3 == "active" { print $1; exit }')}"
TPL_STORAGE="${TPL_STORAGE:-$(pvesm status -content vztmpl 2>/dev/null | awk 'NR > 1 && $3 == "active" { print $1; exit }')}"
[ -n "$STORAGE" ] || die "no container storage found – set STORAGE=…"
[ -n "$TPL_STORAGE" ] || die "no template storage found – set TPL_STORAGE=…"
if [ -n "$HOST_DOWNLOADS" ]; then
  [ -d "$HOST_DOWNLOADS" ] || die "HOST_DOWNLOADS: folder $HOST_DOWNLOADS does not exist on this host"
fi

# newest Debian template (debian-12/13-standard)
say "Looking for a Debian template …"
pveam update >/dev/null 2>&1 || true
arch=$(dpkg --print-architecture)
TEMPLATE=$(pveam available --section system | awk '{print $2}' | grep -E "^debian-[0-9]+-standard_.*_${arch}\.tar\.(zst|gz|xz)$" | sort -V | tail -n 1)
[ -n "$TEMPLATE" ] || die "no Debian template found"
if ! pveam list "$TPL_STORAGE" | grep -q "$TEMPLATE"; then
  say "Downloading $TEMPLATE …"
  pveam download "$TPL_STORAGE" "$TEMPLATE" >/dev/null
fi

net="name=eth0,bridge=$BRIDGE,ip=$IP"
if [ "$IP" != dhcp ] && [ -n "${GATEWAY:-}" ]; then net="$net,gw=$GATEWAY"; fi

say "Creating container $CTID ($CT_HOSTNAME) …"
pct create "$CTID" "$TPL_STORAGE:vztmpl/$TEMPLATE" \
  --hostname "$CT_HOSTNAME" --cores "$CORES" --memory "$MEMORY" --swap 512 \
  --rootfs "$STORAGE:$DISK" --net0 "$net" \
  --unprivileged 1 --features nesting=1 --onboot 1 --tags tubesy \
  --password "$ROOT_PASSWORD" ${SSH_KEY_FILE:+--ssh-public-keys "$SSH_KEY_FILE"} \
  --description "Tubesy – video downloader: http://<IP>:$PORT" >/dev/null
if [ -n "$HOST_DOWNLOADS" ]; then
  pct set "$CTID" --mp0 "$HOST_DOWNLOADS,mp=/var/lib/tubesy/downloads" >/dev/null
fi
pct start "$CTID"

say "Waiting for network …"
i=0
until pct exec "$CTID" -- getent hosts github.com >/dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -lt 60 ] || die "container $CTID has no network connection"
  sleep 1
done

# Use install.sh next to this script, otherwise download it.
dir=$(cd "$(dirname "$0")" && pwd)
if [ -f "$0" ] && [ -f "$dir/install.sh" ]; then
  pct push "$CTID" "$dir/install.sh" /root/tubesy-install.sh
else
  pct exec "$CTID" -- sh -c "apt-get update -qq && apt-get install -y -qq curl ca-certificates >/dev/null && curl -fsSL '$INSTALL_URL' -o /root/tubesy-install.sh"
fi

say "Installing Tubesy in the container …"
pct exec "$CTID" -- env TUBESY_PORT="$PORT" TUBESY_UID="$CT_UID" sh /root/tubesy-install.sh

ct_ip=$(pct exec "$CTID" -- hostname -I | awk '{print $1}')
pct set "$CTID" --description "Tubesy – video downloader: http://$ct_ip:$PORT" >/dev/null
say "Done! Tubesy is running in container $CTID ($CT_HOSTNAME): http://$ct_ip:$PORT"
echo
echo "Console login for the container (Proxmox → $CTID → Console):"
echo "  user: root"
echo "  password: $ROOT_PASSWORD"
echo "Please change it after the first login with: passwd"
if [ -n "$HOST_DOWNLOADS" ]; then
  # Unprivileged containers shift user IDs by 100000 on the host.
  host_uid=$((100000 + CT_UID))
  echo
  echo "Downloads go to $HOST_DOWNLOADS on this host. If Tubesy reports missing write access, run here:"
  echo "  chown -R $host_uid:$host_uid $HOST_DOWNLOADS"
fi
echo
echo "Update: pct exec $CTID -- sh /root/tubesy-install.sh"
