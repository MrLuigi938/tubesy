# Reverse Proxy und HTTPS

[← Installation](installation.md) · [English](../en/reverse-proxy.md)

Um Tubesy aus dem Internet zu erreichen, stell es hinter einen Reverse Proxy mit HTTPS. Zwei Dinge sind wichtig:

1. **WebSockets** müssen durchgereicht werden (`/api/ws`) – der Live-Fortschritt nutzt sie.
2. **`FORWARDED_ALLOW_IPS`** muss die Adresse des Proxys enthalten, damit Tubesy die echte Client-IP sieht (Login-Sperre) und erkennt, dass die Anfrage per HTTPS kam (sichere Cookies). Die Compose-Datei erlaubt bereits alle Docker-Netze (`172.16.0.0/12`).

Lass die Registrierung bei öffentlichen Instanzen auf **Nur mit Einladung** (Standard). Soll Tubesy nur noch über den Proxy erreichbar sein, den `ports:`-Block aus der Compose-Datei entfernen.

- [SWAG](#swag)
- [Nginx Proxy Manager](#nginx-proxy-manager)
- [Caddy](#caddy)
- [Traefik](#traefik)
- [Einfaches nginx](#einfaches-nginx)
- [Anubis, Authelia und andere Schutzschichten](#anubis-authelia-und-andere-schutzschichten)

## SWAG

Tubesy und [SWAG](https://docs.linuxserver.io/general/swag/) müssen in einem gemeinsamen Docker-Netzwerk sein. Ergänze in der `docker-compose.yml` von Tubesy:

```yaml
services:
  tubesy:
    # … wie bisher …
    networks:
      - swag_default

networks:
  swag_default:
    external: true
```

Dann [`docker/swag/tubesy.subdomain.conf.sample`](../../docker/swag/tubesy.subdomain.conf.sample) nach `<swag-config>/nginx/proxy-confs/tubesy.subdomain.conf` kopieren, in SWAG `tubesy` zu `SUBDOMAINS` hinzufügen (oder ein Wildcard-Zertifikat nutzen) und `docker restart swag` ausführen. Tubesy ist dann unter `https://tubesy.<deine-domain>` erreichbar. Authelia/Authentik lässt sich in der Datei als zusätzlicher Schutz einschalten.

Das Docker-Standardnetz `bridge` lässt sich in Compose nicht mit anderen Netzen kombinieren. Falls nötig, nach dem Start `docker network connect bridge tubesy` ausführen.

## Nginx Proxy Manager

**Hosts → Proxy Hosts → Add Proxy Host**: Domain, Schema `http`, Forward-Host `tubesy` (gleiches Docker-Netz) oder die Server-IP, Port `8080`, **Websockets Support** einschalten. Im Reiter SSL ein Zertifikat anfordern und *Force SSL* aktivieren.

## Caddy

```caddy
tubesy.example.com {
    reverse_proxy tubesy:8080
}
```

Caddy reicht WebSockets und die Forwarded-Header von selbst weiter.

## Traefik

```yaml
services:
  tubesy:
    # … wie bisher, ohne ports: …
    labels:
      - traefik.enable=true
      - traefik.http.routers.tubesy.rule=Host(`tubesy.example.com`)
      - traefik.http.routers.tubesy.entrypoints=websecure
      - traefik.http.routers.tubesy.tls.certresolver=letsencrypt
      - traefik.http.services.tubesy.loadbalancer.server.port=8080
```

## Einfaches nginx

```nginx
server {
    listen 443 ssl;
    server_name tubesy.example.com;
    # ssl_certificate …

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 1h;
    }
}
```

Ohne Docker passt der Standard `FORWARDED_ALLOW_IPS=127.0.0.1` bereits zu einem Proxy auf demselben Rechner.

## Anubis, Authelia und andere Schutzschichten

Ein Bot-Schutz oder Login vor Tubesy (z. B. [Anubis](https://anubis.techaro.lol/), Authelia, Authentik, Cloudflare Access) ist kein Problem – Tubesy hat ohnehin eigene Logins. Zwei Dinge brauchen aber eine Ausnahme, weil sie **ohne** die Cookies deines Browsers abgerufen werden:

- **Als App installieren:** Der Browser lädt `/manifest.webmanifest`, `/sw.js` und die Symbole ohne Anmeldung (unter Android teils über Google-Server). Antwortet der Schutz mit seiner eigenen Seite, scheitert die Installation – Android zeigt dann einen grauen Buchstaben statt des Symbols und meldet *Diese App kann nicht installiert werden*. *Konto → App → Prüfen, was fehlt* erkennt das.
- **Dashboards und Skripte** mit API-Schlüssel (z. B. Heimdeck) rufen `/api/v1/…` auf.

Bei Anubis diese Regeln oben in die `bots`-Liste deiner Richtliniendatei eintragen:

```yaml
bots:
  # Tubesy: App-Dateien für „App installieren“ und die API für Dashboards
  - name: tubesy-app-files
    path_regex: ^/(manifest\.webmanifest|sw\.js|favicon\.svg|apple-touch-icon\.png|icon-[a-z0-9-]+\.png)$
    action: ALLOW
  - name: tubesy-api
    path_regex: ^/api/v1/
    action: ALLOW
  # … deine übrigen Regeln
```

Bei Authelia/Authentik für dieselben Pfade eine *bypass*-Regel anlegen. Beide Pfade enthalten nichts Privates: Die App-Dateien sind bei jedem Tubesy gleich, und die API braucht einen Schlüssel.

