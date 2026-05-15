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
    ReviewAssigneeChangeRequest,
    ReviewRecordListResponse,
    ReviewRecordResponse,
    ReviewSubmitRequest,
)
from app.services.project_conflicts import assert_project_can_submit_review
from app.services.workflow_notification_service import send_workflow_notification
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

ROUND_CURRENT_REVIEWER_ATTR = {
    "FIRST": "first_reviewer_id",
    "SECOND": "second_reviewer_id",
    "THIRD": "third_reviewer_id",
}

ROUND_NEXT = {
    "FIRST": "SECOND",
    "SECOND": "THIRD",
}

REVIEW_ROUND_SEQUENCE = {
    "FIRST": 1,
    "SECOND": 2,
    "THIRD": 3,
}

REVIEW_FILE_CATEGORIES = {"REPORT_ZIP", "REVIEW_REPLY", "REVIEW_OPINION"}


def _to_review_record_response(db: Session, record: ReviewRecord) -> ReviewRecordResponse:
    reviewer_name = db.query(User.real_name).filter(User.id == record.reviewer_user_id).scalar()
    data = ReviewRecordResponse.model_validate(record, from_attributes=True)
    data.reviewer_name = reviewer_name
    data.comment = _strip_auto_comment_marker(record.comment)
    source_record_id = _parse_source_record_id(record.comment)
    if source_record_id:
        source_record = db.query(ReviewRecord).filter(ReviewRecord.id == source_record_id).first()
        if source_record:
            data.source_record_id = source_record.id
            data.source_round_comment = _strip_auto_comment_marker(source_record.comment)
            data.source_round_reviewer_name = db.query(User.real_name).filter(User.id == source_record.reviewer_user_id).scalar()
            data.auto_carried_from_previous = True
    return data


def _parse_source_record_id(comment: str | None) -> int | None:
    if not comment:
        return None
    marker = "[AUTO_FROM_RECORD:"
    if marker not in comment:
        return None
    try:
        value = comment.split(marker, 1)[1].split("]", 1)[0]
        return int(value)
    except (IndexError, ValueError):
        return None


def _strip_auto_comment_marker(comment: str | None) -> str | None:
    if not comment:
        return comment
    marker = "[AUTO_FROM_RECORD:"
    if marker not in comment:
        return comment
    prefix, _ = comment.split(marker, 1)
    value = prefix.strip()
    return value or None


def _latest_submit_record(db: Session, work_order_id: int, review_round: str) -> ReviewRecord | None:
    return (
        db.query(ReviewRecord)
        .filter(
            ReviewRecord.work_order_id == work_order_id,
            ReviewRecord.review_round == review_round,
            ReviewRecord.action == "SUBMIT",
        )
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .first()
    )


def _latest_round_files(db: Session, work_order_id: int, review_round: str, file_category: str) -> list[WorkOrderFile]:
    rows = (
        db.query(WorkOrderFile)
        .filter(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.business_stage == f"REVIEW_{review_round}",
            WorkOrderFile.file_category == file_category,
        )
        .order_by(WorkOrderFile.version_no.desc(), WorkOrderFile.id.desc())
        .all()
    )
    latest_by_name: dict[str, WorkOrderFile] = {}
    for row in rows:
        if row.origin_file_name not in latest_by_name:
            latest_by_name[row.origin_file_name] = row
    return list(latest_by_name.values())


def _clone_files_to_round(
    db: Session,
    *,
    work_order_id: int,
    from_round: str,
    to_round: str,
    uploaded_by: int,
) -> None:
    stage_to = f"REVIEW_{to_round}"
    for file_category in ("REPORT_ZIP", "REVIEW_REPLY"):
        source_files = _latest_round_files(db, work_order_id, from_round, file_category)
        if not source_files:
            continue
        existing_latest = (
            db.query(WorkOrderFile)
            .filter(
                WorkOrderFile.work_order_id == work_order_id,
                WorkOrderFile.business_stage == stage_to,
                WorkOrderFile.file_category == file_category,
            )
            .order_by(WorkOrderFile.version_no.desc())
            .first()
        )
        next_version = 1 if not existing_latest else existing_latest.version_no + 1
        db.query(WorkOrderFile).filter(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.business_stage == stage_to,
            WorkOrderFile.file_category == file_category,
            WorkOrderFile.is_current.is_(True),
        ).update({"is_current": False})
        for source_file in source_files:
            db.add(
                WorkOrderFile(
                    work_order_id=source_file.work_order_id,
                    file_category=source_file.file_category,
                    business_stage=stage_to,
                    version_no=next_version,
                    is_current=True,
                    origin_file_name=source_file.origin_file_name,
                    storage_key=source_file.storage_key,
                    file_size=source_file.file_size,
                    uploaded_by=uploaded_by,
                    uploaded_at=source_file.uploaded_at,
                )
            )
            next_version += 1


