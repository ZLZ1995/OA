from datetime import datetime

from pydantic import BaseModel


class ProjectMemberCreate(BaseModel):
    project_id: int
    user_id: int
    member_role: str = "MEMBER"


class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    member_role: str
    created_at: datetime


class ProjectMemberListResponse(BaseModel):
    items: list[ProjectMemberResponse]
