# Changelog

All notable changes to Tubesy. Versions follow [semantic versioning](https://semver.org/).

## [1.1.1]

- Download anyway really forces it: if yt-dlp does not know the page, Tubesy looks for the video on it itself (video tags, og:video, stream and file addresses in the page and its scripts, embedded frames) and downloads it directly, named after the page
- Browser impersonation for yt-dlp (curl_cffi): sites that block plain requests, e.g. Vimeo or pages behind Cloudflare, work again

## [1.1.0]

Subscriptions, hidden videos and order.

- Subscriptions: channels and playlists are checked hourly to weekly and their new videos downloaded – with preset, own folder, hiding and optionally the newest videos right away; seen videos are never fetched twice
- Hidden videos: covered in Tubesy (no thumbnail, title or file name until tapped), a library tab of their own, never shown to dashboards like Heimdeck or the API; videos rated 18+ are hidden automatically (per user, can be turned off)
- Notifications when downloads are finished or failed: ntfy (with token), Telegram and the browser; one message per playlist or subscription round, hidden videos never named
- Select several videos or playlists: download as one ZIP, hide or show, delete
- Clean up: delete all single videos, playlists or everything, with a second confirmation that shows the numbers; automatic rules by age (per user) and free space (per instance)
- Download anyway when the check fails; the real title is filled in by yt-dlp
- Installable as an app in every Chromium browser (PNG icons, service worker); Account → App explains when HTTPS is missing
- The storage quota is checked before and during a download, not only at its start
- Links to local addresses (home network) need an administrator's permission for normal users
- Database migrations: existing installations get new fields on start

## [1.0.0]

The first public release.

- Downloads from YouTube (videos, playlists, channels) and more than 1000 other sites with yt-dlp, with preview, live progress, cancel and retry
- Playlists with selection of single videos, numbered folders and ZIP download
- Presets for resolution, container, audio only, subtitles, thumbnail, metadata, chapters, SponsorBlock and file names; global and per user
- Library with search, playback in the browser and download
- User accounts with roles, invitation links, open/invite-only/closed registration, a folder per user, storage quotas and fair queueing
- Security for public instances: Argon2, HttpOnly cookies, CSRF protection, sign-in rate limit, session overview, security headers
- English and German interface, chosen during setup and changeable at any time
- Version in the footer and a hint when a new release is out (can be turned off)
- API with keys for dashboards and automations
- Docker image for amd64 and arm64, install script for Debian/Ubuntu and a script for a Proxmox LXC container
- `reset-password` command for locked-out administrators
