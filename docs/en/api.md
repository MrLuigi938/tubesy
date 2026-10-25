# API

[← Usage](usage.md) · [Deutsch](../de/api.md)

A small, stable API for dashboards and automations. Create a key under **Account → API keys** and send it with every request:

```
X-Api-Key: tsy_…
```

or `Authorization: Bearer tsy_…`. A key acts with the rights of its user. *Read only* keys can only use `GET`.

| Endpoint | |
|---|---|
| `GET /api/v1/stats` | counts (waiting, active, finished, failed, finished in 24 h), storage and quota, current speed; administrators also get the whole instance |
| `GET /api/v1/queue?limit=10` | running and waiting downloads (administrators: of all users) |
| `POST /api/v1/download` | queue a link: `{"url": "https://…", "preset": "Audio (MP3)"}` – videos directly, playlists completely in their own folder. `preset` is a name or ID, empty = your default preset. Needs a *read & downloads* key |

Example:

```sh
curl -H "X-Api-Key: tsy_…" https://tubesy.example.com/api/v1/stats
curl -X POST -H "X-Api-Key: tsy_…" -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=…"}' https://tubesy.example.com/api/v1/download
```

The complete, interactive documentation of all endpoints is built in: `https://<your-tubesy>/api/docs`.
