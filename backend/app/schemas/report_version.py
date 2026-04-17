from datetime import datetime

from pydantic import BaseModel


class ReportVersionCreate(BaseModel):
    work_order_id: int
    file_id: int
    submit_stage: str


class ReportVersionResponse(BaseModel):
    id: int
    work_order_id: int
    version_no: int
    file_id: int
    submitted_by: int
    submit_stage: str
    created_at: datetime


class ReportVersionListResponse(BaseModel):
    items: list[ReportVersionResponse]
