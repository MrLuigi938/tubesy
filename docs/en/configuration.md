# Configuration

[← Installation](installation.md) · [Deutsch](../de/configuration.md)

Most settings are made in the web interface under **Admin → Settings**. Only what is needed before the start is set with environment variables (Docker: `environment:` / `.env`, without Docker: `/etc/default/tubesy`).

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `PUID` / `PGID` | `1000` | Docker only: user/group Tubesy runs as and writes files with |
| `TZ` | `Etc/UTC` | time zone, e.g. `Europe/London` |
| `PORT` | `8080` | port inside the container / of the service |
| `YTDLP_AUTO_UPDATE` | `true` | update yt-dlp on every start (sites change often) |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | address/network of your reverse proxy; only from there `X-Forwarded-*` is trusted. The Compose file sets `172.16.0.0/12` (all Docker networks) |
| `COOKIE_SECURE` | `auto` | `auto` sets the Secure cookie flag for HTTPS requests, `true` always |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | – | create the administrator without the setup wizard (only while there is no user) |
| `CONFIG_DIR` | `/config` | database, cache, temporary files |
| `DOWNLOAD_DIR` | `/downloads` | where the videos are saved |

## Settings in the web interface

**Admin → Settings**

| Setting | Default | |
|---|---|---|
| Concurrent downloads (total) | 3 | how many downloads run at the same time |
| Concurrent downloads per user | 2 | keeps one big playlist from blocking everyone else |
| Max. items per playlist | 500 | longer playlists and channels are cut off |
| Default quota for new users | unlimited | in GB, can be changed per user |
| Sign-in valid for | 30 days | with "Stay signed in"; otherwise one day |
| Minimum password length (users) | 6 | administrators always need at least 6 |
| Tell me about new versions | on | asks GitHub twice a day, see [Updating](updating.md) |

**Admin → Invitations:** registration *closed*, *invitation only* (default) or *open*.

The language is chosen per browser – during setup, on the sign-in page or under **Account**.

## Data and backup

Everything except the videos is in **one folder**: `/config` (Docker) or `/var/lib/tubesy/config`. To back up, stop Tubesy and copy that folder (`tubesy.db` is the database). The videos are ordinary files in the download folder: `<download folder>/<username>/…`.
