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
    ReviewApprovalRoutingRequest,
    ReviewCandidateListResponse,
    ReviewCandidateResponse,
    ReviewDecisionRequest,
    ReviewRecallRoutingRequest,
    ReviewAssigneeChangeRequest,
    ReviewRecordListResponse,
    ReviewRecordResponse,
    ReviewSubmitRequest,
)
from app.services.project_conflicts import assert_project_can_submit_review
from app.services.project_role_conflict_service import get_project_party_user_ids, validate_not_project_party, validate_reviewer_round_conflict
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
        WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND,
        WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
        WorkOrderStatus.SECOND_REVIEW_REJECTED,
    },
    "THIRD": {
        WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD,
        WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
        WorkOrderStatus.THIRD_REVIEW_REJECTED,
    },
    "EXTERNAL_FIRST": {
        WorkOrderStatus.WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT,
        WorkOrderStatus.EXTERNAL_FIRST_REJECTED,
    },
    "EXTERNAL_SECOND": {
        WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT,
        WorkOrderStatus.EXTERNAL_SECOND_REJECTED,
    },
    "EXTERNAL_THIRD": {
        WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT,
        WorkOrderStatus.EXTERNAL_THIRD_REJECTED,
    },
}

ROUND_REVIEWING_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_REVIEWING,
    "SECOND": WorkOrderStatus.SECOND_REVIEWING,
    "THIRD": WorkOrderStatus.THIRD_REVIEWING,
    "EXTERNAL_FIRST": WorkOrderStatus.EXTERNAL_FIRST_REVIEWING,
    "EXTERNAL_SECOND": WorkOrderStatus.EXTERNAL_SECOND_REVIEWING,
    "EXTERNAL_THIRD": WorkOrderStatus.EXTERNAL_THIRD_REVIEWING,
}

ROUND_APPROVED_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND,
    "SECOND": WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD,
    "THIRD": WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM,
    "EXTERNAL_FIRST": WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT,
    "EXTERNAL_SECOND": WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT,
    "EXTERNAL_THIRD": WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD,
}

ROUND_REJECTED_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_REVIEW_REJECTED,
    "SECOND": WorkOrderStatus.SECOND_REVIEW_REJECTED,
    "THIRD": WorkOrderStatus.THIRD_REVIEW_REJECTED,
    "EXTERNAL_FIRST": WorkOrderStatus.EXTERNAL_FIRST_REJECTED,
    "EXTERNAL_SECOND": WorkOrderStatus.EXTERNAL_SECOND_REJECTED,
    "EXTERNAL_THIRD": WorkOrderStatus.EXTERNAL_THIRD_REJECTED,
}

ROUND_ROLE_CODE = {
    "FIRST": "FIRST_REVIEWER",
    "SECOND": "SECOND_REVIEWER",
    "THIRD": "THIRD_REVIEWER",
    "EXTERNAL_FIRST": "FIRST_REVIEWER",
    "EXTERNAL_SECOND": "SECOND_REVIEWER",
    "EXTERNAL_THIRD": "THIRD_REVIEWER",
}

ROUND_WAIT_STATUS = {
    "FIRST": WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT,
    "SECOND": WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND,
    "THIRD": WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD,
    "EXTERNAL_FIRST": WorkOrderStatus.WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT,
    "EXTERNAL_SECOND": WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT,
    "EXTERNAL_THIRD": WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT,
}

ROUND_CURRENT_REVIEWER_ATTR = {
    "FIRST": "first_reviewer_id",
    "SECOND": "second_reviewer_id",
    "THIRD": "third_reviewer_id",
    "EXTERNAL_FIRST": "first_reviewer_id",
    "EXTERNAL_SECOND": "second_reviewer_id",
    "EXTERNAL_THIRD": "third_reviewer_id",
}

ROUND_PREVIOUS_REVIEWER_ATTR = {
    "SECOND": "first_reviewer_id",
    "THIRD": "second_reviewer_id",
    "EXTERNAL_SECOND": "first_reviewer_id",
    "EXTERNAL_THIRD": "second_reviewer_id",
}

