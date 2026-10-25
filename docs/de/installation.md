# Installation

[← Zurück zur README](../../README.de.md) · [English](../en/installation.md)

Tubesy läuft auf **amd64** und **arm64** unter Linux: PCs, Server, NAS-Systeme und Raspberry Pi 4/5 mit 64-Bit-System.
Nach der Installation `http://<dein-server>:8080` öffnen und das Administrator-Konto anlegen. Dabei wird auch die Sprache der Oberfläche abgefragt (Deutsch oder Englisch).

## Welcher Weg passt zu mir?

| Du hast … | Nimm | Anleitung |
|---|---|---|
| Docker mit Compose (die meisten Heimserver) | `docker compose` | **[Docker Compose](docker-compose.md)** (empfohlen) |
| Docker ohne Compose | `docker run` | [Docker](docker.md) |
| Synology, QNAP, Unraid, TrueNAS, Portainer | die Container-App des NAS | [NAS und Container-Verwaltungen](nas.md) |
| Proxmox VE | eigener LXC-Container per Skript | [Proxmox VE](proxmox.md) |
| Debian, Ubuntu, Raspberry Pi OS – ohne Docker | Installationsskript mit systemd-Dienst | [Debian / Ubuntu](debian.md) |

In jeder Variante enthalten: yt-dlp (bei jedem Start aktualisiert), ffmpeg zum Zusammenführen und Umwandeln und Deno, das yt-dlp für YouTube braucht.

## Nach der Installation

- [Einstellungen](configuration.md) – Umgebungsvariablen und Einstellungen in der Weboberfläche
- [Reverse Proxy und HTTPS](reverse-proxy.md) – SWAG, Nginx Proxy Manager, Caddy, Traefik
- [Aktualisieren](updating.md)
- [Benutzung](usage.md) – Downloads, Presets, Bibliothek, Benutzer und Einladungen
- [Fehlerbehebung](troubleshooting.md)

## Voraussetzungen

- 1 CPU-Kern und 512 MB RAM reichen; für Umwandlungen (z. B. in MP3 oder MKV) und mehrere parallele Downloads sind 2 Kerne und 1 GB angenehm.
- Speicherplatz für deine Videos. Den Download-Ordner am besten auf eine Freigabe oder eine große Platte legen.
- Internetzugang nach außen (zu den Videoseiten und, für den Update-Hinweis, zu GitHub).
