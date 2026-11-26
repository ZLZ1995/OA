from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from app.core.config import settings
from app.storage.local_storage import save_upload_file
from app.models.user_notification import UserNotification
from app.services.contract_revision import (
    APPROVALS, CONTRACT_STAGES, DELETED, PENDING_DELETE, contract_status,
    last_review, lock_work_order, purge_replaced_contracts, set_contract_status,
)
from app.services.contract_print_room_flow import has_current_stamped_contract_scan
from app.services.project_conflicts import upsert_conflict_snapshot_and_detect
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
    ContractReviewApproveTransferRequest,
    ContractReviewDecisionRequest,
    ContractReviewFileResponse,
    ContractReviewRecordListResponse,
    ContractReviewRecordResponse,
    ContractReviewSubmitRequest,
    ContractReviewTransferApprovedRequest,
)
from app.services.contract_print_room_flow import get_contract_print_room_status
from app.services.project_role_conflict_service import get_project_party_user_ids, validate_not_project_party
from app.services.workflow_log_service import create_workflow_log
from app.services.workflow_notification_service import send_workflow_notification
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
    WorkOrderStatus.WAIT_PRINT_ROOM_PROCESS.value: "待文印室处理",
    WorkOrderStatus.WAIT_PROJECT_LEADER_CONTRACT_CONFIRM.value: "待项目负责人确认",
    WorkOrderStatus.CONTRACT_PROCESS_COMPLETED.value: "合同流程办结",
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


def _ensure_print_room_handler(db: Session, user_id: int) -> None:
    exists = (
        db.query(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(User, User.id == UserRole.user_id)
        .filter(User.id == user_id, User.is_active.is_(True), Role.code == "PRINT_ROOM")
        .first()
    )
    if not exists:
        raise HTTPException(status_code=400, detail="请选择有效的文印室人员")


def _ensure_project_operator(db: Session, work_order: WorkOrder, user: User) -> None:
    if any(item.role.code == "ADMIN" for item in user.roles):
        return
    if user.id in {work_order.initiator_user_id, work_order.project_leader_id}:
        return
    is_member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == user.id,
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="仅项目方人员可操作合同审核")


def _ensure_project_operator_or_contract_reviewer(db: Session, work_order: WorkOrder, user: User) -> None:
    if any(item.role.code == "ADMIN" for item in user.roles):
        return
    if work_order.contract_reviewer_id == user.id:
        return
    _ensure_project_operator(db, work_order, user)


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
        downloadable=file_row.source_type not in {DELETED, PENDING_DELETE},
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


def _latest_review_contract_file_id(db: Session, work_order_id: int) -> int | None:
    record = (
        db.query(ContractReviewRecord)
        .filter(
            ContractReviewRecord.work_order_id == work_order_id,
            ContractReviewRecord.contract_file_id.isnot(None),
        )
        .order_by(ContractReviewRecord.created_at.desc(), ContractReviewRecord.id.desc())
        .first()
    )
    if record:
        return record.contract_file_id
    contract_file = _get_current_contract_file(db, work_order_id)
    return contract_file.id if contract_file else None


def ensure_current_submission(db: Session, record: ContractReviewRecord) -> None:
    active = last_review(db, record.work_order_id)
    current = _get_current_contract_file(db, record.work_order_id)
    if (not active or active.id != record.id or record.action_type != "SUBMIT_CONTRACT"
            or not current or record.contract_file_id != current.id):
        raise HTTPException(409, "本轮审核已结束或文件版本已变化，请刷新查看最新合同")


