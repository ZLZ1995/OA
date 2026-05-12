from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.project import Project
from app.models.review_record import ReviewRecord
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.review import (
    ReviewCandidateListResponse,
    ReviewCandidateResponse,
    ReviewDecisionRequest,
    ReviewRecordListResponse,
    ReviewRecordResponse,
    ReviewSubmitRequest,
)
from app.services.workflow_log_service import create_workflow_log
from app.workflows.guards import filter_candidates, validate_reviewer_avoidance
from app.workflows.states import WorkOrderStatus
from app.workflows.transitions import can_transit

router = APIRouter(prefix="/reviews", tags=["审核"])

ROUND_SUBMIT_STATUS = {
    "FIRST": {
        WorkOrderStatus.CONTRACT_APPROVED,
        WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT,
        WorkOrderStatus.FIRST_REVIEW_REJECTED,
    },
    "SECOND": {
        WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
        WorkOrderStatus.SECOND_REVIEW_REJECTED,
    },
    "THIRD": {
        WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
        WorkOrderStatus.THIRD_REVIEW_REJECTED,
    },
}

ROUND_REVIEWING_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_REVIEWING,
    "SECOND": WorkOrderStatus.SECOND_REVIEWING,
    "THIRD": WorkOrderStatus.THIRD_REVIEWING,
}

ROUND_APPROVED_STATUS = {
    "FIRST": WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
    "SECOND": WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
    "THIRD": WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM,
}

ROUND_REJECTED_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_REVIEW_REJECTED,
    "SECOND": WorkOrderStatus.SECOND_REVIEW_REJECTED,
    "THIRD": WorkOrderStatus.THIRD_REVIEW_REJECTED,
}

ROUND_ROLE_CODE = {
    "FIRST": "FIRST_REVIEWER",
    "SECOND": "SECOND_REVIEWER",
    "THIRD": "THIRD_REVIEWER",
}

ROUND_WAIT_STATUS = {
    "FIRST": WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT,
    "SECOND": WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
    "THIRD": WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
}


def _to_review_record_response(db: Session, record: ReviewRecord) -> ReviewRecordResponse:
    reviewer_name = db.query(User.real_name).filter(User.id == record.reviewer_user_id).scalar()
    data = ReviewRecordResponse.model_validate(record, from_attributes=True)
    data.reviewer_name = reviewer_name
    return data


def _ensure_reviewer_has_round_role(db: Session, reviewer_user_id: int, review_round: str) -> None:
    required_role = ROUND_ROLE_CODE[review_round]
    exists = (
        db.query(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(User, User.id == UserRole.user_id)
        .filter(User.id == reviewer_user_id, User.is_active.is_(True), Role.code == required_role)
        .first()
    )
    if not exists:
        raise HTTPException(status_code=400, detail=f"所选审核人不具备{review_round}轮审核角色")


@router.get("/candidates", response_model=ReviewCandidateListResponse)
def list_review_candidates(
    work_order_id: int,
    review_round: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "ADMIN")),
) -> ReviewCandidateListResponse:
    if review_round not in ROUND_ROLE_CODE:
        raise HTTPException(status_code=400, detail="非法审核轮次")

    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if current_user.id not in {work_order.project_leader_id, work_order.initiator_user_id} and "ADMIN" not in role_codes:
        raise HTTPException(status_code=403, detail="仅项目负责人或创建人可查看审核候选人")

    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    current_round_existing = {
        "FIRST": work_order.first_reviewer_id,
        "SECOND": work_order.second_reviewer_id,
        "THIRD": work_order.third_reviewer_id,
    }[review_round]

    excluded_user_ids = {
        work_order.project_leader_id,
        project.business_user_id,
        *(uid for uid in [work_order.first_reviewer_id, work_order.second_reviewer_id, work_order.third_reviewer_id] if uid),
    }
    if current_round_existing:
        excluded_user_ids.discard(current_round_existing)

    reviewer_users = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.code == ROUND_ROLE_CODE[review_round], User.is_active.is_(True))
        .order_by(User.id.asc())
        .all()
    )
    allowed_ids = set(filter_candidates([u.id for u in reviewer_users], excluded_user_ids))
    return ReviewCandidateListResponse(
        items=[
            ReviewCandidateResponse(user_id=user.id, username=user.username, real_name=user.real_name)
            for user in reviewer_users
            if user.id in allowed_ids
        ]
    )


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
    if current_user.id not in {work_order.project_leader_id, work_order.initiator_user_id} and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅项目负责人或创建人可发起审核")

    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    _ensure_reviewer_has_round_role(db, payload.reviewer_user_id, payload.review_round)

    first_reviewer_id = payload.reviewer_user_id if payload.review_round == "FIRST" else work_order.first_reviewer_id
    second_reviewer_id = payload.reviewer_user_id if payload.review_round == "SECOND" else work_order.second_reviewer_id
    third_reviewer_id = payload.reviewer_user_id if payload.review_round == "THIRD" else work_order.third_reviewer_id
    ok, msg = validate_reviewer_avoidance(
        project_leader_id=work_order.project_leader_id,
        business_user_id=project.business_user_id,
        first_reviewer_id=first_reviewer_id,
        second_reviewer_id=second_reviewer_id,
        third_reviewer_id=third_reviewer_id,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    from_status = WorkOrderStatus(work_order.current_status)
    if payload.review_round == "FIRST" and from_status == WorkOrderStatus.CONTRACT_APPROVED:
        work_order.current_status = WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT.value
        from_status = WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT

    to_status = ROUND_REVIEWING_STATUS[payload.review_round]
    allowed_submit_statuses = ROUND_SUBMIT_STATUS[payload.review_round]
    if from_status not in allowed_submit_statuses:
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
    return _to_review_record_response(db, record)


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
    if reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅当前轮审核老师可操作")

    from_status = WorkOrderStatus(work_order.current_status)
    reviewing_status = ROUND_REVIEWING_STATUS[payload.review_round]
    if from_status != reviewing_status:
        raise HTTPException(status_code=400, detail="当前状态不可审核")

    if payload.action == "APPROVE":
        to_status = ROUND_APPROVED_STATUS[payload.review_round]
        next_handler = work_order.project_leader_id if payload.review_round != "THIRD" else current_user.id
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
        comment=payload.comment or ("审核通过" if payload.action == "APPROVE" else None),
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
    return _to_review_record_response(db, record)


@router.get("/work-orders/{work_order_id}", response_model=ReviewRecordListResponse)
def list_reviews(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReviewRecordListResponse:
    rows = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.work_order_id == work_order_id)
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .all()
    )
    return ReviewRecordListResponse(items=[_to_review_record_response(db, item) for item in rows])


