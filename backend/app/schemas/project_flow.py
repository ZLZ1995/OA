from pydantic import BaseModel


class ProjectFlowProject(BaseModel):
    id: int
    project_no: str
    project_name: str
    client_name: str
    undertaking_unit: str
    current_step: str
    status_display: str


class ProjectFlowResponse(BaseModel):
    project: ProjectFlowProject
    current_work_order_id: int | None = None
    user_role_in_project: str
    available_action: str
    can_operate: bool
    flow_steps: list[str]
