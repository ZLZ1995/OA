from sqlalchemy import String, ForeignKey, Numeric, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), nullable=False)
    invoice_no: Mapped[str] = mapped_column(String(128), nullable=False)
    invoice_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    issued_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
