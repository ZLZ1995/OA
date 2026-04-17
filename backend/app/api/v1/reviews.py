from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.review_record import ReviewRecord
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.review import (
    ReviewDecisionRequest,
    ReviewRecordListResponse,
    ReviewRecordResponse,
    ReviewSubmitRequest,
)
from app.services.workflow_log_service import create_workflow_log
from app.workflows.states import WorkOrderStatus
from app.workflows.transitions import can_transit

router = APIRouter(prefix="/reviews", tags=["审核"])

ROUND_SUBMIT_STATUS = {
    "FIRST": WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT,
    "SECOND": WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
    "THIRD": WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
}

ROUND_REVIEWING_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_REVIEWING,
    "SECOND": WorkOrderStatus.SECOND_REVIEWING,
    "THIRD": WorkOrderStatus.THIRD_REVIEWING,
}

ROUND_APPROVED_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND,
    "SECOND": WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD,
    "THIRD": WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM,
}

ROUND_REJECTED_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_REVIEW_REJECTED,
    "SECOND": WorkOrderStatus.SECOND_REVIEW_REJECTED,
    "THIRD": WorkOrderStatus.THIRD_REVIEW_REJECTED,
}


@router.post("/submit", response_model=ReviewRecordResponse)
def submit_review(
    payload: ReviewSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PROJECT_LEADER", "ADMIN")),
) -> ReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if work_order.project_leader_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅项目负责人可发起审核")

    from_status = WorkOrderStatus(work_order.current_status)
    to_status = ROUND_REVIEWING_STATUS[payload.review_round]
    required_submit_status = ROUND_SUBMIT_STATUS[payload.review_round]
    if from_status != required_submit_status:
        raise HTTPException(status_code=400, detail=f"当前状态不可发起{payload.review_round}审")
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    if payload.review_round == "FIRST":
        work_order.first_reviewer_id = payload.reviewer_user_id
    elif payload.review_round == "SECOND":
        work_order.second_reviewer_id = payload.reviewer_user_id
    else:
        work_order.third_reviewer_id = payload.reviewer_user_id

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = payload.reviewer_user_id

    record = ReviewRecord(
        work_order_id=work_order.id,
        review_round=payload.review_round,
        reviewer_user_id=payload.reviewer_user_id,
        action="SUBMIT",
        comment=payload.comment,
        acted_at=datetime.now(timezone.utc),
    )
    db.add(record)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type=f"SUBMIT_{payload.review_round}",
        operator_user_id=current_user.id,
        remark=payload.comment,
    )
    db.commit()
    db.refresh(record)
    return ReviewRecordResponse.model_validate(record, from_attributes=True)


@router.post("/decision", response_model=ReviewRecordResponse)
def decide_review(
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("FIRST_REVIEWER", "SECOND_REVIEWER", "THIRD_REVIEWER", "ADMIN")),
) -> ReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    reviewer_id = {
        "FIRST": work_order.first_reviewer_id,
        "SECOND": work_order.second_reviewer_id,
        "THIRD": work_order.third_reviewer_id,
    }[payload.review_round]
    if reviewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅当前轮审核老师可操作")

    from_status = WorkOrderStatus(work_order.current_status)
    reviewing_status = ROUND_REVIEWING_STATUS[payload.review_round]
    if from_status != reviewing_status:
        raise HTTPException(status_code=400, detail="当前状态不可审核")

    if payload.action == "APPROVE":
        to_status = ROUND_APPROVED_STATUS[payload.review_round]
        next_handler = work_order.project_leader_id if payload.review_round != "THIRD" else None
    else:
        to_status = ROUND_REJECTED_STATUS[payload.review_round]
        next_handler = work_order.project_leader_id

    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = next_handler

    record = ReviewRecord(
        work_order_id=work_order.id,
        review_round=payload.review_round,
        reviewer_user_id=current_user.id,
        action=payload.action,
        comment=payload.comment,
        acted_at=datetime.now(timezone.utc),
    )
    db.add(record)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type=f"{payload.review_round}_{payload.action}",
        operator_user_id=current_user.id,
        remark=payload.comment,
    )

    db.commit()
    db.refresh(record)
    return ReviewRecordResponse.model_validate(record, from_attributes=True)


@router.get("/work-orders/{work_order_id}", response_model=ReviewRecordListResponse)
def list_reviews(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReviewRecordListResponse:
    rows = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.work_order_id == work_order_id)
        .order_by(ReviewRecord.acted_at.desc())
        .all()
    )
    return ReviewRecordListResponse(
        items=[ReviewRecordResponse.model_validate(item, from_attributes=True) for item in rows]
    )
