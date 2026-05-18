from pydantic import BaseModel


class WorkbenchProjectItem(BaseModel):
    id: int
    project_no: str
    project_name: str
    client_name: str
    my_project_role: str | None = None
    project_leader_name: str | None = None
    transfer_user_name: str | None = None
    current_step: str
    status_display: str
    todo_action: str | None = None
    termination_status: str | None = None
    termination_reason: str | None = None
    delete_request_status: str | None = None
    delete_request_id: int | None = None
    delete_request_reason: str | None = None
    delete_approver_user_id: int | None = None
    delete_approver_user_name: str | None = None
    delete_requester_user_name: str | None = None
    delete_requested_at: str | None = None
    can_edit: bool
    can_delete: bool
    can_archive: bool
    can_request_termination: bool = False
    can_approve_termination: bool = False
    can_approve_delete: bool = False
    can_enter: bool
    is_reminded: bool = False
    remind_count_today: int = 0
    latest_remind_at: str | None = None


class WorkbenchResponse(BaseModel):
    my_projects: list[WorkbenchProjectItem]
    todo_projects: list[WorkbenchProjectItem]
