from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.reminder_event import ReminderEvent
from app.models.reminder_receipt import ReminderReceipt
from app.models.user import User
from app.models.user_notification import UserNotification
from app.services.notification_service import mark_notification_read


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def test_mark_notification_read_updates_receipt() -> None:
    db = _build_session()
    user = User(username="notify", password_hash="x", real_name="Notify", is_active=True)
    db.add(user)
    db.flush()
    event = ReminderEvent(
        project_id=1,
        work_order_id=1,
        current_handler_user_id=user.id,
        initiator_user_id=user.id,
        initiator_role_type="PROJECT_LEADER",
        trigger_type="MANUAL",
        current_status="FIRST_REVIEWING",
        overdue_seconds=3600,
        day_remind_seq=1,
        handler_cycle_key="1:1:FIRST_REVIEWING",
    )
    db.add(event)
    db.flush()
    receipt = ReminderReceipt(
        reminder_event_id=event.id,
        receiver_user_id=user.id,
        receiver_type="PRIMARY",
        channel="IN_APP",
        delivery_status="SENT",
        read_status="UNREAD",
    )
    notification = UserNotification(
        user_id=user.id,
        biz_type="WORK_ORDER_REMINDER",
        biz_id=event.id,
        title="title",
        content="content",
        is_read=False,
        popup_flag=True,
    )
    db.add(receipt)
    db.add(notification)
    db.commit()

    mark_notification_read(db, notification)
    db.commit()

    assert notification.is_read is True
    assert receipt.read_status == "READ"
