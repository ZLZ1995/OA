from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.invoice import InvoiceCreate, InvoiceListResponse, InvoiceResponse, InvoiceUpdate

router = APIRouter(prefix="/finance", tags=["财务"])


@router.get("/invoices", response_model=InvoiceListResponse)
def list_invoices(
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("FINANCE", "ADMIN")),
) -> InvoiceListResponse:
    rows = db.query(Invoice).order_by(Invoice.id.desc()).all()
    return InvoiceListResponse(items=[InvoiceResponse.model_validate(item, from_attributes=True) for item in rows])


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("FINANCE", "ADMIN")),
) -> InvoiceResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    exists = db.query(Invoice).filter(Invoice.invoice_no == payload.invoice_no).first()
    if exists:
        raise HTTPException(status_code=400, detail="发票号已存在")

    row = Invoice(**payload.model_dump(), handled_by=current_user.id)
    db.add(row)
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
