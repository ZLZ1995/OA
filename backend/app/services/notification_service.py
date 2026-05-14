from __future__ import annotations

from datetime import datetime

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.reminder_receipt import ReminderReceipt
from app.models.user_notification import UserNotification
from app.services.realtime_notification_service import notification_connection_manager

PENDING_NOTIFICATION_EVENTS_KEY = "_pending_notification_events"
PENDING_READ_EVENTS_KEY = "_pending_notification_read_events"


def _append_session_event(db: Session, key: str, payload: dict) -> None:
    pending_items = db.info.setdefault(key, [])
    pending_items.append(payload)


def flush_notification_events(db: Session) -> None:
    for payload in db.info.pop(PENDING_NOTIFICATION_EVENTS_KEY, []):
        notification_connection_manager.push_after_commit(payload["user_id"], payload)
    for payload in db.info.pop(PENDING_READ_EVENTS_KEY, []):
        notification_connection_manager.push_after_commit(payload["user_id"], payload)


@event.listens_for(Session, "after_commit")
def _after_commit(session: Session) -> None:
    flush_notification_events(session)


@event.listens_for(Session, "after_rollback")
def _after_rollback(session: Session) -> None:
    session.info.pop(PENDING_NOTIFICATION_EVENTS_KEY, None)
    session.info.pop(PENDING_READ_EVENTS_KEY, None)


def create_notification(
    db: Session,
    *,
    user_id: int,
    biz_type: str,
    biz_id: int,
    title: str,
    content: str,
    message_type: str = "SYSTEM",
    priority: str = "NORMAL",
    sender_user_id: int | None = None,
    project_id: int | None = None,
    work_order_id: int | None = None,
    process_status: str = "PENDING",
    cc_flag: bool = False,
    group_key: str | None = None,
    link_type: str | None,
    link_target_id: int | None,
    popup_flag: bool = True,
) -> UserNotification:
    row = UserNotification(
        user_id=user_id,
        biz_type=biz_type,
        biz_id=biz_id,
        title=title,
        content=content,
        message_type=message_type,
        priority=priority,
        sender_user_id=sender_user_id,
        project_id=project_id,
        work_order_id=work_order_id,
        process_status=process_status,
        cc_flag=cc_flag,
        group_key=group_key,
        link_type=link_type,
        link_target_id=link_target_id,
        popup_flag=popup_flag,
    )
    db.add(row)
    db.flush()
    _append_session_event(
        db,
        PENDING_NOTIFICATION_EVENTS_KEY,
        {
            "event": "notification_created",
            "notification_id": row.id,
            "user_id": user_id,
            "message_type": row.message_type,
            "biz_type": row.biz_type,
            "project_id": row.project_id,
            "work_order_id": row.work_order_id,
            "created_at": row.created_at.isoformat() if row.created_at else datetime.utcnow().isoformat(),
        },
    )
    return row


def mark_notification_read(db: Session, notification: UserNotification) -> None:
    notification.is_read = True
    receipt = (
        db.query(ReminderReceipt)
        .filter(
            ReminderReceipt.reminder_event_id == notification.biz_id,
            ReminderReceipt.receiver_user_id == notification.user_id,
        )
        .order_by(ReminderReceipt.id.desc())
        .first()
    )
    if receipt:
        receipt.read_status = "READ"
    _append_session_event(
        db,
        PENDING_READ_EVENTS_KEY,
        {
            "event": "notification_read",
            "notification_ids": [notification.id],
            "user_id": notification.user_id,
            "read_at": datetime.utcnow().isoformat(),
        },
    )
