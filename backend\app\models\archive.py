from sqlalchemy import String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Archive(Base, TimestampMixin):
    __tablename__ = "archives"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), unique=True, nullable=False)
    archived_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    archive_no: Mapped[str] = mapped_column(String(128), nullable=False)
    archive_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archive_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
