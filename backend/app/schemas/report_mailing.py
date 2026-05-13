from datetime import datetime

from pydantic import BaseModel, Field


class ReportMailingSubmitRequest(BaseModel):
    receiver_name: str = Field(min_length=1, max_length=128)
    receiver_phone: str = Field(min_length=1, max_length=64)
    receiver_address: str = Field(min_length=1, max_length=1000)
    receiver_remark: str | None = Field(default=None, max_length=2000)


class ReportMailingExpressRequest(BaseModel):
    express_no: str = Field(min_length=1, max_length=128)


class ReportMailingDecisionRequest(BaseModel):
    remark: str | None = Field(default=None, max_length=2000)


class ReportMailingRecordResponse(BaseModel):
    id: int
    work_order_id: int
    project_id: int
    action_type: str
    operator_user_id: int
    operator_user_name: str | None = None
    receiver_name: str | None = None
    receiver_phone: str | None = None
    receiver_address: str | None = None
    receiver_remark: str | None = None
    express_no: str | None = None
    status: str
    invalidated_express_no: str | None = None
    created_at: datetime


class ReportMailingRecordListResponse(BaseModel):
    items: list[ReportMailingRecordResponse]
