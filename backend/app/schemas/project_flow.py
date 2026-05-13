from pydantic import BaseModel

from app.schemas.contract_review import ContractReviewRecordResponse


class ProjectFlowProject(BaseModel):
    id: int
    project_no: str
    project_name: str
    client_name: str
    undertaking_unit: str
    report_type: str | None = None
    valuation_base_date: str | None = None
    business_salesman: str | None = None
    project_amount: float | None = None
    project_source: str = "INTERNAL"
    project_source_display: str = "内部项目"
    external_project_leader_name: str | None = None
    project_leader_display_name: str | None = None
    contract_no: str | None = None
    report_no: str | None = None
    first_reviewer_name: str | None = None
    second_reviewer_name: str | None = None
    third_reviewer_name: str | None = None
    print_room_handler_name: str | None = None
    invoice_handler_name: str | None = None
    archive_reviewer_name: str | None = None
    current_step: str
    status_display: str


class ProjectUpdateLogItem(BaseModel):
    id: int
    operator_user_id: int
    operator_user_name: str | None = None
    changed_fields: str
    created_at: str


class ProjectFlowResponse(BaseModel):
    project: ProjectFlowProject
    current_work_order_id: int | None = None
    current_work_order_status: str | None = None
    current_handler_user_id: int | None = None
    contract_reviewer_id: int | None = None
    contract_reviewer_name: str | None = None
    contract_review_status: str | None = None
    contract_review_status_display: str | None = None
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
    contract_review_records: list[ContractReviewRecordResponse] = []
    project_update_logs: list[ProjectUpdateLogItem] = []
