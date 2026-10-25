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
