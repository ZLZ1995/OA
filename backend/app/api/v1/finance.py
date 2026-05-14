from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.schemas.invoice import InvoiceCreate, InvoiceListResponse, InvoiceResponse, InvoiceUpdate
from app.services.workflow_log_service import create_workflow_log

router = APIRouter(prefix="/finance", tags=["财务"])

ACTIVE_INVOICE_STATUSES = {"SUBMITTED", "FINANCE_COMPLETED", "PROJECT_RETURNED"}
COUNTED_INVOICE_STATUSES = {"SUBMITTED", "FINANCE_COMPLETED", "PROJECT_RETURNED", "ISSUED"}


def _user_has_role(user: User, role_code: str) -> bool:
    return any(item.role.code == role_code for item in user.roles)


def _assert_project_party(db: Session, work_order: WorkOrder, current_user: User, role_codes: set[str]) -> None:
    is_member = db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == current_user.id,
    ).first()
    if "ADMIN" not in role_codes and current_user.id != work_order.project_leader_id and not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可办理开票")


def _assert_finance_handler(db: Session, handler_id: int | None) -> User:
    if not handler_id:
        raise HTTPException(status_code=400, detail="请选择办理开票业务的财务人员")
    handler = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(User.id == handler_id, User.is_active.is_(True), Role.code == "FINANCE")
        .first()
    )
    if not handler:
        raise HTTPException(status_code=400, detail="请选择有效的财务人员")
    return handler


def _assert_assigned_finance(row: Invoice, current_user: User) -> None:
    if _user_has_role(current_user, "ADMIN"):
        return
    if row.finance_handler_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅指定财务人员可处理该开票业务")


def _latest_invoice(db: Session, work_order_id: int) -> Invoice | None:
    return db.query(Invoice).filter(Invoice.work_order_id == work_order_id).order_by(Invoice.id.desc()).first()


def calculate_project_invoice_total(db: Session, project_id: int) -> float:
    rows = (
        db.query(Invoice)
        .join(WorkOrder, WorkOrder.id == Invoice.work_order_id)
        .filter(WorkOrder.project_id == project_id, Invoice.status.in_(COUNTED_INVOICE_STATUSES))
        .all()
    )
    return sum(float(row.amount or 0) for row in rows)


def _log_invoice_action(
    db: Session,
    work_order: WorkOrder,
    action_type: str,
    operator_user_id: int,
    remark: str | None = None,
) -> None:
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=work_order.current_status,
        to_status=work_order.current_status,
        action_type=action_type,
        operator_user_id=operator_user_id,
        remark=remark,
    )


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
    _assert_project_party(db, work_order, current_user, role_codes)
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.project_amount is None:
        raise HTTPException(status_code=400, detail="请先在项目基本信息模块中录入项目金额")

    if not payload.invoice_info or not payload.invoice_type:
        raise HTTPException(status_code=400, detail="请填写开票信息和发票类型")
    _assert_finance_handler(db, payload.finance_handler_id)

    row = _latest_invoice(db, payload.work_order_id)
    if row and row.status in ACTIVE_INVOICE_STATUSES:
        raise HTTPException(status_code=400, detail="已有未完成的开票业务，请完成后再提交新申请")

    if calculate_project_invoice_total(db, work_order.project_id) + float(payload.amount or 0) > float(project.project_amount):
        raise HTTPException(status_code=400, detail="累计开票金额已超过项目金额，请核对后再提交")

    data = payload.model_dump()
    data["invoice_no"] = payload.invoice_no or f"PENDING-{payload.work_order_id}"
    if row and row.status == "REJECTED":
        for key, value in data.items():
            setattr(row, key, value)
    else:
        row = Invoice(**data)
        db.add(row)

    row.status = "SUBMITTED"
    row.handled_by = None
    row.finance_handler_id = payload.finance_handler_id
    _log_invoice_action(db, work_order, "SUBMIT_INVOICE_INFO", current_user.id, payload.invoice_info)
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
    _assert_assigned_finance(row, current_user)

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
    _assert_assigned_finance(row, current_user)
    if row.status not in {"SUBMITTED", "PROJECT_RETURNED"}:
        raise HTTPException(status_code=400, detail="当前开票业务不可退回开票信息")
    row.status = "REJECTED"
    row.handled_by = current_user.id
    _log_invoice_action(db, work_order, "REJECT_INVOICE_INFO", current_user.id, payload.status)
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
    _assert_assigned_finance(row, current_user)
    if row.status not in {"SUBMITTED", "PROJECT_RETURNED"}:
        raise HTTPException(status_code=400, detail="当前开票业务不可完成")
    row.status = "FINANCE_COMPLETED"
    row.handled_by = current_user.id
    row.issued_at = datetime.now(timezone.utc)
    _log_invoice_action(db, work_order, "FINANCE_COMPLETE_INVOICE", current_user.id)
    db.commit()
    db.refresh(row)
    return InvoiceResponse.model_validate(row, from_attributes=True)


@router.post("/invoices/{invoice_id}/confirm", response_model=InvoiceResponse)
def confirm_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> InvoiceResponse:
    row = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="发票不存在")
    work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _assert_project_party(db, work_order, current_user, role_codes)
    if row.status != "FINANCE_COMPLETED":
        raise HTTPException(status_code=400, detail="当前开票业务尚未进入项目方确认")
    row.status = "ISSUED"
    _log_invoice_action(db, work_order, "PROJECT_CONFIRM_INVOICE", current_user.id)
    db.commit()
    db.refresh(row)
    return InvoiceResponse.model_validate(row, from_attributes=True)


@router.post("/invoices/{invoice_id}/return", response_model=InvoiceResponse)
def return_invoice_to_finance(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> InvoiceResponse:
    row = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="发票不存在")
    work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _assert_project_party(db, work_order, current_user, role_codes)
    if row.status != "FINANCE_COMPLETED":
        raise HTTPException(status_code=400, detail="当前开票业务不可退回财务修改")
    row.status = "PROJECT_RETURNED"
    _log_invoice_action(db, work_order, "PROJECT_RETURN_INVOICE", current_user.id, payload.status)
    db.commit()
    db.refresh(row)
    return InvoiceResponse.model_validate(row, from_attributes=True)


@router.post("/invoices/{invoice_id}/withdraw", response_model=InvoiceResponse)
def withdraw_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> InvoiceResponse:
    row = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="发票不存在")
    work_order = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _assert_project_party(db, work_order, current_user, role_codes)
    if row.status != "SUBMITTED" or row.handled_by is not None:
        raise HTTPException(status_code=400, detail="财务已处理，不能撤回开票信息")
    row.status = "REJECTED"
    _log_invoice_action(db, work_order, "WITHDRAW_INVOICE_INFO", current_user.id)
    db.commit()
    db.refresh(row)
    return InvoiceResponse.model_validate(row, from_attributes=True)
