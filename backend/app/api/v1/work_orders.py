from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.work_order import WorkOrderCreate, WorkOrderOut, WorkOrderUpdate

router = APIRouter(prefix="/work-orders", tags=["工单管理"])


@router.get("", response_model=list[WorkOrderOut])
def list_work_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkOrderOut]:
    require_roles(current_user, {"ADMIN", "PROJECT_LEADER", "PROJECT_MEMBER", "SALES"})
    rows = db.query(WorkOrder).order_by(WorkOrder.id.desc()).all()
    return [WorkOrderOut(**row.__dict__) for row in rows]


@router.post("", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkOrderOut:
    require_roles(current_user, {"ADMIN", "PROJECT_LEADER", "SALES"})
    exists = db.query(WorkOrder).filter(WorkOrder.work_order_no == payload.work_order_no).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="工单号已存在")

    row = WorkOrder(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return WorkOrderOut(**row.__dict__)


@router.get("/{work_order_id}", response_model=WorkOrderOut)
def get_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkOrderOut:
    require_roles(current_user, {"ADMIN", "PROJECT_LEADER", "PROJECT_MEMBER", "SALES"})
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")
    return WorkOrderOut(**row.__dict__)


@router.patch("/{work_order_id}", response_model=WorkOrderOut)
def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkOrderOut:
    require_roles(current_user, {"ADMIN", "PROJECT_LEADER", "SALES"})
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return WorkOrderOut(**row.__dict__)
