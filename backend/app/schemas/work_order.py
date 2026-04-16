from datetime import datetime

from pydantic import BaseModel


class WorkOrderCreate(BaseModel):
    title: str
    description: str = ""


class WorkOrderItem(BaseModel):
    id: int
    title: str
    description: str
    status: str
    created_at: datetime


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderItem]
