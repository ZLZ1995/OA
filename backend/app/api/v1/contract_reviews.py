from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.contract_review_record import ContractReviewRecord
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.contract_review import (
    ContractReviewDecisionRequest,
    ContractReviewFileResponse,
    ContractReviewRecordListResponse,
    ContractReviewRecordResponse,
    ContractReviewSubmitRequest,
)
from app.services.workflow_notification_service import send_workflow_notification
from app.services.workflow_log_service import create_workflow_log
from app.workflows.states import WorkOrderStatus
from app.workflows.transitions import can_transit

router = APIRouter(prefix="/contract-reviews", tags=["合同审核"])

CONTRACT_DRAFT_FILE_CATEGORY = "CONTRACT_DRAFT"
CONTRACT_DRAFT_STAGE = "CONTRACT_DRAFT"

CONTRACT_STATUS_LABELS = {
    WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value: "待上传合同",
    WorkOrderStatus.CONTRACT_UPLOADED.value: "合同已上传",
    WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT.value: "待提交合同审核",
    WorkOrderStatus.CONTRACT_REVIEWING.value: "合同审核中",
    WorkOrderStatus.CONTRACT_REJECTED.value: "合同审核退回",
    WorkOrderStatus.CONTRACT_APPROVED.value: "合同审核通过",
}


def get_contract_review_status_display(status: str | None) -> str | None:
    return CONTRACT_STATUS_LABELS.get(status or "")


def _ensure_contract_reviewer(db: Session, user_id: int) -> None:
    exists = (
        db.query(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(User, User.id == UserRole.user_id)
        .filter(User.id == user_id, User.is_active.is_(True), Role.code == "CONTRACT_REVIEWER")
        .first()
    )
    if not exists:
        raise HTTPException(status_code=400, detail="请选择有效的合同审核人")


def _ensure_project_operator(db: Session, work_order: WorkOrder, user: User) -> None:
    if any(item.role.code == "ADMIN" for item in user.roles):
        return
    if user.id in {work_order.initiator_user_id, work_order.project_leader_id}:
        return
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if project and project.project_source == "EXTERNAL":
        raise HTTPException(status_code=403, detail="评估二部项目仅项目创建人或项目负责人可操作")
    is_member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == user.id,
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="仅项目方人员可操作合同审核")


def _get_current_contract_file(db: Session, work_order_id: int) -> WorkOrderFile | None:
    return (
        db.query(WorkOrderFile)
        .filter(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.file_category == CONTRACT_DRAFT_FILE_CATEGORY,
            WorkOrderFile.business_stage == CONTRACT_DRAFT_STAGE,
            WorkOrderFile.is_current.is_(True),
        )
        .order_by(WorkOrderFile.version_no.desc())
        .first()
    )


def _serialize_file(file_row: WorkOrderFile | None) -> ContractReviewFileResponse | None:
    if not file_row:
        return None
    return ContractReviewFileResponse(
        id=file_row.id,
        origin_file_name=file_row.origin_file_name,
        file_size=file_row.file_size,
        uploaded_at=file_row.uploaded_at,
    )


def _serialize_record(db: Session, record: ContractReviewRecord) -> ContractReviewRecordResponse:
    operator_name = db.query(User.real_name).filter(User.id == record.operator_user_id).scalar()
    reviewer_name = db.query(User.real_name).filter(User.id == record.reviewer_user_id).scalar()
    contract_file = db.query(WorkOrderFile).filter(WorkOrderFile.id == record.contract_file_id).first() if record.contract_file_id else None
    review_file = db.query(WorkOrderFile).filter(WorkOrderFile.id == record.review_attachment_file_id).first() if record.review_attachment_file_id else None
    return ContractReviewRecordResponse(
        id=record.id,
        work_order_id=record.work_order_id,
        project_id=record.project_id,
        action_type=record.action_type,
        operator_user_id=record.operator_user_id,
        operator_user_name=operator_name,
        reviewer_user_id=record.reviewer_user_id,
        reviewer_user_name=reviewer_name,
        comment=record.comment,
        contract_file_id=record.contract_file_id,
        review_attachment_file_id=record.review_attachment_file_id,
        contract_file=_serialize_file(contract_file),
        review_attachment_file=_serialize_file(review_file),
        created_at=record.created_at,
    )


