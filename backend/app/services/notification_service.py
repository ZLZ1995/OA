from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.reminder_receipt import ReminderReceipt
from app.models.user_notification import UserNotification


def create_notification(
    db: Session,
    *,
    user_id: int,
    biz_type: str,
    biz_id: int,
    title: str,
    content: str,
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
        link_type=link_type,
        link_target_id=link_target_id,
        popup_flag=popup_flag,
    )
    db.add(row)
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
