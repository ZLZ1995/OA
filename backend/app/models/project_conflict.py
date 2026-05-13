from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ProjectConflictSnapshot(Base, TimestampMixin):
    __tablename__ = "project_conflict_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, unique=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), nullable=False)
    project_no: Mapped[str] = mapped_column(String(64), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_amount: Mapped[float] = mapped_column(Float, nullable=False)
    valuation_base_date: Mapped[Date] = mapped_column(Date, nullable=False)
    project_leader_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    creator_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    creator_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectConflictRecord(Base, TimestampMixin):
    __tablename__ = "project_conflict_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_a_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project_b_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    snapshot_a_id: Mapped[int] = mapped_column(ForeignKey("project_conflict_snapshots.id"), nullable=False)
    snapshot_b_id: Mapped[int] = mapped_column(ForeignKey("project_conflict_snapshots.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kept_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    delete_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolve_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
