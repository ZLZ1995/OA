from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.file import WorkOrderFileListResponse, WorkOrderFileResponse
from app.services.archive_sync_service import SIGNOFF_SYNC_SOURCE_TYPE, is_signoff_source_category, refresh_archive_synced_file_by_source
from app.services.project_conflicts import upsert_conflict_snapshot_and_detect
from app.storage.local_storage import save_upload_file
from app.workflows.states import WorkOrderStatus

router = APIRouter(prefix="/files", tags=["files"])

CONTRACT_DRAFT_FILE_CATEGORY = "CONTRACT_DRAFT"
FINAL_CONTRACT_SCAN_FILE_CATEGORY = "FINAL_CONTRACT_SCAN"
CONTRACT_DRAFT_STAGE = "CONTRACT_DRAFT"
FINAL_CONTRACT_SCAN_STAGE = "FINAL_CONTRACT_SCAN"
FORMAL_REPORT_FILE_CATEGORY = "FORMAL_REPORT"
FORMAL_REPORT_STAGE = "FORMAL_REPORT"
REVIEW_STAGE_PREFIX = "REVIEW_"


def _user_name(db: Session, user_id: int) -> str | None:
    return db.query(User.real_name).filter(User.id == user_id).scalar()


def _to_file_response(db: Session, row: WorkOrderFile) -> WorkOrderFileResponse:
    display_label = None
    if row.source_type == SIGNOFF_SYNC_SOURCE_TYPE:
        display_label = "签发同步文件"
    elif row.file_category == "ELECTRONIC_DRAFT":
        display_label = "电子底稿"
    return WorkOrderFileResponse(
        id=row.id,
        work_order_id=row.work_order_id,
        file_category=row.file_category,
        business_stage=row.business_stage,
        version_no=row.version_no,
        is_current=row.is_current,
        origin_file_name=row.origin_file_name,
        storage_key=row.storage_key,
        file_size=row.file_size,
        uploaded_by=row.uploaded_by,
        uploaded_by_name=_user_name(db, row.uploaded_by),
        uploaded_at=row.uploaded_at,
        source_type=row.source_type,
        source_file_id=row.source_file_id,
        locked=row.locked,
        display_label=display_label,
    )


def _ensure_project_contract_operator(db: Session, work_order: WorkOrder, current_user: User) -> None:
    if any(item.role.code == "ADMIN" for item in current_user.roles):
        return
    if current_user.id in {work_order.project_leader_id, work_order.initiator_user_id}:
        return
    is_member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == current_user.id,
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人、创建人或项目组成员可操作合同")


def _ensure_project_signoff_operator(db: Session, work_order: WorkOrder, current_user: User) -> None:
    if any(item.role.code == "ADMIN" for item in current_user.roles):
        return
    if current_user.id in {work_order.project_leader_id, work_order.initiator_user_id}:
        return
    is_member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == current_user.id,
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人、创建人或项目组成员可上传报告附件和合同扫描件")


def _get_latest_file(
    db: Session,
    work_order_id: int,
    *,
    file_category: str,
    business_stage: str,
) -> WorkOrderFile | None:
    return (
        db.query(WorkOrderFile)
        .filter(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.file_category == file_category,
            WorkOrderFile.business_stage == business_stage,
            WorkOrderFile.is_current.is_(True),
        )
        .order_by(WorkOrderFile.version_no.desc())
        .first()
    )


def _ensure_review_package_unlocked(work_order: WorkOrder, row: WorkOrderFile) -> None:
    if work_order.current_status not in {
        WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value,
        WorkOrderStatus.THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND.value,
        WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM.value,
        WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value,
        WorkOrderStatus.SIGNOFF_REVIEWING.value,
    }:
        return
    if row.file_category not in {"REPORT_ZIP", "REVIEW_REPLY"}:
        return
    if not row.business_stage.startswith(REVIEW_STAGE_PREFIX):
        return
    raise HTTPException(status_code=400, detail="报告资料包已在三审通过后锁定，请先撤回三审审核通过后再修改")


def _ensure_upload_permission(
    db: Session,
    *,
    work_order: WorkOrder,
    current_user: User,
    file_category: str,
) -> None:
    if file_category == "ELECTRONIC_DRAFT":
        return
    if file_category == CONTRACT_DRAFT_FILE_CATEGORY:
        if work_order.current_status in {WorkOrderStatus.CONTRACT_REVIEWING.value, WorkOrderStatus.CONTRACT_APPROVED.value}:
            raise HTTPException(status_code=400, detail="合同初稿在审核中或已通过，已锁定")
        _ensure_project_contract_operator(db, work_order, current_user)
        return

    if file_category == FORMAL_REPORT_FILE_CATEGORY:
        if work_order.current_status == WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value:
            _ensure_project_signoff_operator(db, work_order, current_user)
            return
        if work_order.current_status != WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value:
            raise HTTPException(status_code=400, detail="三审通过或进入签发附件上传流程后才可上传报告附件")
        if current_user.id != work_order.third_reviewer_id:
            raise HTTPException(status_code=403, detail="仅三审老师可上传正式报告文件")
        return

    if file_category == FINAL_CONTRACT_SCAN_FILE_CATEGORY:
        if work_order.current_status == WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value:
            _ensure_project_signoff_operator(db, work_order, current_user)
            return
        if work_order.current_status != WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value:
            raise HTTPException(status_code=400, detail="三审通过或进入签发附件上传流程后才可上传合同扫描件")
        if current_user.id != work_order.third_reviewer_id and not any(item.role.code == "ADMIN" for item in current_user.roles):
            raise HTTPException(status_code=403, detail="仅三审老师可上传合同扫描件")


