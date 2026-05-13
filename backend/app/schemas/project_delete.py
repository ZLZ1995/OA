from datetime import datetime

from pydantic import BaseModel, Field


class ProjectDeleteRequestCreate(BaseModel):
    approver_user_id: int
    reason: str | None = Field(default=None, max_length=2000)


class ProjectDeleteRequestResponse(BaseModel):
    id: int
    project_id: int | None = None
    project_no: str
    project_name: str
    client_name: str
    current_step: str
    requester_user_id: int
    requester_user_name: str | None = None
    approver_user_id: int
    approver_user_name: str | None = None
    reason: str | None = None
    status: str
    requested_at: datetime
    reviewed_at: datetime | None = None


class ProjectDeleteRequestListResponse(BaseModel):
    items: list[ProjectDeleteRequestResponse]
