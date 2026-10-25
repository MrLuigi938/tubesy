# API

[← Benutzung](usage.md) · [English](../en/api.md)

Eine kleine, stabile API für Dashboards und Automatisierungen. Unter **Konto → API-Schlüssel** einen Schlüssel erzeugen und bei jeder Anfrage mitschicken:

```
X-Api-Key: tsy_…
```

oder `Authorization: Bearer tsy_…`. Ein Schlüssel handelt mit den Rechten seines Benutzers. Schlüssel mit *Nur lesen* dürfen nur `GET`.

| Endpunkt | |
|---|---|
| `GET /api/v1/stats` | Zähler (wartend, aktiv, fertig, fehlgeschlagen, fertig in 24 h), Speicher und Kontingent, aktuelle Geschwindigkeit; Administratoren zusätzlich die ganze Instanz |
| `GET /api/v1/queue?limit=10` | laufende und wartende Downloads (Administratoren: aller Benutzer) |
| `POST /api/v1/download` | einen Link einreihen: `{"url": "https://…", "preset": "Audio (MP3)"}` – Videos direkt, Playlists komplett in einem eigenen Ordner. `preset` ist Name oder ID, leer = dein Standard-Preset. Braucht einen Schlüssel mit *Lesen & Downloads* |

Beispiel:

```sh
curl -H "X-Api-Key: tsy_…" https://tubesy.example.com/api/v1/stats
curl -X POST -H "X-Api-Key: tsy_…" -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=…"}' https://tubesy.example.com/api/v1/download
```

Die vollständige, interaktive Dokumentation aller Endpunkte ist eingebaut: `https://<dein-tubesy>/api/docs`.
