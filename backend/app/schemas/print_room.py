from datetime import datetime

from pydantic import BaseModel


class IssueOfficialContractRequest(BaseModel):
    work_order_id: int
    contract_no: str
    remark: str | None = None


class IssuePaperReportRequest(BaseModel):
    work_order_id: int
    paper_report_no: str
    copy_count: int = 1
    remark: str | None = None


class PrintRoomInfoResponse(BaseModel):
    work_order_id: int
    contract_no: str | None = None
    paper_report_no: str | None = None
    copy_count: int | None = None
    formal_report_count: int | None = None
    remark: str | None = None


class PrintRoomRollbackRequest(BaseModel):
    work_order_id: int
    remark: str | None = None


class TransferPrintRoomRequest(BaseModel):
    work_order_id: int
    handler_user_id: int
    remark: str | None = None


class PrintRoomRecordResponse(BaseModel):
    id: int
    work_order_id: int
    handled_by: int
    paper_report_no: str
    copy_count: int
    printed_at: datetime | None
    remark: str | None