ROUND_RECALL_TARGET_STATUS = {
    "SECOND": WorkOrderStatus.FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND,
    "THIRD": WorkOrderStatus.SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD,
    "EXTERNAL_SECOND": WorkOrderStatus.EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND,
    "EXTERNAL_THIRD": WorkOrderStatus.EXTERNAL_SECOND_APPROVED_WAIT_RECALL_OR_THIRD,
}

ROUND_NEXT = {
    "FIRST": "SECOND",
    "SECOND": "THIRD",
    "EXTERNAL_FIRST": "EXTERNAL_SECOND",
    "EXTERNAL_SECOND": "EXTERNAL_THIRD",
}

REVIEW_ROUND_SEQUENCE = {
    "FIRST": 1,
    "SECOND": 2,
    "THIRD": 3,
    "EXTERNAL_FIRST": 4,
    "EXTERNAL_SECOND": 5,
    "EXTERNAL_THIRD": 6,
}

REVIEW_FILE_CATEGORIES = {"REPORT_ZIP", "REVIEW_REPLY", "REVIEW_OPINION"}
STATE_OWNED_EVAL_NATURE = "国有资产评估业务"
AUTO_FROM_RECORD_MARKER = "[AUTO_FROM_RECORD:"
PASSED_TO_MARKER = "[PASSED_TO_ROUND:"


def _to_review_record_response(db: Session, record: ReviewRecord) -> ReviewRecordResponse:
    reviewer_name = db.query(User.real_name).filter(User.id == record.reviewer_user_id).scalar()
    data = ReviewRecordResponse.model_validate(record, from_attributes=True)
    data.reviewer_name = reviewer_name
    data.comment = _strip_internal_markers(record.comment)
    source_record_id = _parse_source_record_id(record.comment)
    if source_record_id:
        source_record = db.query(ReviewRecord).filter(ReviewRecord.id == source_record_id).first()
        if source_record:
            data.source_record_id = source_record.id
            data.source_round_comment = _strip_internal_markers(source_record.comment)
            data.source_round_reviewer_name = db.query(User.real_name).filter(User.id == source_record.reviewer_user_id).scalar()
            data.auto_carried_from_previous = True
    transferred_to_round = _parse_transferred_to_round(record.comment)
    if transferred_to_round:
        data.transferred_to_next = True
        data.transferred_to_round = transferred_to_round
    return data


def _parse_source_record_id(comment: str | None) -> int | None:
    if not comment:
        return None
    marker = AUTO_FROM_RECORD_MARKER
    if marker not in comment:
        return None
    try:
        value = comment.split(marker, 1)[1].split("]", 1)[0]
        return int(value)
    except (IndexError, ValueError):
        return None


def _parse_transferred_to_round(comment: str | None) -> str | None:
    if not comment:
        return None
    marker = PASSED_TO_MARKER
    if marker not in comment:
        return None
    try:
        return comment.split(marker, 1)[1].split("]", 1)[0]
    except (IndexError, ValueError):
        return None


def _strip_internal_markers(comment: str | None) -> str | None:
    if not comment:
        return comment
    value = comment
    for marker in (AUTO_FROM_RECORD_MARKER, PASSED_TO_MARKER):
        if marker in value:
            value = value.split(marker, 1)[0]
    value = value.strip()
    return value or None


def _append_passed_to_marker(comment: str | None, next_round: str) -> str:
    base = _strip_internal_markers(comment) or "审核通过"
    return f"{base} {PASSED_TO_MARKER}{next_round}]"


ROUND_REVIEWER_SELECT_STATUS = {
    "FIRST": WorkOrderStatus.FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND,
    "SECOND": WorkOrderStatus.SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD,
    "EXTERNAL_FIRST": WorkOrderStatus.EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND,
    "EXTERNAL_SECOND": WorkOrderStatus.EXTERNAL_SECOND_APPROVED_WAIT_RECALL_OR_THIRD,
}