@router.post("/upload", response_model=WorkOrderFileResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    work_order_id: int = Form(...),
    file_category: str = Form(...),
    business_stage: str = Form(...),
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(
        require_roles(
            "ADMIN",
            "SALES",
            "PROJECT_LEADER",
            "PROJECT_MEMBER",
            "PRINT_ROOM",
            "FINANCE",
            "CONTRACT_REVIEWER",
            "FIRST_REVIEWER",
            "SECOND_REVIEWER",
            "THIRD_REVIEWER",
            "ARCHIVE_MANAGER",
            "CHIEF_APPRAISER",
        )
    ),
) -> WorkOrderFileResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    _ensure_upload_permission(db, work_order=work_order, current_user=current_user, file_category=file_category)

    latest_same_slot = _get_latest_file(
        db,
        work_order_id,
        file_category=file_category,
        business_stage=business_stage,
    )
    if latest_same_slot:
        _ensure_review_package_unlocked(work_order, latest_same_slot)

    latest = (
        db.query(WorkOrderFile)
        .filter(
            and_(
                WorkOrderFile.work_order_id == work_order_id,
                WorkOrderFile.file_category == file_category,
                WorkOrderFile.business_stage == business_stage,
            )
        )
        .order_by(WorkOrderFile.version_no.desc())
        .first()
    )
    next_version = 1 if not latest else latest.version_no + 1

    db.query(WorkOrderFile).filter(
        and_(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.file_category == file_category,
            WorkOrderFile.business_stage == business_stage,
            WorkOrderFile.is_current.is_(True),
        )
    ).update({"is_current": False})

    storage_key, file_size = save_upload_file(upload)
    row = WorkOrderFile(
        work_order_id=work_order_id,
        file_category=file_category,
        business_stage=business_stage,
        version_no=next_version,
        is_current=True,
        origin_file_name=upload.filename or "unknown",
        storage_key=storage_key,
        file_size=file_size,
        uploaded_by=current_user.id,
        uploaded_at=datetime.now(timezone.utc),
        source_type="MANUAL",
        source_file_id=None,
        locked=False,
    )
    db.add(row)

    if file_category == CONTRACT_DRAFT_FILE_CATEGORY and work_order.current_status in {
        WorkOrderStatus.WORK_ORDER_CREATED.value,
        WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value,
        WorkOrderStatus.CONTRACT_REJECTED.value,
    }:
        work_order.current_status = WorkOrderStatus.CONTRACT_UPLOADED.value
        work_order.current_handler_user_id = work_order.project_leader_id
    if file_category == CONTRACT_DRAFT_FILE_CATEGORY:
        project = db.query(Project).filter(Project.id == work_order.project_id).first()
        if project:
            upsert_conflict_snapshot_and_detect(db, project, work_order, row.uploaded_at)
    if is_signoff_source_category(file_category):
        db.flush()
        refresh_archive_synced_file_by_source(db, row)

    db.commit()
    db.refresh(row)
    return _to_file_response(db, row)


