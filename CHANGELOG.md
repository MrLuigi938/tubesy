# Changelog

All notable changes to Tubesy. Versions follow [semantic versioning](https://semver.org/).

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
