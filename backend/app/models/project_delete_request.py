from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ProjectDeleteRequest(Base, TimestampMixin):
    __tablename__ = "project_delete_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, unique=True)
    project_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    project_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    client_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    requester_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approver_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
