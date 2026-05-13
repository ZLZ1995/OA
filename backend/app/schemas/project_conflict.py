from datetime import datetime

from pydantic import BaseModel, Field


class ProjectConflictSnapshotItem(BaseModel):
    project_id: int
    project_no: str
    project_name: str
    client_name: str
    project_amount: float
    valuation_base_date: str
    project_leader_display_name: str
    creator_username: str | None = None
    contract_uploaded_at: str


class ProjectConflictRecordItem(BaseModel):
    id: int
    status: str
    decision: str | None = None
    kept_project_id: int | None = None
    delete_project_id: int | None = None
    resolve_comment: str | None = None
    created_at: datetime
    decided_at: datetime | None = None
    resolved_at: datetime | None = None
    project_a: ProjectConflictSnapshotItem
    project_b: ProjectConflictSnapshotItem


class ProjectConflictListResponse(BaseModel):
    items: list[ProjectConflictRecordItem]


class ProjectConflictDecisionRequest(BaseModel):
    kept_project_id: int | None = None
    comment: str | None = Field(default=None, max_length=1000)
