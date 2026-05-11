from sqlalchemy import String, ForeignKey, Date, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    undertaking_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="中勤")
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    project_leader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    start_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    termination_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    termination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    termination_requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    termination_requested_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    termination_approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    termination_approved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
