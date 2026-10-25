# NAS and container managers

[← Installation](installation.md) · [Deutsch](../de/nas.md)

- [Synology (Container Manager)](#synology-container-manager)
- [QNAP (Container Station)](#qnap-container-station)
- [Unraid](#unraid)
- [TrueNAS SCALE](#truenas-scale)
- [Portainer](#portainer)

All of them use the same image, `ghcr.io/mrluigi938/tubesy:latest`, and the same two folders: `/config` (database, small) and `/downloads` (videos).

## Synology (Container Manager)

1. In **File Station** create the folders `docker/tubesy/config` and e.g. `video/tubesy`.
2. Find your user and group ID: **Control Panel → Terminal & SNMP** enable SSH, log in and run `id <your-user>`. On Synology this usually is `uid=1026` and `gid=100`.
3. **Container Manager → Project → Create**, name `tubesy`, path `docker/tubesy`, source *Create docker-compose.yml*:

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
         PUID: 1026
         PGID: 100
       volumes:
         - /volume1/docker/tubesy/config:/config
         - /volume1/video/tubesy:/downloads
   ```

4. Finish the wizard – the project starts on its own. Open `http://<nas-ip>:8080`.

If Tubesy reports missing write access: in File Station right-click the download folder → **Properties → Permission** and give your user *Read & Write*. Whether it works now is shown under **Admin → Settings → System → Write access**.

Update: **Container Manager → Project → tubesy → Action → Build** (pulls the new image) or via SSH `docker compose pull && docker compose up -d` in `/volume1/docker/tubesy`.

## QNAP (Container Station)

1. Create a shared folder for the videos and a folder for the configuration, e.g. `/share/Container/tubesy`.
2. **Container Station → Applications → Create**, name `tubesy`, and paste the Compose file from the Synology section with your paths (`/share/…`) and IDs (`id <user>` via SSH; often `PUID=1000`, `PGID=100`).
3. Open `http://<nas-ip>:8080`.

## Unraid

**Docker → Add Container**, switch to the advanced view and fill in:

| Field | Value |
|---|---|
| Repository | `ghcr.io/mrluigi938/tubesy:latest` |
| Network | `bridge` |
| Port | container `8080` → host `8080` |
| Path `/config` | `/mnt/user/appdata/tubesy` |
| Path `/downloads` | e.g. `/mnt/user/media/tubesy` |
| Variable `PUID` | `99` (nobody) |
| Variable `PGID` | `100` (users) |
| Variable `TZ` | your time zone |
| WebUI | `http://[IP]:[PORT:8080]/` |

Apply – Unraid pulls the image and starts the container. Updates appear on the Docker page as *update ready*.

## TrueNAS SCALE

**Apps → Discover Apps → Custom App** (or *Install via YAML* on newer versions with the Compose file above):

- Image `ghcr.io/mrluigi938/tubesy`, tag `latest`
- Port 8080 → 8080
- Storage: a dataset (host path) for `/config` and one for `/downloads`
- Environment: `PUID`/`PGID` of the dataset owner (the `apps` user is `568`), `TZ`

## Portainer

**Stacks → Add stack**, name `tubesy`, paste the Compose file from [Docker Compose](docker-compose.md), adjust the paths and deploy. For updates open the stack and click **Pull and redeploy**.

Next: [Reverse proxy](reverse-proxy.md) · [Updating](updating.md)
