# Einstellungen

[← Installation](installation.md) · [English](../en/configuration.md)

Die meisten Einstellungen nimmst du in der Weboberfläche unter **Verwaltung → Einstellungen** vor. Nur was vor dem Start feststehen muss, wird über Umgebungsvariablen gesetzt (Docker: `environment:` / `.env`, ohne Docker: `/etc/default/tubesy`).

## Umgebungsvariablen

| Variable | Standard | Bedeutung |
|---|---|---|
| `PUID` / `PGID` | `1000` | nur Docker: Benutzer/Gruppe, unter der Tubesy läuft und Dateien schreibt |
| `TZ` | `Etc/UTC` | Zeitzone, z. B. `Europe/Berlin` |
| `PORT` | `8080` | Port im Container bzw. des Dienstes |
| `YTDLP_AUTO_UPDATE` | `true` | yt-dlp bei jedem Start aktualisieren (Seiten ändern sich oft) |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Adresse/Netz deines Reverse Proxys; nur von dort wird `X-Forwarded-*` geglaubt. Die Compose-Datei setzt `172.16.0.0/12` (alle Docker-Netze) |
| `COOKIE_SECURE` | `auto` | `auto` setzt das Secure-Flag bei HTTPS-Anfragen, `true` immer |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | – | Administrator ohne Einrichtungsassistent anlegen (nur solange es keinen Benutzer gibt) |
| `CONFIG_DIR` | `/config` | Datenbank, Cache, temporäre Dateien |
| `DOWNLOAD_DIR` | `/downloads` | wohin die Videos gespeichert werden |

## Einstellungen in der Weboberfläche

**Verwaltung → Einstellungen**

| Einstellung | Standard | |
|---|---|---|
| Gleichzeitige Downloads (gesamt) | 3 | wie viele Downloads gleichzeitig laufen |
| Gleichzeitige Downloads pro Benutzer | 2 | damit eine große Playlist nicht alle anderen blockiert |
| Max. Einträge pro Playlist | 500 | längere Playlists und Kanäle werden abgeschnitten |
| Standard-Kontingent neuer Benutzer | unbegrenzt | in GB, pro Benutzer änderbar |
| Anmeldung gültig | 30 Tage | mit „Angemeldet bleiben“; sonst ein Tag |
| Mindestlänge Passwort (Benutzer) | 6 | Administratoren brauchen immer mindestens 6 |
| Auf neue Versionen hinweisen | an | fragt zweimal am Tag bei GitHub, siehe [Aktualisieren](updating.md) |

**Verwaltung → Einladungen:** Registrierung *geschlossen*, *nur mit Einladung* (Standard) oder *offen*.

Die Sprache wird pro Browser gewählt – bei der Einrichtung, auf der Anmeldeseite oder unter **Konto**.

## Daten und Sicherung

Alles außer den Videos liegt in **einem Ordner**: `/config` (Docker) bzw. `/var/lib/tubesy/config`. Zum Sichern Tubesy stoppen und diesen Ordner kopieren (`tubesy.db` ist die Datenbank). Die Videos sind ganz normale Dateien im Download-Ordner: `<download-ordner>/<benutzername>/…`.
