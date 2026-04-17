from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    project_code: str = Field(min_length=1, max_length=64)
    project_name: str = Field(min_length=1, max_length=255)
    client_name: str = Field(min_length=1, max_length=255)
    business_user_id: int
    project_leader_id: int
    department_id: int | None = None
    status: str = "ACTIVE"
    description: str | None = None


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    business_user_id: int | None = None
    project_leader_id: int | None = None
    department_id: int | None = None
    status: str | None = None
    description: str | None = None


class ProjectOut(BaseModel):
    id: int
    project_code: str
    project_name: str
    client_name: str
    business_user_id: int
    project_leader_id: int
    department_id: int | None
    status: str
    description: str | None
