from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ProjectHandover(Base, TimestampMixin):
    __tablename__ = "project_handovers"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    work_order_id: Mapped[int | None] = mapped_column(ForeignKey("work_orders.id"))
    duty: Mapped[str] = mapped_column(String(64))
    source_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    custodian_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    held_current_task: Mapped[bool] = mapped_column(default=False)
    custodian_member_created: Mapped[bool] = mapped_column(default=False)
    reason: Mapped[str] = mapped_column(Text)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class ProjectConflictEvaluation(Base, TimestampMixin):
    __tablename__ = "project_conflict_evaluations"
    __table_args__ = (UniqueConstraint("project_a_id", "project_b_id", "fingerprint", name="uq_conflict_evaluation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_a_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    project_b_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    fingerprint: Mapped[str] = mapped_column(String(64))
    evidence: Mapped[str] = mapped_column(Text)
    conflict_id: Mapped[int] = mapped_column(ForeignKey("project_conflict_records.id"), index=True)
