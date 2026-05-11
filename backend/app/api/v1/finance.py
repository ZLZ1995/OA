from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.invoice import Invoice
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.invoice import InvoiceCreate, InvoiceListResponse, InvoiceResponse, InvoiceUpdate
from app.services.workflow_log_service import create_workflow_log
from app.workflows.states import WorkOrderStatus
from app.workflows.transitions import can_transit

router = APIRouter(prefix="/finance", tags=["财务"])


@router.get("/invoices", response_model=InvoiceListResponse)
def list_invoices(
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("FINANCE", "ADMIN", "PROJECT_LEADER", "PROJECT_MEMBER")),
) -> InvoiceListResponse:
    rows = db.query(Invoice).order_by(Invoice.id.desc()).all()
    return InvoiceListResponse(items=[InvoiceResponse.model_validate(item, from_attributes=True) for item in rows])


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> InvoiceResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    is_member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == current_user.id,
    ).first()
    if "ADMIN" not in role_codes and current_user.id != work_order.project_leader_id and not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可提交开票信息")

    from_status = WorkOrderStatus(work_order.current_status)
    if from_status not in {WorkOrderStatus.WAIT_INVOICE_INFO, WorkOrderStatus.INVOICE_INFO_REJECTED}:
        raise HTTPException(status_code=400, detail="当前流程不可提交开票信息")
    to_status = WorkOrderStatus.INVOICE_PROCESSING
    if not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="非法状态迁移")

    if not payload.invoice_info or not payload.invoice_type:
        raise HTTPException(status_code=400, detail="请填写开票信息和发票类型")

    row = db.query(Invoice).filter(Invoice.work_order_id == payload.work_order_id).order_by(Invoice.id.desc()).first()
    data = payload.model_dump()
    data["invoice_no"] = payload.invoice_no or f"PENDING-{payload.work_order_id}"
    if row:
        for key, value in data.items():
            setattr(row, key, value)
    else:
        row = Invoice(**data)
        db.add(row)
    row.status = "SUBMITTED"
    row.handled_by = None
    work_order.current_status = to_status.value
    work_order.current_handler_user_id = None
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="SUBMIT_INVOICE_INFO",
        operator_user_id=current_user.id,
        remark=payload.invoice_info,
    )
    db.commit()
    db.refresh(row)
    return InvoiceResponse.model_validate(row, from_attributes=True)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("FINANCE", "ADMIN")),
) -> InvoiceResponse:
    row = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="发票不存在")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    row.handled_by = current_user.id
    db.commit()
    db.refresh(row)
    return InvoiceResponse.model_validate(row, from_attributes=True)


@router.post("/invoices/{invoice_id}/reject", response_model=InvoiceResponse)
def reject_invoice_info(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("FINANCE", "ADMIN")),
) -> InvoiceResponse:
    row = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="发票不存在")
    work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    from_status = WorkOrderStatus(work_order.current_status)
    to_status = WorkOrderStatus.INVOICE_INFO_REJECTED
    if from_status != WorkOrderStatus.INVOICE_PROCESSING or not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="当前流程不可退回开票信息")
    row.status = "REJECTED"
    row.handled_by = current_user.id
    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.project_leader_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="REJECT_INVOICE_INFO",
        operator_user_id=current_user.id,
        remark=payload.status,
    )
    db.commit()
    db.refresh(row)
    return InvoiceResponse.model_validate(row, from_attributes=True)


@router.post("/invoices/{invoice_id}/complete", response_model=InvoiceResponse)
def complete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("FINANCE", "ADMIN")),
) -> InvoiceResponse:
    row = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="发票不存在")
    work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    from_status = WorkOrderStatus(work_order.current_status)
    to_status = WorkOrderStatus.WAIT_ARCHIVE_SUBMIT
    if from_status != WorkOrderStatus.INVOICE_PROCESSING or not can_transit(from_status, to_status):
        raise HTTPException(status_code=400, detail="当前流程不可完成开票")
    row.status = "ISSUED"
    row.handled_by = current_user.id
    row.issued_at = datetime.now(timezone.utc)
    work_order.current_status = to_status.value
    work_order.current_handler_user_id = work_order.project_leader_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=to_status.value,
        action_type="COMPLETE_INVOICE",
        operator_user_id=current_user.id,
    )
    db.commit()
    db.refresh(row)
    return InvoiceResponse.model_validate(row, from_attributes=True)
