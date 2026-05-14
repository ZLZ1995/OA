from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.services.realtime_notification_service import notification_connection_manager

router = APIRouter(tags=["通知实时通道"])


def _resolve_user_id(token: str | None) -> int | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
        return user.id if user else None
    finally:
        db.close()


@router.websocket("/ws/notifications")
async def notification_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    user_id = _resolve_user_id(token)
    if not user_id:
        await websocket.close(code=1008)
        return

    await notification_connection_manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_connection_manager.disconnect(user_id, websocket)
    except Exception:
        notification_connection_manager.disconnect(user_id, websocket)
        await websocket.close()
