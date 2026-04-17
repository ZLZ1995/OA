from datetime import datetime

from pydantic import BaseModel


class WorkOrderFileResponse(BaseModel):
    id: int
    work_order_id: int
    file_category: str
    business_stage: str
    version_no: int
    is_current: bool
    origin_file_name: str
    storage_key: str
    uploaded_by: int
    uploaded_at: datetime


class WorkOrderFileListResponse(BaseModel):
    items: list[WorkOrderFileResponse]