def _round_leader_wait_status(review_round: str) -> WorkOrderStatus:
    if review_round == "FIRST":
        return WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND
    if review_round == "SECOND":
        return WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD
    if review_round == "EXTERNAL_FIRST":
        return WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT
    if review_round == "EXTERNAL_SECOND":
        return WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT
    raise HTTPException(status_code=400, detail="仅支持带下一轮转交流程的审核阶段")


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
    return (
        db.query(WorkOrderFile)
        .filter(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.business_stage == f"REVIEW_{review_round}",
            WorkOrderFile.file_category == file_category,
            WorkOrderFile.is_current.is_(True),
        )
        .order_by(WorkOrderFile.version_no.desc(), WorkOrderFile.id.desc())
        .all()
    )


def _has_current_round_file(db: Session, work_order_id: int, review_round: str, file_category: str) -> bool:
    return (
        db.query(WorkOrderFile.id)
        .filter(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.business_stage == f"REVIEW_{review_round}",
            WorkOrderFile.file_category == file_category,
            WorkOrderFile.is_current.is_(True),
        )
        .first()
        is not None
    )


def _latest_rejection_record(db: Session, work_order_id: int, review_round: str) -> ReviewRecord | None:
    return (
        db.query(ReviewRecord)
        .filter(
            ReviewRecord.work_order_id == work_order_id,
            ReviewRecord.review_round == review_round,
            ReviewRecord.action == "REJECT_RETURN",
        )
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .first()
    )


