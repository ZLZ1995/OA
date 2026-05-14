from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.role import Role
from app.models.user import User
from app.models.user_notification import UserNotification
from app.models.user_role import UserRole
from app.models.reminder_event import ReminderEvent
from app.models.reminder_receipt import ReminderReceipt
from app.models.project import Project
from app.models.work_order import WorkOrder
from app.models.workflow_log import WorkflowLog
from app.api.v1.notifications import (
    batch_read_notification,
    get_notification_detail,
    get_notification_stats,
    get_notification_timeline,
    list_my_notifications,
)
from app.schemas.notification import NotificationBatchReadRequest


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_user(db: Session) -> User:
    user = User(username="notify-user", password_hash="x", real_name="Notify User", is_active=True)
    db.add(user)
    db.flush()
    role = Role(code="PROJECT_LEADER", name="项目负责人", description="", is_system_fixed=True)
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


def _seed_notifications(db: Session, user: User) -> None:
    now = datetime.now()
    db.add_all([
        UserNotification(
            user_id=user.id,
            biz_type="WORK_ORDER_REMINDER",
            biz_id=1,
            title="催办提醒1",
            content="请处理工单1",
            message_type="REMINDER",
            priority="IMPORTANT",
            sender_user_id=user.id,
            project_id=11,
            work_order_id=21,
            process_status="PENDING",
            cc_flag=False,
            group_key="WORK_ORDER:21",
            is_read=False,
            popup_flag=True,
            created_at=now,
        ),
        UserNotification(
            user_id=user.id,
            biz_type="SYSTEM_NOTICE",
            biz_id=2,
            title="系统通知",
            content="系统维护通知",
            message_type="SYSTEM",
            priority="NORMAL",
            sender_user_id=user.id,
            project_id=12,
            work_order_id=22,
            process_status="PROCESSED",
            cc_flag=True,
            group_key="WORK_ORDER:22",
            is_read=True,
            popup_flag=False,
            created_at=now - timedelta(days=1),
        ),
    ])
    db.commit()


def test_list_notifications_supports_filters_and_paging() -> None:
    db = _build_session()
    user = _seed_user(db)
    _seed_notifications(db, user)

    result = list_my_notifications(
        tab="unread",
        keyword=None,
        message_type="REMINDER",
        priority=None,
        read_status=None,
        project_id=None,
        work_order_id=None,
        page=1,
        page_size=20,
        db=db,
        current_user=user,
    )

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].message_type == "REMINDER"


def test_notification_stats_returns_counts() -> None:
    db = _build_session()
    user = _seed_user(db)
    _seed_notifications(db, user)

    result = get_notification_stats(db=db, current_user=user)

    assert result.unread_count == 1
    assert result.today_reminder_count == 1
    assert result.today_new_count >= 1


def test_batch_read_updates_selected_notifications() -> None:
    db = _build_session()
    user = _seed_user(db)
    _seed_notifications(db, user)
    rows = db.query(UserNotification).filter(UserNotification.user_id == user.id, UserNotification.is_read.is_(False)).all()

    batch_read_notification(
        payload=NotificationBatchReadRequest(notification_ids=[row.id for row in rows]),
        db=db,
        current_user=user,
    )

    refreshed = db.query(UserNotification).filter(UserNotification.user_id == user.id).all()
    assert all(row.is_read for row in refreshed)


