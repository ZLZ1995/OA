from pydantic import BaseModel


class WorkbenchProjectItem(BaseModel):
    id: int
    project_no: str
    project_name: str
    client_name: str
    current_step: str
    status_display: str
    todo_action: str | None = None
    can_edit: bool
    can_delete: bool
    can_archive: bool
    can_enter: bool


class WorkbenchResponse(BaseModel):
    my_projects: list[WorkbenchProjectItem]
    todo_projects: list[WorkbenchProjectItem]
