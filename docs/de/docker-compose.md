# Docker Compose

[← Installation](installation.md) · [English](../en/docker-compose.md)

Das Image wird automatisch für amd64 und arm64 gebaut und als `ghcr.io/mrluigi938/tubesy` veröffentlicht. Auf deinem Server wird nichts gebaut.

## 1. Ordner mit zwei Dateien anlegen

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
      TZ: Europe/Berlin
      # Besitzer des Download-Ordners (`id <benutzer>` auf dem Server ausführen)
      PUID: 1000
      PGID: 1000
    volumes:
      - ./config:/config        # Datenbank und Cache (klein)
      - ./downloads:/downloads  # deine Videos
```

Oder nimm [docker-compose.yml](../../docker-compose.yml) und [.env.example](../../.env.example) aus dem Repository: Dort stehen alle Werte in einer `.env`-Datei daneben.

## 2. Starten

```sh
docker compose up -d
```

`http://<server-ip>:8080` öffnen, Sprache wählen und das Administrator-Konto anlegen. Weitere Personen lädst du unter **Verwaltung → Einladungen** ein.

## Image-Tags

| Tag | Enthält |
|---|---|
| `latest` | die neueste stabile Version |
| `1.0` | die neueste Version 1.0.x (nur Fehlerbehebungen) |
| `1.0.0` | genau diese Version |
| `edge` | den aktuellen Entwicklungsstand von `main` – nicht für den Alltag |

Alle Versionen stehen unter [Packages](https://github.com/MrLuigi938/tubesy/pkgs/container/tubesy).

## Download-Ordner und Rechte

Tubesy läuft im Container als `PUID`/`PGID` und schreibt die Dateien mit diesem Besitzer. Setze beide auf den Benutzer, dem der Download-Ordner gehört:

```sh
id meinbenutzer                        # uid=1000(meinbenutzer) gid=1000(meinbenutzer)
ls -ldn /srv/medien/videos             # wem gehört der Ordner?
```

Ein leerer Ordner, den Docker selbst angelegt hat, wird beim ersten Start automatisch übernommen. Ein vorhandener Ordner mit Dateien wird nie verändert – meldet Tubesy *keine Schreibrechte*, siehe [Fehlerbehebung](troubleshooting.md#keine-schreibrechte-auf-den-download-ordner).

Jeder Benutzer bekommt einen Unterordner: `/downloads/<benutzername>/…`, Playlists einen eigenen nummerierten Ordner.

## Image selbst bauen (optional)

```sh
git clone https://github.com/MrLuigi938/tubesy.git && cd tubesy
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

Weiter: [Einstellungen](configuration.md) · [Reverse Proxy](reverse-proxy.md) · [Aktualisieren](updating.md)
