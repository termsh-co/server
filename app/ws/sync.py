from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.config import settings

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        if user_id in self._connections:
            self._connections[user_id] = [c for c in self._connections[user_id] if c != ws]

    async def notify(self, user_id: str, event: str, data: dict) -> None:
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_json({"event": event, "data": data})
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/sync/ws")
async def sync_websocket(ws: WebSocket, token: str | None = None) -> None:
    if not token:
        await ws.close(code=4001, reason="Token gerekli")
        return

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        await ws.close(code=4001, reason="Geçersiz token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await ws.close(code=4001, reason="Geçersiz token")
        return

    await manager.connect(user_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, ws)