def _clone_files_to_round(
    db: Session,
    *,
    work_order_id: int,
    from_round: str,
    to_round: str,
    uploaded_by: int,
) -> None:
    stage_to = f"REVIEW_{to_round}"
    clone_categories = ("REPORT_ZIP", "EXTERNAL_AUDIT_OPINION") if from_round.startswith("EXTERNAL") else ("REPORT_ZIP",)
    for file_category in clone_categories:
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
    if review_round.startswith("EXTERNAL_"):
        return True
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
    if current_round == "EXTERNAL_FIRST":
        if not work_order.second_reviewer_id:
            return WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT, work_order.project_leader_id, f"{current_round}_APPROVE"
        _clone_files_to_round(
            db,
            work_order_id=work_order.id,
            from_round=current_round,
            to_round="EXTERNAL_SECOND",
            uploaded_by=work_order.project_leader_id,
        )
        db.add(
            ReviewRecord(
                work_order_id=work_order.id,
                review_round="EXTERNAL_SECOND",
                reviewer_user_id=work_order.second_reviewer_id,
                action="SUBMIT",
                comment=f"来源于上一轮自动流转 [AUTO_FROM_RECORD:{approved_record.id}]",
                acted_at=datetime.now(timezone.utc),
            )
        )
        return WorkOrderStatus.EXTERNAL_SECOND_REVIEWING, work_order.second_reviewer_id, "SUBMIT_EXTERNAL_SECOND"

    if current_round == "EXTERNAL_SECOND":
        if not work_order.third_reviewer_id:
            return WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT, work_order.project_leader_id, f"{current_round}_APPROVE"
        _clone_files_to_round(
            db,
            work_order_id=work_order.id,
            from_round=current_round,
            to_round="EXTERNAL_THIRD",
            uploaded_by=work_order.project_leader_id,
        )
        db.add(
            ReviewRecord(
                work_order_id=work_order.id,
                review_round="EXTERNAL_THIRD",
                reviewer_user_id=work_order.third_reviewer_id,
                action="SUBMIT",
                comment=f"来源于上一轮自动流转 [AUTO_FROM_RECORD:{approved_record.id}]",
                acted_at=datetime.now(timezone.utc),
            )
        )
        return WorkOrderStatus.EXTERNAL_THIRD_REVIEWING, work_order.third_reviewer_id, "SUBMIT_EXTERNAL_THIRD"

    next_round = ROUND_NEXT.get(current_round)
    if not next_round:
        if current_round == "EXTERNAL_THIRD":
            work_order.signoff_status = "WAIT_UPLOAD"
            return WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD, work_order.project_leader_id, f"{current_round}_APPROVE"
        if project and project.evaluation_business_nature == STATE_OWNED_EVAL_NATURE:
            return WorkOrderStatus.THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND, current_reviewer.id, f"{current_round}_APPROVE"
        work_order.signoff_status = "WAIT_UPLOAD"
        return WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD, work_order.project_leader_id, f"{current_round}_APPROVE"
    if not _latest_report_file_owner_is_project_party(db, work_order, current_round):
        return ROUND_APPROVED_STATUS[current_round], work_order.project_leader_id, f"{current_round}_APPROVE"

    _clone_files_to_round(
        db,
        work_order_id=work_order.id,
        from_round=current_round,
        to_round=next_round,
        uploaded_by=current_reviewer.id,
    )
    next_reviewer_id = getattr(work_order, ROUND_CURRENT_REVIEWER_ATTR[next_round])
    if not next_reviewer_id:
        return ROUND_APPROVED_STATUS[current_round], work_order.project_leader_id, f"{current_round}_APPROVE"
    db.add(
        ReviewRecord(
            work_order_id=work_order.id,
            review_round=next_round,
            reviewer_user_id=next_reviewer_id,
            action="SUBMIT",
            comment=f"沿用上一轮审核通过文件 {AUTO_FROM_RECORD_MARKER}{approved_record.id}]",
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
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "FIRST_REVIEWER", "SECOND_REVIEWER", "ADMIN")),
) -> ReviewCandidateListResponse:
    if review_round not in ROUND_ROLE_CODE:
        raise HTTPException(status_code=400, detail="非法审核轮次")

    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if "ADMIN" not in role_codes:
        can_view_as_project_party = _is_project_party(db, work_order, current_user)
        can_view_as_current_reviewer = current_user.id in {
            work_order.first_reviewer_id,
            work_order.second_reviewer_id,
        }
        if not can_view_as_project_party and not can_view_as_current_reviewer:
            raise HTTPException(status_code=403, detail="仅项目负责人、项目组成员或当前审核老师可查看审核候选人")

    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    current_round_existing = {
        "FIRST": work_order.first_reviewer_id,
        "SECOND": work_order.second_reviewer_id,
        "THIRD": work_order.third_reviewer_id,
        "EXTERNAL_FIRST": work_order.first_reviewer_id,
        "EXTERNAL_SECOND": work_order.second_reviewer_id,
        "EXTERNAL_THIRD": work_order.third_reviewer_id,
    }[review_round]

    if review_round == "EXTERNAL_SECOND":
        reviewer = db.query(User).filter(User.id == work_order.second_reviewer_id, User.is_active.is_(True)).first()
        return ReviewCandidateListResponse(
            items=[ReviewCandidateResponse(user_id=reviewer.id, username=reviewer.username, real_name=reviewer.real_name)] if reviewer else []
        )
    if review_round == "EXTERNAL_THIRD":
        reviewer = db.query(User).filter(User.id == work_order.third_reviewer_id, User.is_active.is_(True)).first()
        return ReviewCandidateListResponse(
            items=[ReviewCandidateResponse(user_id=reviewer.id, username=reviewer.username, real_name=reviewer.real_name)] if reviewer else []
        )

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
) -> ReviewRecordResponse:
    return _submit_review_impl(payload=payload, db=db, current_user=current_user)


