from datetime import datetime

from pydantic import BaseModel


class ContractReviewFileResponse(BaseModel):
    id: int
    origin_file_name: str
    file_size: int | None = None
    uploaded_at: datetime | None = None


class ContractReviewSubmitRequest(BaseModel):
    work_order_id: int
    reviewer_user_id: int
    comment: str | None = None


class ContractReviewDecisionRequest(BaseModel):
    comment: str | None = None
    review_attachment_file_id: int | None = None


class ContractReviewRecordResponse(BaseModel):
    id: int
    work_order_id: int
    project_id: int
    action_type: str
    operator_user_id: int
    operator_user_name: str | None = None
    reviewer_user_id: int
    reviewer_user_name: str | None = None
    comment: str | None = None
    contract_file_id: int | None = None
    review_attachment_file_id: int | None = None
    contract_file: ContractReviewFileResponse | None = None
    review_attachment_file: ContractReviewFileResponse | None = None
    created_at: datetime


class ContractReviewRecordListResponse(BaseModel):
    items: list[ContractReviewRecordResponse]
