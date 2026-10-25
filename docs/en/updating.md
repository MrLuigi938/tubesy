# Updating

[← Installation](installation.md) · [Deutsch](../de/updating.md)

Tubesy tells you when a new version is out: twice a day the server asks GitHub for the newest release. Administrators then see a red dot at **Admin** and the new version in the footer; **Admin → Settings → Info** links to the release notes. Nothing is installed automatically, and the check can be turned off there.

A stable version is only offered stable releases; a beta (e.g. `1.1.0-beta.1`) also newer betas. `edge` and self-built versions don't check.

## Docker Compose

```sh
docker compose pull
docker compose up -d
```

## Docker

```sh
docker pull ghcr.io/mrluigi938/tubesy:latest
docker rm -f tubesy
# start it again with the same docker run command
```

## Synology, QNAP, Unraid, Portainer …

See [NAS and container managers](nas.md) – usually *pull/redeploy* in the container app.

## Debian, Ubuntu, Proxmox LXC

Run the install script again:

```sh
sudo sh install.sh                                  # in the container / on the machine
pct exec <CTID> -- sh /root/tubesy-install.sh       # Proxmox: from the host
```

## yt-dlp

yt-dlp is updated independently of Tubesy on every start (`YTDLP_AUTO_UPDATE=true`) and with **Admin → Settings → System → yt-dlp → Update**. If YouTube downloads suddenly fail, this is the first thing to try.

## Pinning a version

Use a version tag instead of `latest` (e.g. `ghcr.io/mrluigi938/tubesy:1.0` for bug fixes of 1.0 only), or `TUBESY_VERSION=1.0.0` for the install script. All releases: [GitHub Releases](https://github.com/MrLuigi938/tubesy/releases).