def test_notification_detail_and_timeline() -> None:
    db = _build_session()
    user = _seed_user(db)
    _seed_notifications(db, user)
    db.add(
        Project(
            id=11,
            project_code="P-DETAIL",
            project_name="Detail Project",
            client_name="Detail Client",
            business_user_id=user.id,
            project_leader_id=user.id,
        )
    )
    db.add(
        WorkOrder(
            id=21,
            work_order_no="WO-DETAIL",
            project_id=11,
            title="Detail Work Order",
            current_status="CONTRACT_REVIEWING",
            current_handler_user_id=user.id,
            initiator_user_id=user.id,
            project_leader_id=user.id,
        )
    )
    db.flush()
    event = ReminderEvent(
        project_id=11,
        work_order_id=21,
        current_handler_user_id=user.id,
        initiator_user_id=user.id,
        initiator_role_type="PROJECT_LEADER",
        trigger_type="MANUAL",
        current_status="CONTRACT_REVIEWING",
        overdue_seconds=3600,
        comment="请及时处理",
        day_remind_seq=1,
        handler_cycle_key="21:1:CONTRACT_REVIEWING",
    )
    db.add(event)
    db.flush()
    receipt = ReminderReceipt(
        reminder_event_id=event.id,
        receiver_user_id=user.id,
        receiver_type="PRIMARY",
        channel="IN_APP",
        delivery_status="SENT",
        read_status="READ",
    )
    db.add(receipt)
    db.add(
        WorkflowLog(
            work_order_id=21,
            from_status="WORK_ORDER_CREATED",
            to_status="CONTRACT_REVIEWING",
            action_type="SUBMIT_CONTRACT_REVIEW",
            operator_user_id=user.id,
            remark="模拟日志",
        )
    )
    notification = UserNotification(
        user_id=user.id,
        biz_type="WORK_ORDER_REMINDER",
        biz_id=event.id,
        title="催办详情",
        content="详情内容",
        message_type="REMINDER",
        priority="IMPORTANT",
        sender_user_id=user.id,
        project_id=11,
        work_order_id=21,
        process_status="PENDING",
        cc_flag=False,
        group_key="WORK_ORDER:21",
        is_read=False,
        popup_flag=True,
    )
    db.add(notification)
    db.commit()

    detail = get_notification_detail(notification.id, db=db, current_user=user)
    timeline = get_notification_timeline(notification.id, db=db, current_user=user)

    assert detail.title == "催办详情"
    assert detail.project_id == 11
    assert detail.project_code == "P-DETAIL"
    assert detail.project_name == "Detail Project"
    assert detail.work_order_no == "WO-DETAIL"
    assert detail.work_order_title == "Detail Work Order"
    assert detail.current_status == "CONTRACT_REVIEWING"
    assert detail.current_handler_user_name == "Notify User"
    assert len(timeline.items) >= 2


def test_reminder_process_status_derives_read_and_processed() -> None:
    db = _build_session()
    user = _seed_user(db)
    unread = UserNotification(
        user_id=user.id,
        biz_type="WORK_ORDER_REMINDER",
        biz_id=300,
        title="未读提醒",
        content="内容",
        message_type="REMINDER",
        priority="IMPORTANT",
        sender_user_id=user.id,
        project_id=1,
        work_order_id=99,
        process_status="PENDING",
        cc_flag=False,
        group_key="WORK_ORDER:99",
        is_read=False,
        popup_flag=True,
    )
    read_row = UserNotification(
        user_id=user.id,
        biz_type="WORK_ORDER_REMINDER",
        biz_id=301,
        title="已读提醒",
        content="内容",
        message_type="REMINDER",
        priority="IMPORTANT",
        sender_user_id=user.id,
        project_id=1,
        work_order_id=100,
        process_status="PENDING",
        cc_flag=False,
        group_key="WORK_ORDER:100",
        is_read=True,
        popup_flag=True,
    )
    processed_row = UserNotification(
        user_id=user.id,
        biz_type="WORK_ORDER_REMINDER",
        biz_id=302,
        title="已处理提醒",
        content="内容",
        message_type="REMINDER",
        priority="IMPORTANT",
        sender_user_id=user.id,
        project_id=1,
        work_order_id=101,
        process_status="PENDING",
        cc_flag=False,
        group_key="WORK_ORDER:101",
        is_read=True,
        popup_flag=True,
    )
    db.add_all([unread, read_row, processed_row])
    db.flush()
    db.add(
        WorkflowLog(
            work_order_id=101,
            from_status="A",
            to_status="B",
            action_type="APPROVE",
            operator_user_id=user.id,
        )
    )
    processed_row.created_at = processed_row.created_at - timedelta(hours=2)
    db.commit()

    unread_result = list_my_notifications(
        tab="all",
        keyword=None,
        message_type=None,
        priority=None,
        read_status=None,
        project_id=None,
        work_order_id=None,
        page=1,
        page_size=20,
        db=db,
        current_user=user,
    )
    by_title = {item.title: item.process_status for item in unread_result.items}

    assert by_title["未读提醒"] == "PENDING"
    assert by_title["已读提醒"] == "READ"
    assert by_title["已处理提醒"] == "PROCESSED"
