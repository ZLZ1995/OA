from pydantic import BaseModel

from app.schemas.work_order import WorkOrderResponse


class DashboardResponse(BaseModel):
    todo_items: list[WorkOrderResponse]
    created_items: list[WorkOrderResponse]
