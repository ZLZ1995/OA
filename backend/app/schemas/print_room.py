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
    current_status: str | None = None
    current_status_display: str | None = None
    print_room_status: str | None = None
    print_room_status_display: str | None = None
    contract_no: str | None = None
    paper_report_no: str | None = None
    copy_count: int | None = None
    formal_report_count: int | None = None
    remark: str | None = None


class PrintRoomContractParticipant(BaseModel):
    user_id: int | None = None
    user_name: str | None = None


class PrintRoomContractFileResponse(BaseModel):
    id: int
    origin_file_name: str
    file_size: int | None = None
    uploaded_at: datetime | None = None
    uploaded_by_user_id: int | None = None
    uploaded_by_user_name: str | None = None
    is_current: bool = True


class ContractPrintRoomInfoResponse(BaseModel):
    work_order_id: int
    current_status: str | None = None
    current_status_display: str | None = None
    project_leader: PrintRoomContractParticipant
    contract_reviewer: PrintRoomContractParticipant
    print_room_handler: PrintRoomContractParticipant
    original_contract_files: list[PrintRoomContractFileResponse] = []
    stamped_contract_scan_files: list[PrintRoomContractFileResponse] = []
    can_upload_scan: bool = False
    can_send_to_project_leader: bool = False
    can_return_to_print_room: bool = False
    can_confirm_complete: bool = False


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
