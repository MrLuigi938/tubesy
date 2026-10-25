# Docker Compose

[← Installation](installation.md) · [Deutsch](../de/docker-compose.md)

The image is built automatically for amd64 and arm64 and published as `ghcr.io/mrluigi938/tubesy`. Nothing is built on your server.

## 1. Create a folder with two files

```sh
mkdir tubesy && cd tubesy
```

`docker-compose.yml`:

```yaml
services:
  tubesy:
    image: ghcr.io/mrluigi938/tubesy:latest
    container_name: tubesy
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      TZ: Europe/London
      # Owner of the download folder (run `id <user>` on the server)
      PUID: 1000
      PGID: 1000
    volumes:
      - ./config:/config        # database and cache (small)
      - ./downloads:/downloads  # your videos
```

Or take the [docker-compose.yml](../../docker-compose.yml) and [.env.example](../../.env.example) from the repository: there all values are in a `.env` file next to it, and the file is already prepared for the SWAG reverse proxy.

## 2. Start

```sh
docker compose up -d
```

Open `http://<server-ip>:8080`, pick your language and create the administrator account. Invite more people under **Admin → Invitations**.

## Image tags

| Tag | Contains |
|---|---|
| `latest` | the newest stable release |
| `1.0` | the newest 1.0.x release (bug fixes only) |
| `1.0.0` | exactly this version |
| `edge` | the current development state of `main` – not for daily use |

All versions are listed under [Packages](https://github.com/MrLuigi938/tubesy/pkgs/container/tubesy).

## Download folder and permissions

Tubesy runs inside the container as `PUID`/`PGID` and writes the files with that owner. Set both to the user that owns the download folder:

```sh
id myuser                              # uid=1000(myuser) gid=1000(myuser)
ls -ldn /srv/media/videos              # who owns the folder?
```

An empty folder that Docker created itself is taken over automatically on the first start. An existing folder with files is never changed – if Tubesy reports *no write access*, see [Troubleshooting](troubleshooting.md#no-write-access-to-the-download-folder).

Every user gets a sub-folder: `/downloads/<username>/…`, playlists get a numbered folder of their own.

## Build the image yourself (optional)

```sh
git clone https://github.com/MrLuigi938/tubesy.git && cd tubesy
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

Next: [Configuration](configuration.md) · [Reverse proxy](reverse-proxy.md) · [Updating](updating.md)