def finish_review_notice(db: Session, record: ContractReviewRecord) -> None:
    db.query(UserNotification).filter_by(
        work_order_id=record.work_order_id, user_id=record.reviewer_user_id,
        title="请处理合同审核", biz_type="WORKFLOW_TRANSFER", biz_id=record.id,
    ).update({"process_status": "PROCESSED"}, synchronize_session=False)


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
) -> ContractReviewRecordResponse:
    work_order = lock_work_order(db, payload.work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _ensure_project_operator(db, work_order, current_user)
    _ensure_contract_reviewer(db, payload.reviewer_user_id)
    validate_not_project_party(
        payload.reviewer_user_id,
        get_project_party_user_ids(db, work_order.project_id, work_order),
        "合同审核人",
    )

    contract_file = _get_current_contract_file(db, work_order.id)
    if not contract_file:
        raise HTTPException(status_code=400, detail="请先上传合同扫描件")

    from_status = WorkOrderStatus(contract_status(db, work_order) or work_order.current_status)
    if from_status not in {WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT, WorkOrderStatus.CONTRACT_REJECTED, WorkOrderStatus.CONTRACT_UPLOADED}:
        raise HTTPException(status_code=400, detail="当前状态不可提交合同审核")

    if from_status == WorkOrderStatus.CONTRACT_UPLOADED:
        from_status = WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT
    to_status = WorkOrderStatus.CONTRACT_REVIEWING
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    work_order.contract_reviewer_id = payload.reviewer_user_id
    set_contract_status(work_order, to_status.value, payload.reviewer_user_id)

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
    db.flush()
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
    work_order = lock_work_order(db, record.work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.contract_reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅当前合同审核人可通过合同")
    ensure_current_submission(db, record)
    if contract_status(db, work_order) != WorkOrderStatus.CONTRACT_REVIEWING.value:
        raise HTTPException(status_code=400, detail="当前状态不可审核通过")

    from_status = WorkOrderStatus.CONTRACT_REVIEWING
    to_status = WorkOrderStatus.CONTRACT_APPROVED
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    set_contract_status(work_order, to_status.value, work_order.project_leader_id)

    approve_record = ContractReviewRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="APPROVE_CONTRACT",
        operator_user_id=current_user.id,
        reviewer_user_id=current_user.id,
        comment=payload.comment or "合同审核通过",
        contract_file_id=record.contract_file_id,
        review_attachment_file_id=payload.review_attachment_file_id,
    )
    finish_review_notice(db, record)
    db.add(approve_record)
    db.flush()
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


@router.post("/{record_id}/approve-and-transfer", response_model=ContractReviewRecordResponse)
def approve_and_transfer_contract_review(
    record_id: int,
    payload: ContractReviewApproveTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("CONTRACT_REVIEWER", "ADMIN")),
) -> ContractReviewRecordResponse:
    record = db.query(ContractReviewRecord).filter(ContractReviewRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="合同审核记录不存在")
    work_order = lock_work_order(db, record.work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.contract_reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅当前合同审核人可通过合同并转发文印室")
    ensure_current_submission(db, record)
    if contract_status(db, work_order) != WorkOrderStatus.CONTRACT_REVIEWING.value:
        raise HTTPException(status_code=400, detail="当前状态不可审核通过")

    _ensure_print_room_handler(db, payload.print_room_handler_id)
    validate_not_project_party(
        payload.print_room_handler_id,
        get_project_party_user_ids(db, work_order.project_id, work_order),
        "文印室办理人",
    )

    from_status = WorkOrderStatus.CONTRACT_REVIEWING
    to_status = WorkOrderStatus.CONTRACT_APPROVED
    if not can_transit(from_status, WorkOrderStatus.WAIT_PRINT_ROOM_PROCESS):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    set_contract_status(work_order, to_status.value, work_order.project_leader_id)
    work_order.contract_print_handler_id = payload.print_room_handler_id
    if work_order.current_status in CONTRACT_STAGES:
        work_order.print_room_handler_id = payload.print_room_handler_id

    approve_record = ContractReviewRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="APPROVE_AND_TRANSFER_PRINT_ROOM",
        operator_user_id=current_user.id,
        reviewer_user_id=current_user.id,
        comment=payload.comment or "合同审核通过，已转发文印室",
        contract_file_id=record.contract_file_id,
        review_attachment_file_id=payload.review_attachment_file_id,
    )
    finish_review_notice(db, record)
    db.add(approve_record)
    db.flush()
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="APPROVE_AND_TRANSFER_PRINT_ROOM",
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
            receiver_user_id=payload.print_room_handler_id,
            action_name="APPROVE_AND_TRANSFER_PRINT_ROOM",
            comment=payload.comment,
            biz_id=approve_record.id,
        )
    db.commit()
    db.refresh(approve_record)
    return _serialize_record(db, approve_record)


