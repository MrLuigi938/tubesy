# Debian, Ubuntu, Raspberry Pi OS (ohne Docker)

[← Installation](installation.md) · [English](../en/debian.md)

Ein Installationsskript richtet Tubesy als systemd-Dienst ein. Unterstützt: **Debian 12/13, Ubuntu 24.04 oder neuer, Raspberry Pi OS (64 Bit, ab Bookworm)** – Tubesy braucht Python 3.11+.

```sh
curl -fsSL https://github.com/MrLuigi938/tubesy/releases/latest/download/install.sh -o install.sh
sudo sh install.sh
```

Das Skript

1. installiert Python, ffmpeg und Deno (JavaScript-Laufzeit, die yt-dlp für YouTube braucht),
2. lädt die neueste Version nach `/opt/tubesy` und legt eine Python-Umgebung dafür an,
3. legt den Systembenutzer `tubesy`, den Datenordner `/var/lib/tubesy` und den Dienst `tubesy` an,
4. zeigt die Adresse an – öffnen und das Administrator-Konto anlegen.

## Optionen für die Erstinstallation

```sh
sudo TUBESY_PORT=8090 TUBESY_DOWNLOAD_DIR=/srv/medien/videos sh install.sh
```

| Variable | Standard | Bedeutung |
|---|---|---|
| `TUBESY_PORT` | `8080` | Port der Weboberfläche |
| `TUBESY_DOWNLOAD_DIR` | `/var/lib/tubesy/downloads` | wohin die Videos gespeichert werden |
| `TUBESY_VERSION` | `latest` | eine feste Version, z. B. `1.0.0` |
| `TUBESY_UID` | – | feste Benutzer-ID für `tubesy`, z. B. passend zum Besitzer einer Freigabe |
| `TUBESY_PACKAGE` | – | Pfad zu einer heruntergeladenen `tubesy.tar.gz` (Offline-Installation) |

Ein **vorhandener** Download-Ordner mit Dateien wird nie verändert. Gib ihn bei Bedarf dem Benutzer `tubesy`: `sudo chown -R tubesy:tubesy /srv/medien/videos`.

## Wo liegt was?

| Pfad | Inhalt |
|---|---|
| `/opt/tubesy` | Programm und Python-Umgebung (wird bei Updates ersetzt) |
| `/var/lib/tubesy/config` | Datenbank, Cache |
| `/var/lib/tubesy/downloads` | Videos (sofern nicht anders gesetzt) |
| `/etc/default/tubesy` | Einstellungen, siehe [Einstellungen](configuration.md) |

```sh
systemctl status tubesy        # läuft es?
journalctl -u tubesy -f        # Protokoll
sudo systemctl restart tubesy  # nach Änderungen an /etc/default/tubesy
```

## Aktualisieren und entfernen

```sh
sudo sh install.sh             # auf die neueste Version aktualisieren
sudo sh install.sh uninstall   # Programm und Dienst entfernen – Daten und Videos bleiben
```

## Andere Distributionen

Das Skript nutzt `apt`. Auf anderen systemd-Distributionen (Fedora, Arch, openSUSE …) ist [Docker](docker-compose.md) oder Podman der einfachste Weg. Manuell: Python 3.11+, ffmpeg und Deno aus der Paketverwaltung, dann `tubesy.tar.gz` aus dem [Release](https://github.com/MrLuigi938/tubesy/releases/latest) entpacken, `python3 -m venv venv && venv/bin/pip install -r requirements.txt` und `venv/bin/uvicorn app.main:app --port 8080` mit den Variablen aus [Einstellungen](configuration.md) starten.
