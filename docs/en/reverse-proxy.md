# Reverse proxy and HTTPS

[← Installation](installation.md) · [Deutsch](../de/reverse-proxy.md)

To reach Tubesy from the internet, put it behind a reverse proxy with HTTPS. Two things matter:

1. **WebSockets** must be passed through (`/api/ws`) – the live progress uses them.
2. **`FORWARDED_ALLOW_IPS`** must contain the address of the proxy, so Tubesy sees the real client IP (sign-in rate limit) and knows the request came via HTTPS (secure cookies). The Compose file already allows all Docker networks (`172.16.0.0/12`).

Keep registration on **Invitation only** (the default) for public instances. If Tubesy should only be reachable through the proxy, remove the `ports:` block from the Compose file.

- [SWAG](#swag)
- [Nginx Proxy Manager](#nginx-proxy-manager)
- [Caddy](#caddy)
- [Traefik](#traefik)
- [Plain nginx](#plain-nginx)
- [Anubis, Authelia and other protections](#anubis-authelia-and-other-protections)

## SWAG

Tubesy and [SWAG](https://docs.linuxserver.io/general/swag/) must share a Docker network. Add to your Tubesy `docker-compose.yml`:

```yaml
services:
  tubesy:
    # … as before …
    networks:
      - swag_default

networks:
  swag_default:
    external: true
```

Then copy [`docker/swag/tubesy.subdomain.conf.sample`](../../docker/swag/tubesy.subdomain.conf.sample) to `<swag-config>/nginx/proxy-confs/tubesy.subdomain.conf`, add `tubesy` to `SUBDOMAINS` in SWAG (or use a wildcard certificate) and run `docker restart swag`. Tubesy is then at `https://tubesy.<your-domain>`. Authelia/Authentik can be enabled in that file as an extra layer.

## Nginx Proxy Manager

**Hosts → Proxy Hosts → Add Proxy Host**: domain, scheme `http`, forward host `tubesy` (same Docker network) or the server IP, port `8080`, turn on **Websockets Support**. On the SSL tab request a certificate and enable *Force SSL*.

## Caddy

```caddy
tubesy.example.com {
    reverse_proxy tubesy:8080
}
```

Caddy passes WebSockets and the forwarded headers on its own.

## Traefik

```yaml
services:
  tubesy:
    # … as before, without ports: …
    labels:
      - traefik.enable=true
      - traefik.http.routers.tubesy.rule=Host(`tubesy.example.com`)
      - traefik.http.routers.tubesy.entrypoints=websecure
      - traefik.http.routers.tubesy.tls.certresolver=letsencrypt
      - traefik.http.services.tubesy.loadbalancer.server.port=8080
```

## Plain nginx

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

Without Docker the default `FORWARDED_ALLOW_IPS=127.0.0.1` already fits a proxy on the same machine.

## Anubis, Authelia and other protections

A bot protection or login in front of Tubesy (e.g. [Anubis](https://anubis.techaro.lol/), Authelia, Authentik, Cloudflare Access) is fine – Tubesy has its own logins anyway. Two things need an exception, because they are fetched **without** your browser's cookies:

- **Installing as an app:** the browser loads `/manifest.webmanifest`, `/sw.js` and the icons without signing in (on Android partly through Google's servers). If the protection answers with its own page, the install fails – Android shows a grey letter instead of the icon and says *This app cannot be installed*. *Account → App → Check what is missing* detects this.
- **Dashboards and scripts** using an API key (e.g. Heimdeck) call `/api/v1/…`.

For Anubis, add these rules at the top of the `bots` list in your policy file:

```yaml
bots:
  # Tubesy: app files for "Install app" and the API for dashboards
  - name: tubesy-app-files
    path_regex: ^/(manifest\.webmanifest|sw\.js|favicon\.svg|apple-touch-icon\.png|icon-[a-z0-9-]+\.png)$
    action: ALLOW
  - name: tubesy-api
    path_regex: ^/api/v1/
    action: ALLOW
  # … your other rules
```

With Authelia/Authentik, create a *bypass* rule for the same paths. Both paths contain nothing private: the app files are the same for every Tubesy, and the API needs a key.

