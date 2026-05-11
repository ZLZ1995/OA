from sqlalchemy import String, ForeignKey, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PrintRoomRecord(Base, TimestampMixin):
    __tablename__ = "print_room_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    handled_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    paper_report_no: Mapped[str] = mapped_column(String(128), nullable=False)
    copy_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    printed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
