from datetime import datetime

from pydantic import BaseModel


class ArchiveCreate(BaseModel):
    work_order_id: int
    archive_no: str
    archive_location: str | None = None
    archive_at: datetime
    remark: str | None = None


class ArchiveUpdate(BaseModel):
    archive_no: str | None = None
    archive_location: str | None = None
    archive_at: datetime | None = None
    remark: str | None = None


class ArchiveResponse(BaseModel):
    id: int
    work_order_id: int
    archived_by: int
    archive_no: str
    archive_location: str | None
    archive_at: datetime
    remark: str | None


class ArchiveListResponse(BaseModel):
    items: list[ArchiveResponse]
