from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    contract_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    draft_file_id: Mapped[int | None] = mapped_column(ForeignKey("work_order_files.id"), nullable=True)
    official_file_id: Mapped[int | None] = mapped_column(ForeignKey("work_order_files.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT_UPLOADED", nullable=False)
    issued_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    issued_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
