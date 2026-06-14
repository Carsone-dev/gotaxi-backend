from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self._connections[channel].add(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        self._connections[channel].discard(ws)
        if not self._connections[channel]:
            del self._connections[channel]

    async def broadcast(self, channel: str, message: dict):
        dead: list[WebSocket] = []
        for ws in self._connections.get(channel, set()).copy():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)

    async def send_to(self, channel: str, ws: WebSocket, message: dict):
        try:
            await ws.send_json(message)
        except Exception:
            self.disconnect(channel, ws)


manager = ConnectionManager()