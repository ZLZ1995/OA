from datetime import datetime

from pydantic import BaseModel


class InvoiceCreate(BaseModel):
    work_order_id: int
    invoice_no: str
    amount: float
    issued_at: datetime | None = None
    status: str = "PENDING"


class InvoiceUpdate(BaseModel):
    invoice_no: str | None = None
    amount: float | None = None
    issued_at: datetime | None = None
    status: str | None = None


class InvoiceResponse(BaseModel):
    id: int
    work_order_id: int
    invoice_no: str
    amount: float
    issued_at: datetime | None
    status: str
    handled_by: int | None


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
