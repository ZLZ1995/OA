from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from threading import Lock

from fastapi import WebSocket


class NotificationConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = Lock()

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections[user_id].add(websocket)
        await websocket.send_text(
            json.dumps(
                {
                    "event": "hello",
                    "user_id": user_id,
                    "connected_at": datetime.utcnow().isoformat(),
                }
            )
        )

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        with self._lock:
            sockets = self._connections.get(user_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(user_id, None)

    async def push_to_user(self, user_id: int, payload: dict) -> None:
        with self._lock:
            sockets = list(self._connections.get(user_id, set()))
        stale_sockets: list[WebSocket] = []
        message = json.dumps(payload, default=str)
        for websocket in sockets:
            try:
                await websocket.send_text(message)
            except Exception:
                stale_sockets.append(websocket)
        for websocket in stale_sockets:
            self.disconnect(user_id, websocket)

    def push_after_commit(self, user_id: int, payload: dict) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.push_to_user(user_id, payload))
        except RuntimeError:
            asyncio.run(self.push_to_user(user_id, payload))


notification_connection_manager = NotificationConnectionManager()
