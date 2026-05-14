from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserNotification(Base, TimestampMixin):
    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    biz_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    biz_id: Mapped[int] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="SYSTEM", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    sender_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    work_order_id: Mapped[int | None] = mapped_column(ForeignKey("work_orders.id"), nullable=True, index=True)
    process_status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    cc_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    group_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    link_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    link_target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    popup_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
