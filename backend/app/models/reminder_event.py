from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ReminderEvent(Base, TimestampMixin):
    __tablename__ = "reminder_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), nullable=False, index=True)
    current_handler_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    initiator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    initiator_role_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False, default="MANUAL")
    current_status: Mapped[str] = mapped_column(String(64), nullable=False)
    overdue_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_remind_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    handler_cycle_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
