from datetime import datetime

from pydantic import BaseModel, Field


class WorkOrderBase(BaseModel):
    work_order_no: str = Field(min_length=1, max_length=64)
    project_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field(default="MEDIUM", max_length=16)
    deadline_at: datetime | None = None


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: str | None = Field(default=None, max_length=16)
    deadline_at: datetime | None = None
    current_handler_user_id: int | None = None


class WorkOrderResponse(WorkOrderBase):
    id: int
    current_status: str
    current_handler_user_id: int | None
    initiator_user_id: int
    project_leader_id: int


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