@router.get("", response_model=ContractReviewRecordListResponse)
def list_contract_reviews(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ContractReviewRecordListResponse:
    rows = (
        db.query(ContractReviewRecord)
        .filter(ContractReviewRecord.work_order_id == work_order_id)
        .order_by(ContractReviewRecord.created_at.desc(), ContractReviewRecord.id.desc())
        .all()
    )
    return ContractReviewRecordListResponse(items=[_serialize_record(db, row) for row in rows])


@router.post("/submit", response_model=ContractReviewRecordResponse)
def submit_contract_review(
    payload: ContractReviewSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER", "PROJECT_MEMBER")),
) -> ContractReviewRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _ensure_project_operator(db, work_order, current_user)
    _ensure_contract_reviewer(db, payload.reviewer_user_id)

    contract_file = _get_current_contract_file(db, work_order.id)
    if not contract_file:
        raise HTTPException(status_code=400, detail="请先上传合同扫描件")

    from_status = WorkOrderStatus(work_order.current_status)
    if from_status not in {WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT, WorkOrderStatus.CONTRACT_REJECTED, WorkOrderStatus.CONTRACT_UPLOADED}:
        raise HTTPException(status_code=400, detail="当前状态不可提交合同审核")

    if from_status == WorkOrderStatus.CONTRACT_UPLOADED:
        from_status = WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT
    to_status = WorkOrderStatus.CONTRACT_REVIEWING
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    work_order.contract_reviewer_id = payload.reviewer_user_id
    work_order.current_status = to_status.value
    work_order.current_handler_user_id = payload.reviewer_user_id

    record = ContractReviewRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="SUBMIT_CONTRACT",
        operator_user_id=current_user.id,
        reviewer_user_id=payload.reviewer_user_id,
        comment=payload.comment,
        contract_file_id=contract_file.id,
    )
    db.add(record)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="SUBMIT_CONTRACT_REVIEW",
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
            receiver_user_id=payload.reviewer_user_id,
            action_name="SUBMIT_CONTRACT_REVIEW",
            comment=payload.comment,
            biz_id=record.id,
        )
    db.commit()
    db.refresh(record)
    return _serialize_record(db, record)


@router.post("/{record_id}/approve", response_model=ContractReviewRecordResponse)
def approve_contract_review(
    record_id: int,
    payload: ContractReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("CONTRACT_REVIEWER", "ADMIN")),
) -> ContractReviewRecordResponse:
    record = db.query(ContractReviewRecord).filter(ContractReviewRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="合同审核记录不存在")
    work_order = db.query(WorkOrder).filter(WorkOrder.id == record.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.contract_reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅当前合同审核人可通过合同")
    if WorkOrderStatus(work_order.current_status) != WorkOrderStatus.CONTRACT_REVIEWING:
        raise HTTPException(status_code=400, detail="当前状态不可审核通过")

    from_status = WorkOrderStatus.CONTRACT_REVIEWING
    to_status = WorkOrderStatus.CONTRACT_APPROVED
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.project_leader_id

    approve_record = ContractReviewRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="APPROVE_CONTRACT",
        operator_user_id=current_user.id,
        reviewer_user_id=current_user.id,
        comment=payload.comment or "合同审核通过",
        contract_file_id=_get_current_contract_file(db, work_order.id).id if _get_current_contract_file(db, work_order.id) else None,
        review_attachment_file_id=payload.review_attachment_file_id,
    )
    db.add(approve_record)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="APPROVE_CONTRACT_REVIEW",
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
            receiver_user_id=work_order.project_leader_id,
            action_name="APPROVE_CONTRACT_REVIEW",
            comment=payload.comment,
            biz_id=approve_record.id,
        )
    db.commit()
    db.refresh(approve_record)
    return _serialize_record(db, approve_record)


@router.post("/{record_id}/reject", response_model=ContractReviewRecordResponse)
def reject_contract_review(
    record_id: int,
    payload: ContractReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("CONTRACT_REVIEWER", "ADMIN")),
) -> ContractReviewRecordResponse:
    record = db.query(ContractReviewRecord).filter(ContractReviewRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="合同审核记录不存在")
    work_order = db.query(WorkOrder).filter(WorkOrder.id == record.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.contract_reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅当前合同审核人可退回合同")
    if WorkOrderStatus(work_order.current_status) != WorkOrderStatus.CONTRACT_REVIEWING:
        raise HTTPException(status_code=400, detail="当前状态不可退回")

    from_status = WorkOrderStatus.CONTRACT_REVIEWING
    to_status = WorkOrderStatus.CONTRACT_REJECTED
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.project_leader_id

    reject_record = ContractReviewRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="REJECT_CONTRACT",
        operator_user_id=current_user.id,
        reviewer_user_id=current_user.id,
        comment=payload.comment or "合同退回修改",
        contract_file_id=_get_current_contract_file(db, work_order.id).id if _get_current_contract_file(db, work_order.id) else None,
        review_attachment_file_id=payload.review_attachment_file_id,
    )
    db.add(reject_record)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="REJECT_CONTRACT_REVIEW",
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
            receiver_user_id=work_order.project_leader_id,
            action_name="REJECT_CONTRACT_REVIEW",
            comment=payload.comment,
            biz_id=reject_record.id,
        )
    db.commit()
    db.refresh(reject_record)
    return _serialize_record(db, reject_record)