@router.post("/work-orders/{work_order_id}/transfer-approved", response_model=ContractReviewRecordResponse)
def transfer_approved_contract_to_print_room(
    work_order_id: int,
    payload: ContractReviewTransferApprovedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractReviewRecordResponse:
    work_order = lock_work_order(db, work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _ensure_project_operator_or_contract_reviewer(db, work_order, current_user)
    if contract_status(db, work_order) != WorkOrderStatus.CONTRACT_APPROVED.value:
        raise HTTPException(status_code=400, detail="当前状态不可转发文印室")
    if get_contract_print_room_status(db, work_order):
        raise HTTPException(status_code=400, detail="合同已转发文印室，请勿重复转发")

    _ensure_print_room_handler(db, payload.print_room_handler_id)
    validate_not_project_party(
        payload.print_room_handler_id,
        get_project_party_user_ids(db, work_order.project_id, work_order),
        "文印室办理人",
    )

    from_status = WorkOrderStatus.CONTRACT_APPROVED
    to_status = WorkOrderStatus.CONTRACT_APPROVED
    if not can_transit(from_status, WorkOrderStatus.WAIT_PRINT_ROOM_PROCESS):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    set_contract_status(work_order, to_status.value, work_order.project_leader_id)
    work_order.contract_print_handler_id = payload.print_room_handler_id
    if work_order.current_status in CONTRACT_STAGES:
        work_order.print_room_handler_id = payload.print_room_handler_id

    transfer_record = ContractReviewRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="TRANSFER_APPROVED_PRINT_ROOM",
        operator_user_id=current_user.id,
        reviewer_user_id=work_order.contract_reviewer_id or current_user.id,
        comment=payload.comment or "合同已审核通过，补充转发文印室",
        contract_file_id=_latest_review_contract_file_id(db, work_order.id),
    )
    db.add(transfer_record)
    db.flush()
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="TRANSFER_APPROVED_PRINT_ROOM",
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
            receiver_user_id=payload.print_room_handler_id,
            action_name="APPROVE_AND_TRANSFER_PRINT_ROOM",
            comment=payload.comment,
            biz_id=transfer_record.id,
        )
    db.commit()
    db.refresh(transfer_record)
    return _serialize_record(db, transfer_record)


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
    work_order = lock_work_order(db, record.work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.contract_reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅当前合同审核人可退回合同")
    ensure_current_submission(db, record)
    if contract_status(db, work_order) != WorkOrderStatus.CONTRACT_REVIEWING.value:
        raise HTTPException(status_code=400, detail="当前状态不可退回")

    from_status = WorkOrderStatus.CONTRACT_REVIEWING
    to_status = WorkOrderStatus.CONTRACT_REJECTED
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    set_contract_status(work_order, to_status.value, work_order.project_leader_id)

    reject_record = ContractReviewRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="REJECT_CONTRACT",
        operator_user_id=current_user.id,
        reviewer_user_id=current_user.id,
        comment=payload.comment or "合同退回修改",
        contract_file_id=record.contract_file_id,
        review_attachment_file_id=payload.review_attachment_file_id,
    )
    finish_review_notice(db, record)
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


