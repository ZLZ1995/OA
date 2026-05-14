from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ReminderReceipt(Base, TimestampMixin):
    __tablename__ = "reminder_receipts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reminder_event_id: Mapped[int] = mapped_column(ForeignKey("reminder_events.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    receiver_type: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="IN_APP")
    delivery_status: Mapped[str] = mapped_column(String(16), nullable=False, default="SENT")
    read_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNREAD")
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
