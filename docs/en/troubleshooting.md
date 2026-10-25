# Troubleshooting

[← Installation](installation.md) · [Deutsch](../de/troubleshooting.md)

**Admin → Settings → System** shows the most important checks at a glance: yt-dlp version, ffmpeg, Deno, write access to the download folder and free space. **Copy details** there puts version information on the clipboard for a bug report.

## No write access to the download folder

Message *"No write access to the download folder"* or `Permission denied: '/downloads/…'`.

Tubesy writes as `PUID`/`PGID` (Docker) or as the user `tubesy` (without Docker). On the server:

```sh
id <user>                         # uid/gid -> PUID/PGID
ls -ldn /path/to/downloads        # who owns the folder?
sudo chown -R 1000:1000 /path/to/downloads   # use your own values
docker restart tubesy
```

On a Synology alternatively: File Station → folder → Properties → Permission → give the user *Read & Write*. Proxmox with a host folder: see [Proxmox](proxmox.md#saving-videos-on-a-nas-or-a-big-disk).

## YouTube downloads fail

- Update yt-dlp: **Admin → Settings → System → yt-dlp → Update** (happens on every start as well).
- *Sign in to confirm you're not a bot* / HTTP 403: YouTube limits the server's IP address. Wait a while, download fewer videos at once (*Admin → Settings*), or use another connection.
- *Private video* / *Video unavailable* / age-restricted: Tubesy cannot download these without signing in.
- Deno shows *missing* in the system checks: only possible when running from source; install [Deno](https://deno.com).

## The progress doesn't move / the dot in the header is orange

The live connection (WebSocket) does not get through. Behind a reverse proxy WebSockets must be enabled – see [Reverse proxy](reverse-proxy.md).

## Signed out again and again behind HTTPS

Set `FORWARDED_ALLOW_IPS` to the address of your proxy (Compose: `172.16.0.0/12` already covers Docker networks), or `COOKIE_SECURE=false` if you access Tubesy via plain HTTP only.

## Too many sign-in attempts

After repeated wrong passwords, sign-in is blocked for 15 minutes for that user or address. Wait, or have an administrator set a new password. See also [Forgot your password?](usage.md#forgot-your-password).

## Logs

```sh
docker logs -f tubesy          # Docker
journalctl -u tubesy -f        # without Docker
```

Still stuck? [Report a bug](https://github.com/MrLuigi938/tubesy/issues/new) with the copied details.