@router.post("/work-orders/{work_order_id}/withdraw-latest")
def withdraw_latest_review_step(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "FIRST_REVIEWER", "SECOND_REVIEWER", "THIRD_REVIEWER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    latest = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.work_order_id == work_order_id)
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=400, detail="暂无可撤回的审核记录")

    if "ADMIN" not in role_codes:
        if latest.action in {"APPROVE", "REJECT_RETURN"} and latest.reviewer_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="只能撤回本人最新审核操作")
        if latest.action == "SUBMIT" and current_user.id not in {work_order.project_leader_id, work_order.initiator_user_id}:
            raise HTTPException(status_code=403, detail="只能由送审人员撤回最新送审操作")

    current_status = WorkOrderStatus(work_order.current_status)
    review_round = latest.review_round
    reviewing_status = ROUND_REVIEWING_STATUS[review_round]
    rejected_status = ROUND_REJECTED_STATUS[review_round]
    approved_status = ROUND_APPROVED_STATUS[review_round]
    wait_status = ROUND_WAIT_STATUS[review_round]

    if latest.action == "REJECT_RETURN":
        if current_status != rejected_status:
            raise HTTPException(status_code=400, detail="只能撤回当前最新退回操作")
        rollback_status = reviewing_status
        rollback_handler = latest.reviewer_user_id
        file_categories = {"REVIEW_OPINION"}
    elif latest.action == "APPROVE":
        if current_status != approved_status:
            raise HTTPException(status_code=400, detail="只能撤回当前最新通过操作")
        rollback_status = reviewing_status
        rollback_handler = latest.reviewer_user_id
        file_categories = {"REVIEW_OPINION"}
    elif latest.action == "SUBMIT":
        if current_status != reviewing_status:
            raise HTTPException(status_code=400, detail="只能撤回当前最新送审操作")
        previous_rejection = (
            db.query(ReviewRecord)
            .filter(
                ReviewRecord.work_order_id == work_order_id,
                ReviewRecord.review_round == review_round,
                ReviewRecord.action == "REJECT_RETURN",
                ReviewRecord.acted_at < latest.acted_at,
            )
            .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
            .first()
        )
        rollback_status = rejected_status if previous_rejection else wait_status
        rollback_handler = work_order.project_leader_id
        file_categories = {"REPORT_ZIP", "REVIEW_REPLY"}
    else:
        raise HTTPException(status_code=400, detail="该审核记录不可撤回")

    previous_record = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.work_order_id == work_order_id, ReviewRecord.acted_at < latest.acted_at)
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .first()
    )
    stage = f"REVIEW_{review_round}"
    file_query = db.query(WorkOrderFile).filter(
        WorkOrderFile.work_order_id == work_order_id,
        WorkOrderFile.business_stage == stage,
        WorkOrderFile.file_category.in_(file_categories),
        WorkOrderFile.uploaded_at <= latest.acted_at,
    )
    if previous_record:
        file_query = file_query.filter(WorkOrderFile.uploaded_at > previous_record.acted_at)
    files_to_delete = file_query.all()
    for file_row in files_to_delete:
        path = Path(settings.local_storage_dir) / file_row.storage_key
        if path.exists():
            path.unlink()
        db.delete(file_row)

    work_order.current_status = rollback_status.value
    work_order.current_handler_user_id = rollback_handler
    db.delete(latest)
    db.commit()
    return {"status": "ok"}
