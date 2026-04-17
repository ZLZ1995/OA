from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.report_version import ReportVersion
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.schemas.report_version import ReportVersionCreate, ReportVersionListResponse, ReportVersionResponse

router = APIRouter(prefix="/report-versions", tags=["报告版本"])


@router.get("", response_model=ReportVersionListResponse)
def list_report_versions(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReportVersionListResponse:
    rows = (
        db.query(ReportVersion)
        .filter(ReportVersion.work_order_id == work_order_id)
        .order_by(ReportVersion.version_no.desc())
        .all()
    )
    return ReportVersionListResponse(
        items=[ReportVersionResponse.model_validate(item, from_attributes=True) for item in rows]
    )


@router.post("", response_model=ReportVersionResponse, status_code=status.HTTP_201_CREATED)
def create_report_version(
    payload: ReportVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN", "PROJECT_LEADER", "FIRST_REVIEWER", "SECOND_REVIEWER", "THIRD_REVIEWER")),
) -> ReportVersionResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    file_row = db.query(WorkOrderFile).filter(WorkOrderFile.id == payload.file_id).first()
    if not file_row or file_row.work_order_id != payload.work_order_id:
        raise HTTPException(status_code=400, detail="文件不存在或不属于该工单")

    latest = (
        db.query(ReportVersion)
        .filter(ReportVersion.work_order_id == payload.work_order_id)
        .order_by(ReportVersion.version_no.desc())
        .first()
    )
    next_version = 1 if not latest else latest.version_no + 1

    row = ReportVersion(
        work_order_id=payload.work_order_id,
        version_no=next_version,
        file_id=payload.file_id,
        submitted_by=current_user.id,
        submit_stage=payload.submit_stage,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReportVersionResponse.model_validate(row, from_attributes=True)
