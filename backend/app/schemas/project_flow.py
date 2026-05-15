from pydantic import BaseModel

from app.schemas.contract_review import ContractReviewRecordResponse


class ProjectFlowProject(BaseModel):
    id: int
    project_no: str
    project_name: str
    client_name: str
    undertaking_unit: str
    evaluation_business_nature: str | None = None
    report_type: str | None = None
    valuation_base_date: str | None = None
    business_salesman: str | None = None
    project_amount: float | None = None
    invoiced_amount: float = 0
    project_source: str = "INTERNAL"
    project_source_display: str = "评估一部"
    external_project_leader_name: str | None = None
    project_leader_display_name: str | None = None
    display_project_leader_name: str | None = None
    contract_no: str | None = None
    report_no: str | None = None
    first_reviewer_name: str | None = None
    second_reviewer_name: str | None = None
    third_reviewer_name: str | None = None
    print_room_handler_name: str | None = None
    mailing_handler_name: str | None = None
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
    mailing_handler_user_id: int | None = None
    archive_reviewer_id: int | None = None
    archive_submitter_id: int | None = None
    archive_submission_type: str | None = None
    mailing_status: str | None = None
    signoff_status: str | None = None
    chief_appraiser_user_id: int | None = None
    user_role_in_project: str
    available_action: str
    can_operate: bool
    flow_steps: list[str]
    contract_review_records: list[ContractReviewRecordResponse] = []
    project_update_logs: list[ProjectUpdateLogItem] = []
    review_submit_locked: bool = False
    review_submit_lock_reason: str | None = None
    duplicate_delete_required: bool = False
    can_remind_current_handler: bool = False
    reminder_summary: dict[str, str | int | bool | None] | None = None
