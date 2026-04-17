from pydantic import BaseModel, Field


class WorkOrderCreate(BaseModel):
    work_order_no: str = Field(min_length=1, max_length=64)
    project_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    current_status: str
    current_handler_user_id: int | None = None
    initiator_user_id: int
    project_leader_id: int


class WorkOrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    current_status: str | None = None
    current_handler_user_id: int | None = None
    first_reviewer_id: int | None = None
    second_reviewer_id: int | None = None
    third_reviewer_id: int | None = None


class WorkOrderOut(BaseModel):
    id: int
    work_order_no: str
    project_id: int
    title: str
    description: str | None
    current_status: str
    current_handler_user_id: int | None
    initiator_user_id: int
    project_leader_id: int
    first_reviewer_id: int | None
    second_reviewer_id: int | None
    third_reviewer_id: int | None
