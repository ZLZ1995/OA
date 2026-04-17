from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderListResponse,
    WorkOrderResponse,
    WorkOrderUpdate,
)
from app.workflows.states import WorkOrderStatus

router = APIRouter(prefix="/work-orders", tags=["工单"])


@router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WorkOrderListResponse:
    rows = db.query(WorkOrder).order_by(WorkOrder.id.desc()).all()
    return WorkOrderListResponse(
        items=[WorkOrderResponse.model_validate(item, from_attributes=True) for item in rows]
    )


@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER")),
) -> WorkOrderResponse:
    exists = db.query(WorkOrder).filter(WorkOrder.work_order_no == payload.work_order_no).first()
    if exists:
        raise HTTPException(status_code=400, detail="工单号已存在")

    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="关联项目不存在")

    row = WorkOrder(
        **payload.model_dump(),
        current_status=WorkOrderStatus.WORK_ORDER_CREATED.value,
        current_handler_user_id=project.project_leader_id,
        initiator_user_id=current_user.id,
        project_leader_id=project.project_leader_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return WorkOrderResponse.model_validate(row, from_attributes=True)


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WorkOrderResponse:
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")
    return WorkOrderResponse.model_validate(row, from_attributes=True)


@router.patch("/{work_order_id}", response_model=WorkOrderResponse)
def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER")),
) -> WorkOrderResponse:
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return WorkOrderResponse.model_validate(row, from_attributes=True)


@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> None:
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")
    db.delete(row)
    db.commit()
