"""Pushes live updates to connected browsers over WebSockets."""
import asyncio
from dataclasses import dataclass

from fastapi import WebSocket


@dataclass(frozen=True)
class Client:
    ws: WebSocket
    user_id: int
    is_admin: bool


class EventHub:
    def __init__(self) -> None:
        self._clients: set[Client] = set()

    def add(self, client: Client) -> None:
        self._clients.add(client)

    def remove(self, client: Client) -> None:
        self._clients.discard(client)

    def disconnect_user(self, user_id: int) -> None:
        for client in [c for c in self._clients if c.user_id == user_id]:
            self._clients.discard(client)
            asyncio.create_task(client.ws.close(code=4401))

    async def publish(self, event: str, data: dict, owner_id: int) -> None:
        """Delivers to the owner and to every admin."""
        targets = [c for c in self._clients if c.user_id == owner_id or c.is_admin]
        if not targets:
            return
        message = {"event": event, "data": data}
        results = await asyncio.gather(*(c.ws.send_json(message) for c in targets), return_exceptions=True)
        for client, result in zip(targets, results):
            if isinstance(result, Exception):
                self._clients.discard(client)


hub = EventHub()
