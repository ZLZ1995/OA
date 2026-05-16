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
    file_size: int | None = None
    uploaded_by: int
    uploaded_by_name: str | None = None
    uploaded_at: datetime
    source_type: str = "MANUAL"
    source_file_id: int | None = None
    locked: bool = False
    display_label: str | None = None


class WorkOrderFileListResponse(BaseModel):
    items: list[WorkOrderFileResponse]