def _submit_review_impl(
    *,
    payload: ReviewSubmitRequest,
    db: Session,
    current_user: User,
    role_codes: set[str] | None = None,
) -> ReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    role_codes = role_codes or {item.role.code for item in current_user.roles}
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
    if payload.review_round in {"FIRST", "SECOND", "THIRD"}:
        validate_not_project_party(
            target_reviewer_id,
            get_project_party_user_ids(db, work_order.project_id, work_order, project),
            f"{payload.review_round}???",
        )
        validate_reviewer_round_conflict(target_reviewer_id, work_order, payload.review_round)

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
    if not _has_current_round_file(db, work_order.id, payload.review_round, "REPORT_ZIP"):
        raise HTTPException(status_code=400, detail="请先上传待审报告资料包")

    latest_rejection = _latest_rejection_record(db, work_order.id, payload.review_round)
    if latest_rejection and from_status == ROUND_REJECTED_STATUS[payload.review_round]:
        has_reply_file = _has_current_round_file(db, work_order.id, payload.review_round, "REVIEW_REPLY")
        if not has_reply_file and not (payload.comment and payload.comment.strip()):
            raise HTTPException(status_code=400, detail="退回修改后重新送审时，审核意见回复文件或送审备注必须填写一项")

    if payload.review_round in {"FIRST", "EXTERNAL_FIRST"}:
        work_order.first_reviewer_id = target_reviewer_id
    elif payload.review_round in {"SECOND", "EXTERNAL_SECOND"}:
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
) -> ReviewRecordResponse:
    return _change_reviewer_after_reject_impl(payload=payload, db=db, current_user=current_user)


def _change_reviewer_after_reject_impl(
    *,
    payload: ReviewAssigneeChangeRequest,
    db: Session,
    current_user: User,
    role_codes: set[str] | None = None,
) -> ReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    role_codes = role_codes or {item.role.code for item in current_user.roles}
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
    if payload.review_round in {"FIRST", "SECOND", "THIRD"}:
        validate_not_project_party(
            payload.reviewer_user_id,
            get_project_party_user_ids(db, work_order.project_id, work_order, project),
            f"{payload.review_round}???",
        )
        validate_reviewer_round_conflict(payload.reviewer_user_id, work_order, payload.review_round)
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


