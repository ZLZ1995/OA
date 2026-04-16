from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.work_order import WorkOrderCreate, WorkOrderItem, WorkOrderListResponse

router = APIRouter(prefix="/work-orders", tags=["工单"])


@router.post("", response_model=WorkOrderItem)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkOrderItem:
    work_order = WorkOrder(
        title=payload.title.strip(),
        description=payload.description.strip(),
        status="待处理",
        creator_id=current_user.id,
    )
    db.add(work_order)
    db.commit()
    db.refresh(work_order)
    return WorkOrderItem(
        id=work_order.id,
        title=work_order.title,
        description=work_order.description,
        status=work_order.status,
        created_at=work_order.created_at,
    )


@router.get("/mine", response_model=WorkOrderListResponse)
def list_my_work_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkOrderListResponse:
    rows = (
        db.query(WorkOrder)
        .filter(WorkOrder.creator_id == current_user.id)
        .order_by(WorkOrder.id.desc())
        .all()
    )
    return WorkOrderListResponse(
        items=[
            WorkOrderItem(
                id=row.id,
                title=row.title,
                description=row.description,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )
