from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.reminder_event import ReminderEvent
from app.models.reminder_receipt import ReminderReceipt
from app.models.project import Project
from app.models.user import User
from app.models.user_notification import UserNotification
from app.models.work_order import WorkOrder
from app.models.workflow_log import WorkflowLog
from app.schemas.notification import (
    NotificationBatchReadRequest,
    NotificationDetailResponse,
    NotificationItem,
    NotificationListResponse,
    NotificationReadResponse,
    NotificationStatsResponse,
    NotificationTimelineItem,
    NotificationTimelineResponse,
)
from app.services.notification_service import mark_notification_read

router = APIRouter(prefix="/notifications", tags=["消息中心"])


def _derive_process_status(db: Session, row: UserNotification) -> str:
    if row.process_status == "PROCESSED":
        return row.process_status
    if row.message_type == "REMINDER":
        if row.is_read:
            base_status = "READ"
        else:
            base_status = "PENDING"
        if row.work_order_id:
            latest_log = (
                db.query(WorkflowLog)
                .filter(WorkflowLog.work_order_id == row.work_order_id)
                .order_by(WorkflowLog.created_at.desc(), WorkflowLog.id.desc())
                .first()
            )
            if latest_log and latest_log.created_at > row.created_at:
                return "PROCESSED"
        return base_status
    if row.message_type == "WORKFLOW":
        return "READ" if row.is_read else "PENDING"
    return "READ" if row.is_read else row.process_status


def _build_notification_item(db: Session, row: UserNotification) -> NotificationItem:
    sender_name = db.query(User.real_name).filter(User.id == row.sender_user_id).scalar() if row.sender_user_id else None
    receiver_name = db.query(User.real_name).filter(User.id == row.user_id).scalar()
    project = db.query(Project).filter(Project.id == row.project_id).first() if row.project_id else None
    work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first() if row.work_order_id else None
    current_handler_name = (
        db.query(User.real_name).filter(User.id == work_order.current_handler_user_id).scalar()
        if work_order and work_order.current_handler_user_id
        else None
    )
    return NotificationItem(
        id=row.id,
        biz_type=row.biz_type,
        biz_id=row.biz_id,
        title=row.title,
        content=row.content,
        message_type=row.message_type,
        priority=row.priority,
        sender_user_id=row.sender_user_id,
        sender_user_name=sender_name,
        project_id=row.project_id,
        project_code=project.project_code if project else None,
        project_name=project.project_name if project else None,
        client_name=project.client_name if project else None,
        work_order_id=row.work_order_id,
        work_order_no=work_order.work_order_no if work_order else None,
        work_order_title=work_order.title if work_order else None,
        current_status=work_order.current_status if work_order else None,
        current_handler_user_id=work_order.current_handler_user_id if work_order else None,
        current_handler_user_name=current_handler_name,
        process_status=_derive_process_status(db, row),
        cc_flag=row.cc_flag,
        receiver_user_name=receiver_name,
        group_key=row.group_key,
        link_type=row.link_type,
        link_target_id=row.link_target_id,
        is_read=row.is_read,
        popup_flag=row.popup_flag,
        created_at=row.created_at,
    )


