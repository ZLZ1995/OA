from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class IssueFeedback(Base, TimestampMixin):
    __tablename__ = "issue_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    submitter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    project_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    process_step: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspend_note: Mapped[str | None] = mapped_column(Text, nullable=True)