@router.post("/work-orders/{work_order_id}/revise", response_model=ContractReviewRecordResponse)
def revise_approved_contract(
    work_order_id: int,
    approval_id: int = Form(...),
    expected_print_status: str = Form(...),
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = lock_work_order(db, work_order_id)
    if not order:
        raise HTTPException(404, "工单不存在")
    if current_user.id != order.project_leader_id:
        raise HTTPException(403, "仅本项目负责人可撤回合同")
    project = db.get(Project, order.project_id)
    if project.archived_at or project.deleted_at or project.termination_status in {"APPROVED", "PENDING", "DELETE_PENDING"}:
        raise HTTPException(409, "当前项目状态不可撤回合同")

    approval = last_review(db, order.id)
    old = _get_current_contract_file(db, order.id)
    if (not approval or approval.action_type not in APPROVALS or approval.id != approval_id
            or not old or old.id != approval.contract_file_id
            or contract_status(db, order) not in {"CONTRACT_APPROVED", "WAIT_PRINT_ROOM_PROCESS"}):
        raise HTTPException(409, "无法匹配当前已通过的合同及审核记录，请刷新后核对")
    print_status = get_contract_print_room_status(db, order)
    if (expected_print_status != (print_status or "NONE")
            or print_status not in {None, "WAIT_PRINT_ROOM_PROCESS"}
            or has_current_stamped_contract_scan(db, order.id)):
        raise HTTPException(409, "文印进度已变化或已有盖章件，请刷新后按当前进度办理")
    reviewer_id = approval.reviewer_user_id
    reviewer = db.get(User, reviewer_id)
    if not reviewer or not reviewer.is_active or not any(
        link.role.code in {"ADMIN", "CONTRACT_REVIEWER"} for link in reviewer.roles
    ):
        raise HTTPException(409, "原审核人已停用或缺少审核权限，原合同仍然有效")
    validate_not_project_party(reviewer_id, get_project_party_user_ids(db, project.id, order), "合同审核人")
    if not upload.filename or len(upload.filename) > 255:
        raise HTTPException(400, "请选择有效的合同文件，文件名最长255个字符")

    old_id = old.id
    key, size = save_upload_file(upload)
    try:
        if size == 0:
            raise HTTPException(400, "不能提交空文件")
        new = WorkOrderFile(
            work_order_id=order.id, file_category=old.file_category, business_stage=old.business_stage,
            version_no=old.version_no + 1, is_current=True, origin_file_name=upload.filename,
            storage_key=key, file_size=size, uploaded_by=current_user.id,
            uploaded_at=datetime.now(timezone.utc),
        )
        old.is_current = False
        old.source_type = PENDING_DELETE
        db.add(new)
        db.flush()
        record = ContractReviewRecord(
            work_order_id=order.id, project_id=project.id, operator_user_id=current_user.id,
            reviewer_user_id=reviewer_id, action_type="SUBMIT_CONTRACT", contract_file_id=new.id,
            comment=f"撤回第{old.version_no}版合同，提交第{new.version_no}版重新审核",
        )
        db.add(record)
        db.flush()
        if print_status and order.contract_print_assignee:
            handler = order.contract_print_assignee
            db.query(UserNotification).filter_by(
                work_order_id=order.id, user_id=handler, biz_type="WORKFLOW_TRANSFER",
                title="请处理合同文印", process_status="PENDING",
            ).update({"process_status": "PROCESSED"}, synchronize_session=False)
            send_workflow_notification(db, project=project, work_order=order, sender_user=current_user,
                                       receiver_user_id=handler, action_name="CANCEL_CONTRACT_PRINT",
                                       comment="原版合同已撤回，请停止文印。", biz_id=record.id)
            if order.current_status in CONTRACT_STAGES:
                order.print_room_handler_id = None
            order.contract_print_handler_id = None
        set_contract_status(order, "CONTRACT_REVIEWING", reviewer_id)
        order.contract_reviewer_id = reviewer_id
        create_workflow_log(db, work_order_id=order.id, from_status="CONTRACT_APPROVED",
                            to_status="CONTRACT_REVIEWING", action_type="WITHDRAW_APPROVED_CONTRACT",
                            operator_user_id=current_user.id, remark=record.comment)
        upsert_conflict_snapshot_and_detect(db, project, order, new.uploaded_at)
        send_workflow_notification(db, project=project, work_order=order, sender_user=current_user,
                                   receiver_user_id=reviewer_id, action_name="SUBMIT_CONTRACT_REVIEW",
                                   comment=record.comment, biz_id=record.id)
        db.commit()
    except Exception:
        db.rollback()
        (Path(settings.local_storage_dir) / key).unlink(missing_ok=True)
        raise
    purge_replaced_contracts(db, old_id)
    return _serialize_record(db, record)
