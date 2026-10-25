# Docker (ohne Compose)

[← Installation](installation.md) · [English](../en/docker.md)

```sh
docker run -d --name tubesy --restart unless-stopped \
  -p 8080:8080 \
  -e TZ=Europe/Berlin -e PUID=1000 -e PGID=1000 \
  -v /srv/tubesy/config:/config \
  -v /srv/medien/videos:/downloads \
  ghcr.io/mrluigi938/tubesy:latest
```

Dann `http://<server-ip>:8080` öffnen und das Administrator-Konto anlegen.

- `/config` enthält Datenbank, yt-dlp-Cache und temporäre Dateien – gerne auf einer schnellen Platte.
- `/downloads` ist das Ziel der Videos. `PUID`/`PGID` auf den Besitzer dieses Ordners setzen (`id <benutzer>`).
- Weitere Variablen: [Einstellungen](configuration.md).

## Aktualisieren

```sh
docker pull ghcr.io/mrluigi938/tubesy:latest
docker rm -f tubesy
# denselben docker-run-Befehl erneut ausführen
```

Deine Daten bleiben in den beiden Ordnern. Mit [Docker Compose](docker-compose.md) ist das ein einziger Befehl.

## Podman

Derselbe Befehl funktioniert mit `podman run`. Bei rootless Podman `--userns keep-id` ergänzen und `PUID`/`PGID` weglassen, dann gehören die Dateien deinem Benutzer.
