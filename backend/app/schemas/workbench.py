from pydantic import BaseModel


class WorkbenchProjectItem(BaseModel):
    id: int
    project_no: str
    project_name: str
    client_name: str
    project_leader_name: str | None = None
    transfer_user_name: str | None = None
    current_step: str
    status_display: str
    todo_action: str | None = None
    termination_status: str | None = None
    termination_reason: str | None = None
    can_edit: bool
    can_delete: bool
    can_archive: bool
    can_request_termination: bool = False
    can_approve_termination: bool = False
    can_enter: bool


class WorkbenchResponse(BaseModel):
    my_projects: list[WorkbenchProjectItem]
    todo_projects: list[WorkbenchProjectItem]
