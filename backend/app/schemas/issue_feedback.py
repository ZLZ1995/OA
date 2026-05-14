from datetime import datetime

from pydantic import BaseModel, Field


class IssueFeedbackCreate(BaseModel):
    project_no: str = Field(min_length=1, max_length=64)
    process_step: str = Field(min_length=1, max_length=64)
    detail: str = Field(min_length=1, max_length=4000)


class IssueFeedbackSuspendRequest(BaseModel):
    suspend_note: str | None = Field(default=None, max_length=1000)


class IssueFeedbackItem(BaseModel):
    id: int
    project_no: str
    process_step: str
    detail: str
    status: str
    submitter_user_id: int
    submitter_user_name: str
    submitter_username: str
    created_at: datetime
    handled_by_name: str | None = None
    handled_at: datetime | None = None
    suspended_by_name: str | None = None
    suspended_at: datetime | None = None
    suspend_note: str | None = None


class IssueFeedbackListResponse(BaseModel):
    items: list[IssueFeedbackItem]