@router.post("/approve-routing", response_model=ReviewRecordResponse)
def route_approved_review(
    payload: ReviewApprovalRoutingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "FIRST_REVIEWER", "SECOND_REVIEWER", "ADMIN")),
) -> ReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if payload.review_round == "FIRST":
        approved_status = WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND
        reviewer_select_status = WorkOrderStatus.FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND
        reviewer_id = work_order.first_reviewer_id
        next_round = "SECOND"
    elif payload.review_round == "SECOND":
        approved_status = WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD
        reviewer_select_status = WorkOrderStatus.SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD
        reviewer_id = work_order.second_reviewer_id
        next_round = "THIRD"
    elif payload.review_round == "EXTERNAL_FIRST":
        approved_status = WorkOrderStatus.EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND
        reviewer_select_status = WorkOrderStatus.EXTERNAL_FIRST_APPROVED_WAIT_RECALL_OR_SECOND
        reviewer_id = work_order.first_reviewer_id
        next_round = "EXTERNAL_SECOND"
    else:
        approved_status = WorkOrderStatus.EXTERNAL_SECOND_APPROVED_WAIT_RECALL_OR_THIRD
        reviewer_select_status = WorkOrderStatus.EXTERNAL_SECOND_APPROVED_WAIT_RECALL_OR_THIRD
        reviewer_id = work_order.second_reviewer_id
        next_round = "EXTERNAL_THIRD"

    from_status_for_log = WorkOrderStatus(work_order.current_status)

    if payload.route_mode == "REVIEWER_SELECT_NEXT":
        if reviewer_id != current_user.id and "ADMIN" not in role_codes:
            raise HTTPException(status_code=403, detail="仅当前审核老师可直接选择下一轮审核人")
        if WorkOrderStatus(work_order.current_status) != reviewer_select_status:
            raise HTTPException(status_code=400, detail="当前状态不可进入审核人选下一轮")
        if not payload.reviewer_user_id:
            raise HTTPException(status_code=400, detail="请在转交弹窗中选择下一轮审核老师")
        project = db.query(Project).filter(Project.id == work_order.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        _ensure_reviewer_has_round_role(db, payload.reviewer_user_id, next_round)
        if next_round in {"SECOND", "THIRD"}:
            validate_not_project_party(
                payload.reviewer_user_id,
                get_project_party_user_ids(db, work_order.project_id, work_order, project),
                f"{next_round}审核人",
            )
            validate_reviewer_round_conflict(payload.reviewer_user_id, work_order, next_round)
        candidate_first = payload.reviewer_user_id if next_round == "FIRST" else work_order.first_reviewer_id
        candidate_second = payload.reviewer_user_id if next_round == "SECOND" else work_order.second_reviewer_id
        candidate_third = payload.reviewer_user_id if next_round == "THIRD" else work_order.third_reviewer_id
        ok, msg = validate_reviewer_avoidance(
            project_leader_id=work_order.project_leader_id,
            business_user_id=project.business_user_id,
            first_reviewer_id=candidate_first,
            second_reviewer_id=candidate_second,
            third_reviewer_id=candidate_third,
        )
        if not ok:
            raise HTTPException(status_code=400, detail=msg)

        target_status = ROUND_REVIEWING_STATUS[next_round]
        if not can_transit(reviewer_select_status, target_status):
            raise HTTPException(status_code=400, detail="非法状态流转")
        if next_round in {"SECOND", "EXTERNAL_SECOND"}:
            work_order.second_reviewer_id = payload.reviewer_user_id
        else:
            work_order.third_reviewer_id = payload.reviewer_user_id

        latest_approve = (
            db.query(ReviewRecord)
            .filter(
                ReviewRecord.work_order_id == work_order.id,
                ReviewRecord.review_round == payload.review_round,
                ReviewRecord.action == "APPROVE",
            )
            .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
            .first()
        )
        if not latest_approve:
            raise HTTPException(status_code=400, detail="未找到上一轮审核通过记录")
        if not _has_current_round_file(db, work_order.id, next_round, "REPORT_ZIP"):
            _clone_files_to_round(
                db,
                work_order_id=work_order.id,
                from_round=payload.review_round,
                to_round=next_round,
                uploaded_by=current_user.id,
            )
        db.add(
            ReviewRecord(
                work_order_id=work_order.id,
                review_round=next_round,
                reviewer_user_id=payload.reviewer_user_id,
                action="SUBMIT",
                comment=f"沿用上一轮审核通过文件 {AUTO_FROM_RECORD_MARKER}{latest_approve.id}]",
                acted_at=datetime.now(timezone.utc),
            )
        )
        work_order.current_status = target_status.value
        work_order.current_handler_user_id = payload.reviewer_user_id
        action_name = f"{payload.review_round}_APPROVE_REVIEWER_SELECT_{next_round}"
        target_name = db.query(User.real_name).filter(User.id == payload.reviewer_user_id).scalar() or "-"
        default_comment = f"审核老师决定直接转交下一轮审核人：{target_name}"
    else:
        if reviewer_id != current_user.id and "ADMIN" not in role_codes:
            raise HTTPException(status_code=403, detail="仅当前审核老师可决定是否退回项目负责人选人")
        if WorkOrderStatus(work_order.current_status) not in {approved_status, reviewer_select_status}:
            raise HTTPException(status_code=400, detail="当前状态不可返回项目负责人选择")
        target_status = _round_leader_wait_status(payload.review_round)
        if not can_transit(from_status_for_log, target_status):
            raise HTTPException(status_code=400, detail="非法状态流转")
        work_order.current_status = target_status.value
        work_order.current_handler_user_id = work_order.project_leader_id
        action_name = f"{payload.review_round}_APPROVE_RETURN_PROJECT_LEADER_SELECT_{next_round}"
        default_comment = "审核老师决定退回项目负责人选择下一轮审核人"

    record = ReviewRecord(
        work_order_id=work_order.id,
        review_round=payload.review_round,
        reviewer_user_id=current_user.id,
        action="CHANGE_REVIEWER",
        comment=payload.comment or default_comment,
        acted_at=datetime.now(timezone.utc),
    )
    db.add(record)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status_for_log.value,
        to_status=work_order.current_status,
        action_type=action_name,
        operator_user_id=current_user.id,
        remark=payload.comment,
    )
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if project:
        receiver = payload.reviewer_user_id if payload.route_mode == "REVIEWER_SELECT_NEXT" and payload.reviewer_user_id else work_order.project_leader_id
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=receiver,
            action_name=action_name,
            comment=payload.comment,
            biz_id=record.id,
        )
    db.commit()
    db.refresh(record)
    return _to_review_record_response(db, record)


