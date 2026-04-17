from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.file import WorkOrderFileListResponse, WorkOrderFileResponse
from app.storage.local_storage import save_upload_file
from app.workflows.states import WorkOrderStatus

router = APIRouter(prefix="/files", tags=["文件"])


def _to_file_response(row: WorkOrderFile) -> WorkOrderFileResponse:
    return WorkOrderFileResponse(
        id=row.id,
        work_order_id=row.work_order_id,
        file_category=row.file_category,
        business_stage=row.business_stage,
        version_no=row.version_no,
        is_current=row.is_current,
        origin_file_name=row.origin_file_name,
        storage_key=row.storage_key,
        uploaded_by=row.uploaded_by,
        uploaded_at=row.uploaded_at,
    )


@router.post("/upload", response_model=WorkOrderFileResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    work_order_id: int = Form(...),
    file_category: str = Form(...),
    business_stage: str = Form(...),
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER", "PROJECT_MEMBER", "PRINT_ROOM", "FIRST_REVIEWER", "SECOND_REVIEWER", "THIRD_REVIEWER")),
) -> WorkOrderFileResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

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

    storage_key, _ = save_upload_file(upload)
    row = WorkOrderFile(
        work_order_id=work_order_id,
        file_category=file_category,
        business_stage=business_stage,
        version_no=next_version,
        is_current=True,
        origin_file_name=upload.filename or "unknown",
        storage_key=storage_key,
        uploaded_by=current_user.id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(row)

    if work_order.current_status == WorkOrderStatus.WORK_ORDER_CREATED.value and file_category == "CONTRACT":
        work_order.current_status = WorkOrderStatus.CONTRACT_UPLOADED.value
        work_order.current_handler_user_id = work_order.project_leader_id

    db.commit()
    db.refresh(row)
    return _to_file_response(row)


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
    return WorkOrderFileListResponse(items=[_to_file_response(item) for item in rows])
