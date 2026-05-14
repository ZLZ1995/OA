from sqlalchemy import Boolean, ForeignKey, String, Text
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
    link_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    link_target_id: Mapped[int | None] = mapped_column(nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    popup_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
