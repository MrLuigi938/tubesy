# Fehlerbehebung

[← Installation](installation.md) · [English](../en/troubleshooting.md)

**Verwaltung → Einstellungen → System** zeigt die wichtigsten Prüfungen auf einen Blick: yt-dlp-Version, ffmpeg, Deno, Schreibrechte auf den Download-Ordner und freien Speicher. **Infos kopieren** legt dort die Versionsangaben für eine Fehlermeldung in die Zwischenablage.

## Keine Schreibrechte auf den Download-Ordner

Meldung *„Keine Schreibrechte auf den Download-Ordner“* oder `Permission denied: '/downloads/…'`.

Tubesy schreibt als `PUID`/`PGID` (Docker) bzw. als Benutzer `tubesy` (ohne Docker). Auf dem Server:

```sh
id <benutzer>                     # uid/gid -> PUID/PGID
ls -ldn /pfad/zu/downloads        # wem gehört der Ordner?
sudo chown -R 1000:1000 /pfad/zu/downloads   # eigene Werte einsetzen
docker restart tubesy
```

Auf einer Synology alternativ: File Station → Ordner → Eigenschaften → Berechtigung → dem Benutzer *Lesen/Schreiben* geben. Proxmox mit Host-Ordner: siehe [Proxmox](proxmox.md#videos-auf-einem-nas-oder-einer-großen-platte-speichern).

## YouTube-Downloads scheitern

- yt-dlp aktualisieren: **Verwaltung → Einstellungen → System → yt-dlp → Aktualisieren** (passiert auch bei jedem Start).
- *Sign in to confirm you're not a bot* / HTTP 403: YouTube bremst die IP-Adresse des Servers. Eine Weile warten, weniger Videos gleichzeitig laden (*Verwaltung → Einstellungen*) oder eine andere Verbindung nutzen.
- *Private video* / *Video unavailable* / Altersbeschränkung: Solche Videos kann Tubesy ohne Anmeldung nicht laden.
- Deno zeigt *fehlt* in den Systemprüfungen: nur beim Start aus dem Quellcode möglich; [Deno](https://deno.com) installieren.

## Der Fortschritt bewegt sich nicht / der Punkt oben ist orange

Die Live-Verbindung (WebSocket) kommt nicht durch. Hinter einem Reverse Proxy müssen WebSockets eingeschaltet sein – siehe [Reverse Proxy](reverse-proxy.md).

## Hinter HTTPS immer wieder abgemeldet

`FORWARDED_ALLOW_IPS` auf die Adresse deines Proxys setzen (Compose: `172.16.0.0/12` deckt Docker-Netze schon ab), oder `COOKIE_SECURE=false`, wenn du Tubesy nur per HTTP aufrufst.

## Zu viele Anmeldeversuche

Nach mehreren falschen Passwörtern ist die Anmeldung für diesen Benutzer bzw. diese Adresse 15 Minuten gesperrt. Warten oder von einem Administrator ein neues Passwort setzen lassen. Siehe auch [Passwort vergessen?](usage.md#passwort-vergessen).

## Protokolle

```sh
docker logs -f tubesy          # Docker
journalctl -u tubesy -f        # ohne Docker
```

Kommst du nicht weiter? [Fehler melden](https://github.com/MrLuigi938/tubesy/issues/new) mit den kopierten Infos.
