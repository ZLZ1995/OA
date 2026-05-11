from datetime import datetime

from pydantic import BaseModel, Field


class WorkOrderBase(BaseModel):
    project_id: int
    work_order_no: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=255)
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
    signer_one: str | None = Field(default=None, max_length=64)
    signer_two: str | None = Field(default=None, max_length=64)
    formal_report_count: int | None = Field(default=None, ge=1)
    print_room_handler_id: int | None = None
    archive_reviewer_id: int | None = None
    archive_submitter_id: int | None = None
    archive_submission_type: str | None = None


class WorkOrderResponse(WorkOrderBase):
    id: int
    current_status: str
    current_handler_user_id: int | None
    initiator_user_id: int
    project_leader_id: int
    signer_one: str | None = None
    signer_two: str | None = None
    formal_report_count: int | None = None
    print_room_handler_id: int | None = None
    archive_reviewer_id: int | None = None
    archive_submitter_id: int | None = None
    archive_submission_type: str | None = None


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
