# Debian, Ubuntu, Raspberry Pi OS (without Docker)

[← Installation](installation.md) · [Deutsch](../de/debian.md)

An install script sets up Tubesy as a systemd service. Supported: **Debian 12/13, Ubuntu 24.04 or newer, Raspberry Pi OS (64-bit, Bookworm or newer)** – Tubesy needs Python 3.11+.

```sh
curl -fsSL https://github.com/MrLuigi938/tubesy/releases/latest/download/install.sh -o install.sh
sudo sh install.sh
```

The script

1. installs Python, ffmpeg and Deno (JavaScript runtime that yt-dlp needs for YouTube),
2. downloads the newest release to `/opt/tubesy` and creates a Python environment for it,
3. creates the system user `tubesy`, the data folder `/var/lib/tubesy` and the service `tubesy`,
4. prints the address – open it and create the administrator account.

## Options for the first installation

```sh
sudo TUBESY_PORT=8090 TUBESY_DOWNLOAD_DIR=/srv/media/videos sh install.sh
```

| Variable | Default | Meaning |
|---|---|---|
| `TUBESY_PORT` | `8080` | port of the web interface |
| `TUBESY_DOWNLOAD_DIR` | `/var/lib/tubesy/downloads` | where the videos are saved |
| `TUBESY_VERSION` | `latest` | a fixed version, e.g. `1.0.0` |
| `TUBESY_UID` | – | fixed user ID for `tubesy`, e.g. to match the owner of a share |
| `TUBESY_PACKAGE` | – | path to a downloaded `tubesy.tar.gz` (offline install) |

An **existing** download folder with files is never changed. Give it to the user `tubesy` if needed: `sudo chown -R tubesy:tubesy /srv/media/videos`.

## Where is what?

| Path | Content |
|---|---|
| `/opt/tubesy` | program and Python environment (replaced on updates) |
| `/var/lib/tubesy/config` | database, cache |
| `/var/lib/tubesy/downloads` | videos (unless set otherwise) |
| `/etc/default/tubesy` | settings, see [Configuration](configuration.md) |

```sh
systemctl status tubesy        # is it running?
journalctl -u tubesy -f        # log
sudo systemctl restart tubesy  # after changing /etc/default/tubesy
```

## Update and removal

```sh
sudo sh install.sh             # update to the newest version
sudo sh install.sh uninstall   # remove program and service – data and videos stay
```

## Other distributions

The script uses `apt`. On other systemd distributions (Fedora, Arch, openSUSE …) the easiest way is [Docker](docker-compose.md) or Podman. Manual installation: Python 3.11+, ffmpeg and Deno from the package manager, then unpack `tubesy.tar.gz` from the [release](https://github.com/MrLuigi938/tubesy/releases/latest), `python3 -m venv venv && venv/bin/pip install -r requirements.txt` and start `venv/bin/uvicorn app.main:app --port 8080` with the variables from [Configuration](configuration.md).
