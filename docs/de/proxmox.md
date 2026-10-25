# Proxmox VE: als eigener LXC-Container

[← Installation](installation.md) · [English](../en/proxmox.md)

Ein Skript legt einen unprivilegierten Debian-Container an, der mit dem Host startet, und installiert Tubesy darin mit dem [Debian-Installationsskript](debian.md). Ausführen in der **Shell deines Proxmox-Knotens** (als root):

```sh
curl -fsSL https://github.com/MrLuigi938/tubesy/releases/latest/download/proxmox-lxc.sh -o proxmox-lxc.sh
sh proxmox-lxc.sh
```

Das Skript fragt nach dem Containernamen, nimmt die nächste freie ID, lädt bei Bedarf die neueste Debian-Vorlage und zeigt am Ende Adresse und root-Passwort des Containers an.

## Optionen

Vor den Befehl setzen, z. B. `CTID=120 IP=192.168.1.50/24 GATEWAY=192.168.1.1 sh proxmox-lxc.sh`:

| Variable | Standard | Bedeutung |
|---|---|---|
| `CTID` | nächste freie ID | Container-ID |
| `CT_HOSTNAME` | `tubesy` (wird gefragt) | Name des Containers |
| `CORES` / `MEMORY` | `2` / `1024` | CPU-Kerne, RAM in MB |
| `DISK` | `8` | Plattengröße in GB – hier landen die Downloads, außer `HOST_DOWNLOADS` ist gesetzt |
| `STORAGE` | erster Container-Speicher | wo die Platte angelegt wird |
| `BRIDGE` | `vmbr0` | Netzwerk-Bridge |
| `IP` / `GATEWAY` | `dhcp` | feste Adresse, z. B. `192.168.1.50/24` |
| `HOST_DOWNLOADS` | – | Ordner auf dem Proxmox-Host, in den die Videos sollen (siehe unten) |
| `TUBESY_PORT` | `8080` | Port der Weboberfläche |
| `ROOT_PASSWORD` | zufällig | root-Passwort des Containers |
| `SSH_KEY_FILE` | – | öffentlicher Schlüssel für SSH, z. B. `~/.ssh/id_ed25519.pub` |

## Videos auf einem NAS oder einer großen Platte speichern

Zuerst die Freigabe auf dem Proxmox-Host einbinden (z. B. **Rechenzentrum → Storage → Hinzufügen → SMB/CIFS oder NFS**, sie erscheint dann unter `/mnt/pve/<name>`), dann:

```sh
HOST_DOWNLOADS=/mnt/pve/nas/videos sh proxmox-lxc.sh
```

Der Ordner wird als Download-Ordner in den Container eingehängt. Unprivilegierte Container verschieben Benutzer-IDs um 100000, der Tubesy-Benutzer (innen ID 1000) ist auf dem Host also ID **101000**. Meldet Tubesy fehlende Schreibrechte, gib den Ordner auf dem Host dieser ID:

```sh
chown -R 101000:101000 /mnt/pve/nas/videos
```

Bei SMB/CIFS-Freigaben stattdessen `uid=101000,gid=101000` in den Mount-Optionen setzen.

## Im Container anmelden

Proxmox → Container → **Konsole**, Benutzer `root` mit dem am Ende angezeigten Passwort. Ändern mit `passwd`. Die Einstellungen stehen in `/etc/default/tubesy` (danach `systemctl restart tubesy`), das Protokoll zeigt `journalctl -u tubesy -f`.

## Aktualisieren

Auf dem Proxmox-Host:

```sh
pct exec <CTID> -- sh /root/tubesy-install.sh
```

oder im Container `sh /root/tubesy-install.sh`. Siehe [Aktualisieren](updating.md).
