from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WorkOrder(Base, TimestampMixin):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_status: Mapped[str] = mapped_column(String(64), nullable=False)
    current_handler_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    initiator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    project_leader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    contract_reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    first_reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    second_reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    third_reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    signer_one: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signer_two: Mapped[str | None] = mapped_column(String(64), nullable=True)
    formal_report_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    print_room_handler_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    mailing_handler_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    archive_reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    archive_submitter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    archive_submission_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mailing_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    signoff_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    chief_appraiser_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False)
    deadline_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
