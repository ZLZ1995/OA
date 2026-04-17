from datetime import date

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    project_code: str = Field(min_length=1, max_length=64)
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
    pass


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


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
