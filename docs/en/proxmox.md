# Proxmox VE: as its own LXC container

[← Installation](installation.md) · [Deutsch](../de/proxmox.md)

A script creates an unprivileged Debian container that starts with the host, and installs Tubesy in it with the [Debian install script](debian.md). Run it in the **shell of your Proxmox node** (as root):

```sh
curl -fsSL https://github.com/MrLuigi938/tubesy/releases/latest/download/proxmox-lxc.sh -o proxmox-lxc.sh
sh proxmox-lxc.sh
```

The script asks for the container name, takes the next free ID, downloads the newest Debian template if needed and prints the address and the root password of the container at the end.

## Options

Set them in front of the command, e.g. `CTID=120 IP=192.168.1.50/24 GATEWAY=192.168.1.1 sh proxmox-lxc.sh`:

| Variable | Default | Meaning |
|---|---|---|
| `CTID` | next free ID | container ID |
| `CT_HOSTNAME` | `tubesy` (asked) | name of the container |
| `CORES` / `MEMORY` | `2` / `1024` | CPU cores, RAM in MB |
| `DISK` | `8` | disk size in GB – the downloads go here unless `HOST_DOWNLOADS` is set |
| `STORAGE` | first container storage | where the disk is created |
| `BRIDGE` | `vmbr0` | network bridge |
| `IP` / `GATEWAY` | `dhcp` | static address, e.g. `192.168.1.50/24` |
| `HOST_DOWNLOADS` | – | a folder on the Proxmox host to save the videos in (see below) |
| `TUBESY_PORT` | `8080` | port of the web interface |
| `ROOT_PASSWORD` | random | root password of the container |
| `SSH_KEY_FILE` | – | public key for SSH, e.g. `~/.ssh/id_ed25519.pub` |

## Saving videos on a NAS or a big disk

Mount the share on the Proxmox host first (e.g. **Datacenter → Storage → Add → SMB/CIFS or NFS**, it then appears under `/mnt/pve/<name>`), then:

```sh
HOST_DOWNLOADS=/mnt/pve/nas/videos sh proxmox-lxc.sh
```

The folder is mounted into the container as the download folder. Unprivileged containers shift user IDs by 100000, so the Tubesy user (ID 1000 inside) is ID **101000** on the host. If Tubesy reports missing write access, give the folder to that ID on the host:

```sh
chown -R 101000:101000 /mnt/pve/nas/videos
```

For SMB/CIFS shares set `uid=101000,gid=101000` in the mount options instead.

## Logging in to the container

Proxmox → container → **Console**, user `root` with the password shown at the end. Change it with `passwd`. Settings are in `/etc/default/tubesy` (after changes: `systemctl restart tubesy`), the log is shown by `journalctl -u tubesy -f`.

## Update

On the Proxmox host:

```sh
pct exec <CTID> -- sh /root/tubesy-install.sh
```

or inside the container `sh /root/tubesy-install.sh`. See [Updating](updating.md).
