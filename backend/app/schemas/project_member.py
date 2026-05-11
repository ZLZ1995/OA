from datetime import datetime

from pydantic import BaseModel, Field


class ProjectMemberBatchCreate(BaseModel):
    project_id: int
    user_ids: list[int] = Field(min_length=1)
    member_role: str


class ProjectMemberUpdate(BaseModel):
    member_role: str


class ProjectMemberCompleteRequest(BaseModel):
    project_id: int


class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    username: str
    real_name: str
    member_role: str
    created_at: datetime


class ProjectMemberListResponse(BaseModel):
    items: list[ProjectMemberResponse]
