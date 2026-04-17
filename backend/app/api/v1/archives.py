from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.archive import Archive
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.archive import ArchiveCreate, ArchiveListResponse, ArchiveResponse, ArchiveUpdate

router = APIRouter(prefix="/archives", tags=["归档"])


@router.get("", response_model=ArchiveListResponse)
def list_archives(
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ARCHIVE_MANAGER", "ADMIN")),
) -> ArchiveListResponse:
    rows = db.query(Archive).order_by(Archive.id.desc()).all()
    return ArchiveListResponse(items=[ArchiveResponse.model_validate(item, from_attributes=True) for item in rows])


@router.post("", response_model=ArchiveResponse, status_code=status.HTTP_201_CREATED)
def create_archive(
    payload: ArchiveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ARCHIVE_MANAGER", "ADMIN")),
) -> ArchiveResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    exists = db.query(Archive).filter(Archive.work_order_id == payload.work_order_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="该工单已归档")

    row = Archive(**payload.model_dump(), archived_by=current_user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ArchiveResponse.model_validate(row, from_attributes=True)


@router.patch("/{archive_id}", response_model=ArchiveResponse)
def update_archive(
    archive_id: int,
    payload: ArchiveUpdate,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ARCHIVE_MANAGER", "ADMIN")),
) -> ArchiveResponse:
    row = db.query(Archive).filter(Archive.id == archive_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="归档记录不存在")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ArchiveResponse.model_validate(row, from_attributes=True)