@router.get("/work-orders/{work_order_id}", response_model=WorkOrderFileListResponse)
def list_work_order_files(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WorkOrderFileListResponse:
    rows = (
        db.query(WorkOrderFile)
        .filter(WorkOrderFile.work_order_id == work_order_id)
        .order_by(WorkOrderFile.file_category.asc(), WorkOrderFile.business_stage.asc(), WorkOrderFile.version_no.desc())
        .all()
    )
    return WorkOrderFileListResponse(items=[_to_file_response(db, item) for item in rows])


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(
        require_roles(
            "ADMIN",
            "PROJECT_LEADER",
            "PROJECT_MEMBER",
            "FIRST_REVIEWER",
            "SECOND_REVIEWER",
            "THIRD_REVIEWER",
        )
    ),
) -> None:
    row = db.query(WorkOrderFile).filter(WorkOrderFile.id == file_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在")
    if row.locked:
        raise HTTPException(status_code=400, detail="该文件已锁定，不允许删除")
    if not row.is_current:
        raise HTTPException(status_code=400, detail="该文件已不是当前版本")

    work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _ensure_review_package_unlocked(work_order, row)

    if row.file_category in {"REPORT_ZIP", "REVIEW_REPLY"}:
        _ensure_project_signoff_operator(db, work_order, current_user)
    elif row.file_category == "REVIEW_OPINION":
        if row.uploaded_by != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
            raise HTTPException(status_code=403, detail="仅上传人可删除审核意见附件")
    else:
        raise HTTPException(status_code=400, detail="该类型文件暂不支持在此删除")

    row.is_current = False
    db.commit()


@router.post("/{file_id}/replace", response_model=WorkOrderFileResponse)
def replace_work_order_file(
    file_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(
        require_roles(
            "ADMIN",
            "SALES",
            "PROJECT_LEADER",
            "PROJECT_MEMBER",
            "PRINT_ROOM",
            "FINANCE",
            "CONTRACT_REVIEWER",
            "FIRST_REVIEWER",
            "SECOND_REVIEWER",
            "THIRD_REVIEWER",
            "ARCHIVE_MANAGER",
            "CHIEF_APPRAISER",
        )
    ),
) -> WorkOrderFileResponse:
    row = db.query(WorkOrderFile).filter(WorkOrderFile.id == file_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在")
    if row.locked:
        raise HTTPException(status_code=400, detail="该文件已锁定，不允许替换")

    work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if row.file_category == CONTRACT_DRAFT_FILE_CATEGORY:
        if work_order.current_status in {WorkOrderStatus.CONTRACT_REVIEWING.value, WorkOrderStatus.CONTRACT_APPROVED.value}:
            raise HTTPException(status_code=400, detail="合同初稿在审核中或已通过，已锁定")
        _ensure_project_contract_operator(db, work_order, current_user)

    if row.file_category == FINAL_CONTRACT_SCAN_FILE_CATEGORY:
        if work_order.current_status == WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value:
            _ensure_project_signoff_operator(db, work_order, current_user)
        else:
            if work_order.current_status != WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value:
                raise HTTPException(status_code=400, detail="当前状态不可替换合同扫描件")
            if current_user.id != work_order.third_reviewer_id and not any(item.role.code == "ADMIN" for item in current_user.roles):
                raise HTTPException(status_code=403, detail="仅三审老师可替换合同扫描件")

    if row.file_category == FORMAL_REPORT_FILE_CATEGORY:
        if work_order.current_status == WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value:
            _ensure_project_signoff_operator(db, work_order, current_user)
        else:
            if work_order.current_status != WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value:
                raise HTTPException(status_code=400, detail="当前状态不可替换报告附件")
            if current_user.id != work_order.third_reviewer_id:
                raise HTTPException(status_code=403, detail="仅三审老师可替换正式报告文件")

    _ensure_review_package_unlocked(work_order, row)

    old_path = Path(settings.local_storage_dir) / row.storage_key
    storage_key, file_size = save_upload_file(upload)
    row.origin_file_name = upload.filename or "unknown"
    row.storage_key = storage_key
    row.file_size = file_size
    row.uploaded_at = datetime.now(timezone.utc)
    if old_path.exists():
        old_path.unlink()
    if is_signoff_source_category(row.file_category):
        refresh_archive_synced_file_by_source(db, row)

    db.commit()
    db.refresh(row)
    return _to_file_response(db, row)


@router.post("/work-orders/{work_order_id}/complete-contract")
def complete_contract_upload(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER", "PROJECT_MEMBER")),
):
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _ensure_project_contract_operator(db, work_order, current_user)

    has_contract = _get_latest_file(
        db,
        work_order_id,
        file_category=CONTRACT_DRAFT_FILE_CATEGORY,
        business_stage=CONTRACT_DRAFT_STAGE,
    )
    if not has_contract:
        raise HTTPException(status_code=400, detail="请先上传合同初稿扫描件")
    if not work_order.contract_reviewer_id:
        raise HTTPException(status_code=400, detail="请先选择合同审核人")

    from_status = WorkOrderStatus(work_order.current_status)
    to_status = WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT
    if from_status == to_status:
        return {"status": "ok"}

    allowed_statuses = {
        WorkOrderStatus.WORK_ORDER_CREATED,
        WorkOrderStatus.WAIT_CONTRACT_UPLOAD,
        WorkOrderStatus.CONTRACT_UPLOADED,
        WorkOrderStatus.CONTRACT_REJECTED,
    }
    if from_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="当前工单状态无法提交合同初稿审核")

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.project_leader_id
    db.commit()
    return {"status": "ok"}


@router.get("/{file_id}/download")
def download_work_order_file(
    file_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.query(WorkOrderFile).filter(WorkOrderFile.id == file_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在")

    path = Path(settings.local_storage_dir) / row.storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件物理存储不存在")
    return FileResponse(path=path, filename=row.origin_file_name, media_type="application/octet-stream")
