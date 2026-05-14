from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.reminder_event import ReminderEvent
from app.models.reminder_receipt import ReminderReceipt
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.reminder import ReminderCreateRequest, ReminderCreateResponse, ReminderEligibilityResponse, ReminderHistoryItem, ReminderHistoryResponse
from app.services.reminder_policy import evaluate_reminder_eligibility
from app.services.reminder_service import create_reminder

router = APIRouter(prefix="/reminders", tags=["催办"])


def _get_work_order_and_project(db: Session, work_order_id: int) -> tuple[WorkOrder, Project]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    project = db.query(Project).filter(Project.id == work_order.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return work_order, project


@router.get("/eligibility", response_model=ReminderEligibilityResponse)
def get_eligibility(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReminderEligibilityResponse:
    work_order, project = _get_work_order_and_project(db, work_order_id)
    result = evaluate_reminder_eligibility(db, work_order=work_order, project=project, current_user=current_user)
    return ReminderEligibilityResponse(**result.__dict__)


@router.post("", response_model=ReminderCreateResponse)
def post_reminder(
    payload: ReminderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReminderCreateResponse:
    work_order, project = _get_work_order_and_project(db, payload.work_order_id)
    try:
        event = create_reminder(db, project=project, work_order=work_order, current_user=current_user, comment=payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ReminderCreateResponse(
        reminder_event_id=event.id,
        today_remind_count=event.day_remind_seq,
        message=f"催办已发送，今天对该处理人第 {event.day_remind_seq} 次催办",
    )


@router.get("/work-orders/{work_order_id}", response_model=ReminderHistoryResponse)
def list_work_order_reminders(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReminderHistoryResponse:
    rows = (
        db.query(ReminderEvent)
        .filter(ReminderEvent.work_order_id == work_order_id)
        .order_by(ReminderEvent.created_at.desc(), ReminderEvent.id.desc())
        .all()
    )
    items: list[ReminderHistoryItem] = []
    for row in rows:
        initiator = db.query(User).filter(User.id == row.initiator_user_id).first()
        handler = db.query(User).filter(User.id == row.current_handler_user_id).first()
        work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
        primary = (
            db.query(ReminderReceipt)
            .filter(ReminderReceipt.reminder_event_id == row.id, ReminderReceipt.receiver_type == "PRIMARY")
            .order_by(ReminderReceipt.id.desc())
            .first()
        )
        items.append(
            ReminderHistoryItem(
                reminder_event_id=row.id,
                project_id=row.project_id,
                work_order_id=row.work_order_id,
                work_order_no=work_order.work_order_no if work_order else None,
                current_status=row.current_status,
                initiator_user_id=row.initiator_user_id,
                initiator_user_name=initiator.real_name if initiator else None,
                current_handler_user_id=row.current_handler_user_id,
                current_handler_user_name=handler.real_name if handler else None,
                overdue_seconds=row.overdue_seconds,
                comment=row.comment,
                day_remind_seq=row.day_remind_seq,
                created_at=row.created_at,
                primary_read_status=primary.read_status if primary else "UNREAD",
                primary_read_at=primary.updated_at if primary and primary.read_status == "READ" else None,
                delivery_status=primary.delivery_status if primary else "SENT",
            )
        )
    return ReminderHistoryResponse(items=items)


@router.get("/projects/{project_id}", response_model=ReminderHistoryResponse)
def list_project_reminders(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReminderHistoryResponse:
    rows = (
        db.query(ReminderEvent)
        .filter(ReminderEvent.project_id == project_id)
        .order_by(ReminderEvent.created_at.desc(), ReminderEvent.id.desc())
        .all()
    )
    return ReminderHistoryResponse(
        items=[
            ReminderHistoryItem(
                reminder_event_id=row.id,
                project_id=row.project_id,
                work_order_id=row.work_order_id,
                current_status=row.current_status,
                initiator_user_id=row.initiator_user_id,
                current_handler_user_id=row.current_handler_user_id,
                overdue_seconds=row.overdue_seconds,
                comment=row.comment,
                day_remind_seq=row.day_remind_seq,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )
