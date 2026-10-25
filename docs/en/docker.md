# Docker (without Compose)

[← Installation](installation.md) · [Deutsch](../de/docker.md)

```sh
docker run -d --name tubesy --restart unless-stopped \
  -p 8080:8080 \
  -e TZ=Europe/London -e PUID=1000 -e PGID=1000 \
  -v /srv/tubesy/config:/config \
  -v /srv/media/videos:/downloads \
  ghcr.io/mrluigi938/tubesy:latest
```

Then open `http://<server-ip>:8080` and create the administrator account.

- `/config` holds the database, the yt-dlp cache and temporary files – keep it on a fast disk.
- `/downloads` is where the videos end up. Set `PUID`/`PGID` to the owner of that folder (`id <user>`).
- More variables: [Configuration](configuration.md).

## Update

```sh
docker pull ghcr.io/mrluigi938/tubesy:latest
docker rm -f tubesy
# run the same docker run command again
```

Your data stays in the two folders. With [Docker Compose](docker-compose.md) this is a single command.

## Podman

The same command works with `podman run`. With rootless Podman add `--userns keep-id` and leave out `PUID`/`PGID`, then the files belong to your user.