def _latest_report_file_owner_is_project_party(db: Session, work_order: WorkOrder, review_round: str) -> bool:
    latest_report = (
        db.query(WorkOrderFile)
        .filter(
            WorkOrderFile.work_order_id == work_order.id,
            WorkOrderFile.business_stage == f"REVIEW_{review_round}",
            WorkOrderFile.file_category == "REPORT_ZIP",
        )
        .order_by(WorkOrderFile.version_no.desc(), WorkOrderFile.id.desc())
        .first()
    )
    if not latest_report:
        return False
    if latest_report.uploaded_by in {work_order.project_leader_id, work_order.initiator_user_id}:
        return True
    from app.models.project_member import ProjectMember

    return db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == latest_report.uploaded_by,
    ).first() is not None


def _auto_advance_if_needed(
    db: Session,
    *,
    work_order: WorkOrder,
    current_round: str,
    current_reviewer: User,
    project: Project,
    approved_record: ReviewRecord,
) -> tuple[WorkOrderStatus, int, str]:
    next_round = ROUND_NEXT.get(current_round)
    if not next_round:
        return ROUND_APPROVED_STATUS[current_round], current_reviewer.id, f"{current_round}_APPROVE"
    if not _latest_report_file_owner_is_project_party(db, work_order, current_round):
        return ROUND_APPROVED_STATUS[current_round], work_order.project_leader_id, f"{current_round}_APPROVE"

    next_reviewer_id = getattr(work_order, ROUND_CURRENT_REVIEWER_ATTR[next_round])
    if not next_reviewer_id:
        return ROUND_APPROVED_STATUS[current_round], work_order.project_leader_id, f"{current_round}_APPROVE"

    _clone_files_to_round(
        db,
        work_order_id=work_order.id,
        from_round=current_round,
        to_round=next_round,
        uploaded_by=_latest_submit_record(db, work_order.id, current_round).reviewer_user_id if _latest_submit_record(db, work_order.id, current_round) else work_order.project_leader_id,
    )
    db.add(
        ReviewRecord(
            work_order_id=work_order.id,
            review_round=next_round,
            reviewer_user_id=next_reviewer_id,
            action="SUBMIT",
            comment=f"来源于上一轮自动流转 [AUTO_FROM_RECORD:{approved_record.id}]",
            acted_at=datetime.now(timezone.utc),
        )
    )
    return ROUND_REVIEWING_STATUS[next_round], next_reviewer_id, f"SUBMIT_{next_round}"


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


def _is_project_party(db: Session, work_order: WorkOrder, current_user: User) -> bool:
    if current_user.id in {work_order.project_leader_id, work_order.initiator_user_id}:
        return True
    from app.models.project_member import ProjectMember

    return db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == current_user.id,
    ).first() is not None


def _latest_pending_reviewer_change(db: Session, work_order_id: int, review_round: str) -> ReviewRecord | None:
    latest_submit = (
        db.query(ReviewRecord)
        .filter(
            ReviewRecord.work_order_id == work_order_id,
            ReviewRecord.review_round == review_round,
            ReviewRecord.action == "SUBMIT",
        )
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .first()
    )
    latest_submit_at = latest_submit.acted_at if latest_submit else datetime.min.replace(tzinfo=timezone.utc)
    return (
        db.query(ReviewRecord)
        .filter(
            ReviewRecord.work_order_id == work_order_id,
            ReviewRecord.review_round == review_round,
            ReviewRecord.action == "CHANGE_REVIEWER",
            ReviewRecord.acted_at > latest_submit_at,
        )
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .first()
    )


def _has_reviewer_change_after_rejection(db: Session, work_order_id: int, review_round: str) -> bool:
    latest_rejection = (
        db.query(ReviewRecord)
        .filter(
            ReviewRecord.work_order_id == work_order_id,
            ReviewRecord.review_round == review_round,
            ReviewRecord.action == "REJECT_RETURN",
        )
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .first()
    )
    if not latest_rejection:
        return False
    return (
        db.query(ReviewRecord.id)
        .filter(
            ReviewRecord.work_order_id == work_order_id,
            ReviewRecord.review_round == review_round,
            ReviewRecord.action == "CHANGE_REVIEWER",
            ReviewRecord.acted_at > latest_rejection.acted_at,
        )
        .first()
        is not None
    )