@router.post("/recall-routing", response_model=ReviewRecordResponse)
def recall_routed_review(
    payload: ReviewRecallRoutingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("FIRST_REVIEWER", "SECOND_REVIEWER", "ADMIN")),
) -> ReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    previous_reviewer_attr = ROUND_PREVIOUS_REVIEWER_ATTR.get(payload.review_round)
    if not previous_reviewer_attr:
        raise HTTPException(status_code=400, detail="当前轮次不支持撤回转交")
    previous_reviewer_id = getattr(work_order, previous_reviewer_attr)
    current_reviewer_id = getattr(work_order, ROUND_CURRENT_REVIEWER_ATTR[payload.review_round])
    recall_status = ROUND_RECALL_TARGET_STATUS[payload.review_round]

    if previous_reviewer_id != current_user.id and "ADMIN" not in role_codes:
        raise HTTPException(status_code=403, detail="仅上一级审核/复核人员可撤回转交")

    if WorkOrderStatus(work_order.current_status) != ROUND_REVIEWING_STATUS[payload.review_round]:
        raise HTTPException(status_code=400, detail="仅下一级人员尚未审核通过前可撤回转交")

    latest_approve = (
        db.query(ReviewRecord)
        .filter(
            ReviewRecord.work_order_id == work_order.id,
            ReviewRecord.review_round == payload.review_round,
            ReviewRecord.action == "APPROVE",
        )
        .order_by(ReviewRecord.acted_at.desc(), ReviewRecord.id.desc())
        .first()
    )
    if latest_approve:
        raise HTTPException(status_code=400, detail="下一级已确认通过，不能撤回转交")

    work_order.current_status = recall_status.value
    work_order.current_handler_user_id = previous_reviewer_id
    record = ReviewRecord(
        work_order_id=work_order.id,
        review_round=payload.review_round,
        reviewer_user_id=current_user.id,
        action="CHANGE_REVIEWER",
        comment=payload.comment or "撤回转交",
        acted_at=datetime.now(timezone.utc),
    )
    db.add(record)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=ROUND_REVIEWING_STATUS[payload.review_round].value,
        to_status=recall_status.value,
        action_type=f"RECALL_ROUTING_{payload.review_round}",
        operator_user_id=current_user.id,
        remark=payload.comment,
    )
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if project:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=previous_reviewer_id,
            action_name=f"RECALL_ROUTING_{payload.review_round}",
            comment=payload.comment,
            biz_id=record.id,
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
        "EXTERNAL_FIRST": work_order.first_reviewer_id,
        "EXTERNAL_SECOND": work_order.second_reviewer_id,
        "EXTERNAL_THIRD": work_order.third_reviewer_id,
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
    if payload.action == "REJECT_RETURN":
        has_opinion_file = _has_current_round_file(db, work_order.id, payload.review_round, "REVIEW_OPINION")
        if not has_opinion_file and not (payload.comment and payload.comment.strip()):
            raise HTTPException(status_code=400, detail="返回修改时，审核意见文件或审核备注必须填写一项")

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = next_handler

    record = ReviewRecord(
        work_order_id=work_order.id,
        review_round=payload.review_round,
        reviewer_user_id=current_user.id,
        action=payload.action,
        comment=payload.comment or ("审核通过" if payload.action == "APPROVE" else f"{payload.review_round}审核意见返回修改"),
        acted_at=datetime.now(timezone.utc),
    )
    db.add(record)
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if payload.action == "APPROVE":
        default_status = ROUND_REVIEWER_SELECT_STATUS.get(payload.review_round, ROUND_APPROVED_STATUS[payload.review_round])
        if not can_transit(from_status, default_status):
            raise HTTPException(status_code=400, detail="非法状态迁移")
        if payload.review_round in {"FIRST", "SECOND"}:
            next_round = ROUND_NEXT[payload.review_round]
            if _latest_report_file_owner_is_project_party(db, work_order, payload.review_round):
                _clone_files_to_round(
                    db,
                    work_order_id=work_order.id,
                    from_round=payload.review_round,
                    to_round=next_round,
                    uploaded_by=current_user.id,
                )
                record.comment = _append_passed_to_marker(record.comment, next_round)
            to_status = ROUND_REVIEWER_SELECT_STATUS[payload.review_round]
            next_handler = current_user.id
            workflow_action = f"{payload.review_round}_APPROVE_WAIT_REVIEWER_SELECT_{next_round}"
        elif payload.review_round in {"EXTERNAL_FIRST", "EXTERNAL_SECOND"}:
            next_round = ROUND_NEXT[payload.review_round]
            if _latest_report_file_owner_is_project_party(db, work_order, payload.review_round):
                _clone_files_to_round(
                    db,
                    work_order_id=work_order.id,
                    from_round=payload.review_round,
                    to_round=next_round,
                    uploaded_by=current_user.id,
                )
                record.comment = _append_passed_to_marker(record.comment, next_round)
            to_status = ROUND_REVIEWER_SELECT_STATUS[payload.review_round]
            next_handler = current_user.id
            workflow_action = f"{payload.review_round}_APPROVE_WAIT_REVIEWER_SELECT_{next_round}"
        else:
            to_status, next_handler, workflow_action = _auto_advance_if_needed(
                db,
                work_order=work_order,
                current_round=payload.review_round,
                current_reviewer=current_user,
                project=project,
                approved_record=record,
            )
            transferred_round = ROUND_NEXT.get(payload.review_round)
            if transferred_round and _latest_report_file_owner_is_project_party(db, work_order, payload.review_round):
                record.comment = _append_passed_to_marker(record.comment, transferred_round)
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
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if project:
        workflow_action = (
            f"{payload.review_round}_APPROVE"
            if payload.action == "APPROVE"
            else f"{payload.review_round}_REJECT_RETURN"
        )
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

    if latest.action == "APPROVE":
        next_round = _parse_transferred_to_round(latest.comment)
        if next_round:
            carried_categories = {"REPORT_ZIP", "REVIEW_OPINION"}
            carried_categories.add("EXTERNAL_AUDIT_OPINION" if review_round.startswith("EXTERNAL_") else "REVIEW_REPLY")
            carried_stage = f"REVIEW_{next_round}"
            carried_files = db.query(WorkOrderFile).filter(
                WorkOrderFile.work_order_id == work_order_id,
                WorkOrderFile.business_stage == carried_stage,
                WorkOrderFile.file_category.in_(carried_categories),
            ).all()
            for carried_file in carried_files:
                path = Path(settings.local_storage_dir) / carried_file.storage_key
                if path.exists():
                    path.unlink()
                db.delete(carried_file)
            carried_records = db.query(ReviewRecord).filter(
                ReviewRecord.work_order_id == work_order_id,
                ReviewRecord.review_round == next_round,
                ReviewRecord.action == "SUBMIT",
                ReviewRecord.comment.contains(f"{AUTO_FROM_RECORD_MARKER}{latest.id}]"),
            ).all()
            for carried_record in carried_records:
                db.delete(carried_record)

    work_order.current_status = rollback_status.value
    work_order.current_handler_user_id = rollback_handler
    db.delete(latest)
    db.commit()
    return {"status": "ok"}
