from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.contract import Contract
from app.models.print_room_record import PrintRoomRecord
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.print_room import (
    IssueOfficialContractRequest,
    IssuePaperReportRequest,
    PrintRoomInfoResponse,
    PrintRoomRecordResponse,
    PrintRoomRollbackRequest,
    TransferPrintRoomRequest,
)
from app.services.workflow_log_service import create_workflow_log
from app.workflows.states import WorkOrderStatus
from app.workflows.transitions import can_transit

router = APIRouter(prefix="/print-room", tags=["文印室"])


def _ensure_project_operator(db: Session, work_order: WorkOrder, user_id: int) -> None:
    if work_order.project_leader_id == user_id or work_order.initiator_user_id == user_id:
        return
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if project and project.project_source == "EXTERNAL":
        raise HTTPException(status_code=403, detail="外部项目仅创建人或负责人可处理该流程")
    is_member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人、创建人或项目组成员可处理该流程")


@router.get("/work-orders/{work_order_id}", response_model=PrintRoomInfoResponse)
def get_print_room_info(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PrintRoomInfoResponse:
    contract = db.query(Contract).filter(Contract.work_order_id == work_order_id).first()
    record = db.query(PrintRoomRecord).filter(PrintRoomRecord.work_order_id == work_order_id).first()
    return PrintRoomInfoResponse(
        work_order_id=work_order_id,
        contract_no=contract.contract_no if contract else None,
        paper_report_no=record.paper_report_no if record else None,
        copy_count=record.copy_count if record else None,
        remark=record.remark if record else None,
    )


@router.post("/transfer-print-room")
def transfer_to_print_room(
    payload: TransferPrintRoomRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("THIRD_REVIEWER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.third_reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅该项目三审老师可转发文印室")
    if WorkOrderStatus(work_order.current_status) != WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM:
        raise HTTPException(status_code=400, detail="当前状态不可转发文印室")
    if not work_order.signer_one or not work_order.signer_two or not work_order.formal_report_count:
        raise HTTPException(status_code=400, detail="请填写签字评估师和报告出具数量")
    handler = db.query(User).filter(User.id == payload.handler_user_id, User.is_active.is_(True)).first()
    if not handler or not any(item.role.code == "PRINT_ROOM" for item in handler.roles):
        raise HTTPException(status_code=400, detail="请选择有效的文印室人员")

    from_status = WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM
    to_status = WorkOrderStatus.PRINTROOM_PROCESSING
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")
    work_order.current_status = to_status.value
    work_order.current_handler_user_id = payload.handler_user_id
    work_order.print_room_handler_id = payload.handler_user_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="TRANSFER_PRINTROOM",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    db.commit()
    return {"message": "已转发文印室"}


@router.post("/rollback-third")
def rollback_to_third(
    payload: PrintRoomRollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PRINT_ROOM", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    from_status = WorkOrderStatus(work_order.current_status)
    to_status = WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM
    if from_status != WorkOrderStatus.PRINTROOM_PROCESSING:
        raise HTTPException(status_code=400, detail="当前状态不可撤回至三审")
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")
    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.third_reviewer_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="ROLLBACK_THIRD",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    db.commit()
    return {"message": "已撤回至三审"}


@router.post("/contract-error")
def mark_contract_error(
    payload: PrintRoomRollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PRINT_ROOM", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    from_status = WorkOrderStatus(work_order.current_status)
    if from_status not in {WorkOrderStatus.PRINTROOM_PROCESSING, WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM}:
        raise HTTPException(status_code=400, detail="当前状态不可退回合同")
    to_status = WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")
    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.project_leader_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="CONTRACT_ERROR",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    db.commit()
    return {"message": "已退回合同重新审核"}


@router.post("/report-error")
def report_error_to_print_room(
    payload: PrintRoomRollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not any(item.role.code == "ADMIN" for item in current_user.roles):
        _ensure_project_operator(db, work_order, current_user.id)
    from_status = WorkOrderStatus(work_order.current_status)
    if from_status not in {WorkOrderStatus.WAIT_INVOICE_INFO, WorkOrderStatus.PAPER_REPORT_ISSUED, WorkOrderStatus.INVOICE_INFO_REJECTED}:
        raise HTTPException(status_code=400, detail="当前状态不可退回文印室")
    to_status = WorkOrderStatus.PRINTROOM_PROCESSING
    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.print_room_handler_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="REPORT_ERROR",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    db.commit()
    return {"message": "已退回文印室"}


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

    contract = db.query(Contract).filter(Contract.work_order_id == work_order.id).first()
    if not contract:
        contract = Contract(work_order_id=work_order.id)
        db.add(contract)

    contract.contract_no = payload.contract_no
    contract.status = "OFFICIAL_ISSUED"
    contract.issued_by = current_user.id
    contract.issued_at = datetime.now(timezone.utc)

    from_status = WorkOrderStatus(work_order.current_status)
    if from_status not in {WorkOrderStatus.PRINTROOM_PROCESSING, WorkOrderStatus.PAPER_REPORT_ISSUED, WorkOrderStatus.WAIT_INVOICE_INFO}:
        raise HTTPException(status_code=400, detail="当前状态不可填写正式合同编号")

    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=from_status.value,
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

    work_order.current_status = WorkOrderStatus.WAIT_INVOICE_INFO.value
    work_order.current_handler_user_id = work_order.project_leader_id

    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=WorkOrderStatus.WAIT_INVOICE_INFO.value,
        action_type="ISSUE_PAPER_REPORT",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )

    db.commit()
    db.refresh(row)
    return PrintRoomRecordResponse.model_validate(row, from_attributes=True)