@router.get("/candidates", response_model=ReviewCandidateListResponse)
def list_review_candidates(
    work_order_id: int,
    review_round: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> ReviewCandidateListResponse:
    if review_round not in ROUND_ROLE_CODE:
        raise HTTPException(status_code=400, detail="非法审核轮次")

    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if "ADMIN" not in role_codes and not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可查看审核候选人")

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
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> ReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if "ADMIN" not in role_codes and not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可发起审核")

    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    assert_project_can_submit_review(db, project)

    pending_change = _latest_pending_reviewer_change(db, work_order.id, payload.review_round)
    target_reviewer_id = (
        pending_change.reviewer_user_id
        if pending_change and pending_change.reviewer_user_id == payload.reviewer_user_id
        else payload.reviewer_user_id
    )

    _ensure_reviewer_has_round_role(db, target_reviewer_id, payload.review_round)

    first_reviewer_id = target_reviewer_id if payload.review_round == "FIRST" else work_order.first_reviewer_id
    second_reviewer_id = target_reviewer_id if payload.review_round == "SECOND" else work_order.second_reviewer_id
    third_reviewer_id = target_reviewer_id if payload.review_round == "THIRD" else work_order.third_reviewer_id
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
        work_order.first_reviewer_id = target_reviewer_id
    elif payload.review_round == "SECOND":
        work_order.second_reviewer_id = target_reviewer_id
    else:
        work_order.third_reviewer_id = target_reviewer_id

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = target_reviewer_id

    record = ReviewRecord(
        work_order_id=work_order.id,
        review_round=payload.review_round,
        reviewer_user_id=target_reviewer_id,
        action="SUBMIT",
        comment=payload.comment,
        acted_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.flush()
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type=f"SUBMIT_{payload.review_round}",
        operator_user_id=current_user.id,
        remark=payload.comment,
    )
    if project:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=target_reviewer_id,
            action_name=f"SUBMIT_{payload.review_round}",
            comment=payload.comment,
            biz_id=record.id,
        )
    db.commit()
    db.refresh(record)
    return _to_review_record_response(db, record)


@router.post("/change-reviewer", response_model=ReviewRecordResponse)
def change_reviewer_after_reject(
    payload: ReviewAssigneeChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> ReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if "ADMIN" not in role_codes and not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可变更审核人")

    rejected_status = ROUND_REJECTED_STATUS[payload.review_round]
    if WorkOrderStatus(work_order.current_status) != rejected_status:
        raise HTTPException(status_code=400, detail="仅当前轮次被退回后可变更审核人")
    if _has_reviewer_change_after_rejection(db, work_order.id, payload.review_round):
        raise HTTPException(status_code=400, detail="本次退回已变更过审核人")

    old_reviewer_id = getattr(work_order, ROUND_CURRENT_REVIEWER_ATTR[payload.review_round])
    if old_reviewer_id == payload.reviewer_user_id:
        raise HTTPException(status_code=400, detail="新审核人不能与原审核人相同")

    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    _ensure_reviewer_has_round_role(db, payload.reviewer_user_id, payload.review_round)
    candidate_first = payload.reviewer_user_id if payload.review_round == "FIRST" else work_order.first_reviewer_id
    candidate_second = payload.reviewer_user_id if payload.review_round == "SECOND" else work_order.second_reviewer_id
    candidate_third = payload.reviewer_user_id if payload.review_round == "THIRD" else work_order.third_reviewer_id
    ok, msg = validate_reviewer_avoidance(
        project_leader_id=work_order.project_leader_id,
        business_user_id=project.business_user_id,
        first_reviewer_id=candidate_first,
        second_reviewer_id=candidate_second,
        third_reviewer_id=candidate_third,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    old_name = db.query(User.real_name).filter(User.id == old_reviewer_id).scalar() or "-"
    new_name = db.query(User.real_name).filter(User.id == payload.reviewer_user_id).scalar() or "-"
    comment = f"原审核人：{old_name}；新审核人：{new_name}"
    if payload.comment:
        comment = f"{comment}；备注：{payload.comment}"

    record = ReviewRecord(
        work_order_id=work_order.id,
        review_round=payload.review_round,
        reviewer_user_id=payload.reviewer_user_id,
        action="CHANGE_REVIEWER",
        comment=comment,
        acted_at=datetime.now(timezone.utc),
    )
    db.add(record)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=work_order.current_status,
        to_status=work_order.current_status,
        action_type=f"CHANGE_{payload.review_round}_REVIEWER",
        operator_user_id=current_user.id,
        remark=comment,
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
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if payload.action == "APPROVE":
        default_status = ROUND_APPROVED_STATUS[payload.review_round]
        if not can_transit(from_status, default_status):
            raise HTTPException(status_code=400, detail="闈炴硶鐘舵€佽縼绉?")
        to_status, next_handler, workflow_action = _auto_advance_if_needed(
            db,
            work_order=work_order,
            current_round=payload.review_round,
            current_reviewer=current_user,
            project=project,
            approved_record=record,
        )
    else:
        workflow_action = f"{payload.review_round}_REJECT_RETURN"

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = next_handler

    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type=f"{payload.review_round}_{payload.action}",
        operator_user_id=current_user.id,
        remark=payload.comment,
    )
    if project:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=next_handler,
            action_name=workflow_action,
            comment=payload.comment,
            biz_id=record.id,
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
