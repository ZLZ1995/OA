from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.contract import Contract
from app.models.print_room_record import PrintRoomRecord
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.print_room import (
    IssueOfficialContractRequest,
    IssuePaperReportRequest,
    PrintRoomRecordResponse,
)
from app.services.workflow_log_service import create_workflow_log
from app.workflows.states import WorkOrderStatus
from app.workflows.transitions import can_transit

router = APIRouter(prefix="/print-room", tags=["文印室"])


@router.post("/issue-official-contract")
def issue_official_contract(
    payload: IssueOfficialContractRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PRINT_ROOM", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    from_status = WorkOrderStatus(work_order.current_status)
    to_status = WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT
    if from_status != WorkOrderStatus.WAIT_PRINTROOM_OFFICIAL_CONTRACT:
        raise HTTPException(status_code=400, detail="当前状态不可出具正式合同")
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    contract = db.query(Contract).filter(Contract.work_order_id == work_order.id).first()
    if not contract:
        contract = Contract(work_order_id=work_order.id)
        db.add(contract)

    contract.contract_no = payload.contract_no
    contract.status = "OFFICIAL_ISSUED"
    contract.issued_by = current_user.id
    contract.issued_at = datetime.now(timezone.utc)

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.project_leader_id

    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="ISSUE_OFFICIAL_CONTRACT",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )

    db.commit()
    return {"message": "已出具正式合同"}


@router.post("/issue-paper-report", response_model=PrintRoomRecordResponse)
def issue_paper_report(
    payload: IssuePaperReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PRINT_ROOM", "ADMIN")),
) -> PrintRoomRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    from_status = WorkOrderStatus(work_order.current_status)
    if from_status == WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM:
        mid_status = WorkOrderStatus.PRINTROOM_PROCESSING
        if not can_transit(from_status, mid_status):
            raise HTTPException(status_code=400, detail="非法状态迁移")
        create_workflow_log(
            db,
            work_order_id=work_order.id,
            from_status=from_status.value,
            to_status=mid_status.value,
            action_type="PRINTROOM_START",
            operator_user_id=current_user.id,
            remark=payload.remark,
        )
        work_order.current_status = mid_status.value
        from_status = mid_status

    to_status = WorkOrderStatus.PAPER_REPORT_ISSUED
    if from_status != WorkOrderStatus.PRINTROOM_PROCESSING:
        raise HTTPException(status_code=400, detail="当前状态不可出具纸质报告")
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    row = db.query(PrintRoomRecord).filter(PrintRoomRecord.work_order_id == work_order.id).first()
    if not row:
        row = PrintRoomRecord(
            work_order_id=work_order.id,
            handled_by=current_user.id,
            paper_report_no=payload.paper_report_no,
            copy_count=payload.copy_count,
            printed_at=datetime.now(timezone.utc),
            remark=payload.remark,
        )
        db.add(row)
    else:
        row.handled_by = current_user.id
        row.paper_report_no = payload.paper_report_no
        row.copy_count = payload.copy_count
        row.printed_at = datetime.now(timezone.utc)
        row.remark = payload.remark

    work_order.current_status = to_status.value
    work_order.current_handler_user_id = None

    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="ISSUE_PAPER_REPORT",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )

    db.commit()
    db.refresh(row)
    return PrintRoomRecordResponse.model_validate(row, from_attributes=True)
