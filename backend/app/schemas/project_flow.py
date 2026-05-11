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
    current_work_order_status: str | None = None
    current_handler_user_id: int | None = None
    first_reviewer_id: int | None = None
    second_reviewer_id: int | None = None
    third_reviewer_id: int | None = None
    signer_one: str | None = None
    signer_two: str | None = None
    formal_report_count: int | None = None
    print_room_handler_id: int | None = None
    archive_reviewer_id: int | None = None
    archive_submitter_id: int | None = None
    archive_submission_type: str | None = None
    user_role_in_project: str
    available_action: str
    can_operate: bool
    flow_steps: list[str]