@router.get("/mine", response_model=NotificationListResponse)
def list_my_notifications(
    tab: str = Query("all"),
    keyword: str | None = Query(default=None),
    message_type: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    read_status: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    work_order_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    query = db.query(UserNotification).filter(UserNotification.user_id == current_user.id)
    if tab == "unread":
        query = query.filter(UserNotification.is_read.is_(False))
    elif tab == "read":
        query = query.filter(UserNotification.is_read.is_(True))
    elif tab == "initiated":
        query = query.filter(UserNotification.sender_user_id == current_user.id)
    elif tab == "cc":
        query = query.filter(UserNotification.cc_flag.is_(True))
    if keyword:
        like_value = f"%{keyword}%"
        query = query.filter((UserNotification.title.like(like_value)) | (UserNotification.content.like(like_value)))
    if message_type:
        query = query.filter(UserNotification.message_type == message_type)
    if priority:
        query = query.filter(UserNotification.priority == priority)
    if read_status == "UNREAD":
        query = query.filter(UserNotification.is_read.is_(False))
    elif read_status == "READ":
        query = query.filter(UserNotification.is_read.is_(True))
    if project_id:
        query = query.filter(UserNotification.project_id == project_id)
    if work_order_id:
        query = query.filter(UserNotification.work_order_id == work_order_id)
    total = query.count()
    rows = (
        query.order_by(UserNotification.created_at.desc(), UserNotification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return NotificationListResponse(
        items=[_build_notification_item(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=NotificationStatsResponse)
def get_notification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationStatsResponse:
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    query = db.query(UserNotification).filter(UserNotification.user_id == current_user.id)
    total = query.count()
    unread_count = query.filter(UserNotification.is_read.is_(False)).count()
    today_new_count = query.filter(UserNotification.created_at >= start_of_day).count()
    today_reminder_count = query.filter(UserNotification.created_at >= start_of_day, UserNotification.message_type == "REMINDER").count()
    read_count = query.filter(UserNotification.is_read.is_(True)).count()
    latest_row = (
        query.order_by(UserNotification.created_at.desc(), UserNotification.id.desc())
        .with_entities(UserNotification.id)
        .first()
    )
    latest_notification_id = latest_row[0] if latest_row else None
    read_rate = round((read_count / total) * 100, 2) if total else 0.0
    return NotificationStatsResponse(
        today_new_count=today_new_count,
        unread_count=unread_count,
        today_reminder_count=today_reminder_count,
        read_rate=read_rate,
        avg_process_duration_seconds=0,
        latest_notification_id=latest_notification_id,
        server_time=now,
    )


@router.post("/{notification_id}/read", response_model=NotificationReadResponse)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationReadResponse:
    row = db.query(UserNotification).filter(UserNotification.id == notification_id, UserNotification.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="消息不存在")
    mark_notification_read(db, row)
    db.commit()
    return NotificationReadResponse()


@router.post("/read/batch", response_model=NotificationReadResponse)
def batch_read_notification(
    payload: NotificationBatchReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationReadResponse:
    rows = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.id, UserNotification.id.in_(payload.notification_ids))
        .all()
    )
    for row in rows:
        mark_notification_read(db, row)
    db.commit()
    return NotificationReadResponse()


@router.get("/{notification_id}", response_model=NotificationDetailResponse)
def get_notification_detail(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationDetailResponse:
    row = db.query(UserNotification).filter(UserNotification.id == notification_id, UserNotification.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="消息不存在")
    item = _build_notification_item(db, row)
    return NotificationDetailResponse(**item.model_dump())


@router.get("/{notification_id}/timeline", response_model=NotificationTimelineResponse)
def get_notification_timeline(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationTimelineResponse:
    row = db.query(UserNotification).filter(UserNotification.id == notification_id, UserNotification.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="消息不存在")

    items: list[NotificationTimelineItem] = []
    if row.message_type == "REMINDER":
        event = db.query(ReminderEvent).filter(ReminderEvent.id == row.biz_id).first()
        if event:
            operator_name = db.query(User.real_name).filter(User.id == event.initiator_user_id).scalar()
            items.append(
                NotificationTimelineItem(
                    event_type="REMINDER_CREATED",
                    title="发起催办",
                    operator_user_name=operator_name,
                    status=event.current_status,
                    created_at=event.created_at,
                    remark=event.comment,
                )
            )
            receipts = (
                db.query(ReminderReceipt)
                .filter(ReminderReceipt.reminder_event_id == event.id)
                .order_by(ReminderReceipt.created_at.asc(), ReminderReceipt.id.asc())
                .all()
            )
            for receipt in receipts:
                receiver_name = db.query(User.real_name).filter(User.id == receipt.receiver_user_id).scalar()
                items.append(
                    NotificationTimelineItem(
                        event_type="RECEIPT",
                        title=f"{receiver_name or '接收人'}{'已读' if receipt.read_status == 'READ' else '收到消息'}",
                        operator_user_name=receiver_name,
                        status=receipt.read_status,
                        created_at=receipt.updated_at if receipt.read_status == "READ" else receipt.created_at,
                        remark=receipt.receiver_type,
                    )
                )
    elif row.message_type == "WORKFLOW":
        event = db.query(WorkflowLog).filter(WorkflowLog.id == row.biz_id).first()
        if event:
            operator_name = db.query(User.real_name).filter(User.id == event.operator_user_id).scalar()
            items.append(
                NotificationTimelineItem(
                    event_type="WORKFLOW_CREATED",
                    title=event.action_type,
                    operator_user_name=operator_name,
                    status=event.to_status,
                    created_at=event.created_at,
                    remark=event.remark,
                )
            )
    if row.work_order_id:
        logs = (
            db.query(WorkflowLog)
            .filter(WorkflowLog.work_order_id == row.work_order_id)
            .order_by(WorkflowLog.created_at.desc(), WorkflowLog.id.desc())
            .limit(10)
            .all()
        )
        for log in logs:
            operator_name = db.query(User.real_name).filter(User.id == log.operator_user_id).scalar()
            items.append(
                NotificationTimelineItem(
                    event_type="WORKFLOW",
                    title=log.action_type,
                    operator_user_name=operator_name,
                    status=log.to_status,
                    created_at=log.created_at,
                    remark=log.remark,
                )
            )
    items.sort(key=lambda item: item.created_at, reverse=True)
    return NotificationTimelineResponse(items=items)
