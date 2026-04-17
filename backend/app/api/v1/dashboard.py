from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.dashboard import DashboardResponse
from app.schemas.work_order import WorkOrderResponse

router = APIRouter(prefix="/dashboard", tags=["首页"])


@router.get("/mine", response_model=DashboardResponse)
def my_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    todo_items = (
        db.query(WorkOrder)
        .filter(WorkOrder.current_handler_user_id == current_user.id)
        .order_by(WorkOrder.id.desc())
        .all()
    )
    created_items = (
        db.query(WorkOrder)
        .filter(WorkOrder.initiator_user_id == current_user.id)
        .order_by(WorkOrder.id.desc())
        .all()
    )

    return DashboardResponse(
        todo_items=[WorkOrderResponse.model_validate(item, from_attributes=True) for item in todo_items],
        created_items=[WorkOrderResponse.model_validate(item, from_attributes=True) for item in created_items],
    )
