# Installation

[← Back to the README](../../README.md) · [Deutsch](../de/installation.md)

Tubesy runs on **amd64** and **arm64** Linux: PCs, servers, NAS systems and the Raspberry Pi 4/5 with a 64-bit OS.
After installing, open `http://<your-server>:8080` and create the administrator account. The setup also asks for the language of the interface (English or German).

## Which way is right for me?

| You have … | Use | Guide |
|---|---|---|
| Docker with Compose (most home servers) | `docker compose` | **[Docker Compose](docker-compose.md)** (recommended) |
| Docker without Compose | `docker run` | [Docker](docker.md) |
| Synology, QNAP, Unraid, TrueNAS, Portainer | the NAS's container app | [NAS and container managers](nas.md) |
| Proxmox VE | its own LXC container, created by a script | [Proxmox VE](proxmox.md) |
| Debian, Ubuntu, Raspberry Pi OS – without Docker | an install script with a systemd service | [Debian / Ubuntu](debian.md) |

What is included in every variant: yt-dlp (updated on every start), ffmpeg for merging and converting, and Deno, which yt-dlp needs for YouTube.

## After the installation

- [Configuration](configuration.md) – environment variables and the settings in the web interface
- [Reverse proxy and HTTPS](reverse-proxy.md) – SWAG, Nginx Proxy Manager, Caddy, Traefik
- [Updating](updating.md)
- [Usage](usage.md) – downloads, presets, library, users and invitations
- [Troubleshooting](troubleshooting.md)

## Requirements

- 1 CPU core and 512 MB RAM are enough; converting (e.g. to MP3 or MKV) and several parallel downloads like 2 cores and 1 GB.
- Disk space for your videos. Point the download folder at a share or a large disk.
- Outgoing internet access (to the video sites and, for the update hint, to GitHub).
