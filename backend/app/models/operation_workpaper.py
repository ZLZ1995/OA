"""Independent operational workpaper review; never reuse final archive state."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OperationWorkpaperReview(Base, TimestampMixin):
    __tablename__ = "operation_workpaper_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    current_submission_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OperationWorkpaperSubmission(Base):
    __tablename__ = "operation_workpaper_submissions"
    __table_args__ = (
        UniqueConstraint("review_id", "round_no"),
        UniqueConstraint("review_id", "request_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("operation_workpaper_reviews.id"), nullable=False)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    material_type: Mapped[str] = mapped_column(String(16), nullable=False)
    cloud_url: Mapped[str | None] = mapped_column(Text)
    cloud_code: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), default="SUBMITTED", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)


class OperationWorkpaperSubmissionFile(Base):
    __tablename__ = "operation_workpaper_submission_files"
    submission_id: Mapped[int] = mapped_column(ForeignKey("operation_workpaper_submissions.id"), primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("work_order_files.id"), primary_key=True)
