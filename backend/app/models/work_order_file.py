from sqlalchemy import String, ForeignKey, Boolean, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkOrderFile(Base):
    __tablename__ = "work_order_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)
    file_category: Mapped[str] = mapped_column(String(32), nullable=False)
    business_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    origin_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
