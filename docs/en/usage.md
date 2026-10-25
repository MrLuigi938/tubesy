# Usage

[← Back to the README](../../README.md) · [Deutsch](../de/usage.md)

- [Downloading](#downloading)
- [Playlists and channels](#playlists-and-channels)
- [Presets](#presets)
- [Library](#library)
- [Sharing from the phone](#sharing-from-the-phone)
- [Users, invitations and quotas](#users-invitations-and-quotas)
- [Account and sessions](#account-and-sessions)
- [API keys and dashboards](#api-keys-and-dashboards)
- [Forgot your password?](#forgot-your-password)

## Downloading

Paste a link on **Downloads** and click **Check**. Tubesy shows title, channel and length first; then pick a preset and click **Download**. The queue shows progress, speed and remaining time live; downloads can be canceled and failed ones retried.

YouTube, YouTube Music and more than 1000 other sites work – **Which sites are supported?** below the field lists all of them. Direct links to video or audio files always work.

## Playlists and channels

A playlist or channel link lists all videos (up to the limit under *Admin → Settings*). Select single videos or all of them; with **Own folder** they are saved in a folder named after the playlist and numbered (`001 - …`). A channel link without a tab downloads the channel's videos.

## Presets

Presets decide quality and format: maximum resolution, container (MP4 plays everywhere, MKV, WebM), audio only (MP3, M4A, Opus, FLAC, WAV), subtitles, embedded thumbnail, metadata and chapters, SponsorBlock (cut out sponsor segments, intros …) and the file name template.

Global presets are set up by administrators and visible to everyone; each user can create their own and choose a default with **Make default**. Raw yt-dlp arguments are deliberately not possible, because options like `--exec` could run commands on the server.

## Library

All finished downloads – search, play in the browser, download to your device or delete (optionally with the file). Under **Playlists** every playlist is one collection that can be downloaded as a ZIP file in one go.

Not every browser plays every format (e.g. MKV in Safari); downloading always works.

## Sharing from the phone

Tubesy can be installed as an app (browser menu → *Install app* / *Add to Home Screen*). On Android it then appears in the share menu: share a video from the YouTube app to **Tubesy** and the check starts right away.

On the desktop, a bookmark works too: `https://<your-tubesy>/?url=` followed by the link opens Tubesy with it.

## Users, invitations and quotas

**Admin → Users:** create users, make them administrators, set a password, lock them or set a storage quota. Every user has their own folder and only sees their own downloads; administrators see everything under **Admin → All downloads**.

**Admin → Invitations:** create invitation links (for one or more people, valid 1/7/30 days or unlimited, optionally as administrator). The link is shown only once. Registration can also be *open* or *closed*.

## Account and sessions

Under **Account** everyone sees their storage use, changes their password and the language, and sees all devices they are signed in on – unknown sessions can be ended there.

## API keys and dashboards

**Account → API keys** creates a key for dashboards (e.g. [Heimdeck](https://github.com/MrLuigi938/heimdeck)), scripts or shortcuts – *read only* or *read & downloads*. Details: [API](api.md).

## Forgot your password?

An administrator can set a new password under **Admin → Users**. If no administrator can sign in any more, reset it on the server:

```sh
# Docker
docker exec -it tubesy python -m app.cli reset-password <user> <new-password>
# without Docker
sudo -u tubesy sh -c 'set -a; . /etc/default/tubesy; cd /opt/tubesy && venv/bin/python -m app.cli reset-password <user> <new-password>'
```

This also unlocks the account and signs out all of its sessions.
