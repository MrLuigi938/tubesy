# Aktualisieren

[← Installation](installation.md) · [English](../en/updating.md)

Tubesy sagt dir, wenn eine neue Version da ist: Zweimal am Tag fragt der Server bei GitHub nach der neuesten Version. Administratoren sehen dann einen roten Punkt bei **Verwaltung** und die neue Version in der Fußzeile; **Verwaltung → Einstellungen → Info** verlinkt die Neuerungen. Es wird nichts automatisch installiert, und die Prüfung lässt sich dort abschalten.

Einer stabilen Version werden nur stabile Versionen angeboten, einer Beta (z. B. `1.1.0-beta.1`) auch neuere Betas. `edge` und selbst gebaute Versionen prüfen nicht.

## Docker Compose

```sh
docker compose pull
docker compose up -d
```

## Docker

```sh
docker pull ghcr.io/mrluigi938/tubesy:latest
docker rm -f tubesy
# mit demselben docker-run-Befehl wieder starten
```

## Synology, QNAP, Unraid, Portainer …

Siehe [NAS und Container-Verwaltungen](nas.md) – meist *Pull/Redeploy* in der Container-App.

## Debian, Ubuntu, Proxmox LXC

Das Installationsskript erneut ausführen:

```sh
sudo sh install.sh                                  # im Container / auf dem Rechner
pct exec <CTID> -- sh /root/tubesy-install.sh       # Proxmox: vom Host aus
```

## yt-dlp

yt-dlp wird unabhängig von Tubesy bei jedem Start aktualisiert (`YTDLP_AUTO_UPDATE=true`) und per **Verwaltung → Einstellungen → System → yt-dlp → Aktualisieren**. Wenn YouTube-Downloads plötzlich scheitern, ist das der erste Versuch.

## Version festhalten

Statt `latest` ein Versions-Tag verwenden (z. B. `ghcr.io/mrluigi938/tubesy:1.0` für nur Fehlerbehebungen von 1.0) bzw. `TUBESY_VERSION=1.0.0` beim Installationsskript. Alle Versionen: [GitHub Releases](https://github.com/MrLuigi938/tubesy/releases).
