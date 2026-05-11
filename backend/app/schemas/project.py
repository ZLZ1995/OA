from datetime import date, datetime

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    project_code: str = Field(min_length=1, max_length=64)
    undertaking_unit: str = Field(min_length=1, max_length=32)
    project_name: str = Field(min_length=1, max_length=255)
    client_name: str = Field(min_length=1, max_length=255)
    business_user_id: int
    project_leader_id: int
    department_id: int | None = None
    start_date: date | None = None
    due_date: date | None = None
    status: str = Field(default="ACTIVE", max_length=32)
    description: str | None = None


class ProjectCreate(ProjectBase):
    project_code: str | None = None


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    business_user_id: int | None = None
    project_leader_id: int | None = None
    department_id: int | None = None
    start_date: date | None = None
    due_date: date | None = None
    status: str | None = Field(default=None, max_length=32)
    description: str | None = None


class ProjectResponse(ProjectBase):
    id: int
    status_display: str = "项目创建"
    termination_status: str | None = None
    termination_reason: str | None = None
    termination_requested_by: int | None = None
    termination_requested_at: datetime | None = None
    termination_approved_by: int | None = None
    termination_approved_at: datetime | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
