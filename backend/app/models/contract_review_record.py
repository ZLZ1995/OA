from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ContractReviewRecord(Base, TimestampMixin):
    __tablename__ = "contract_review_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reviewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_file_id: Mapped[int | None] = mapped_column(ForeignKey("work_order_files.id"), nullable=True)
    review_attachment_file_id: Mapped[int | None] = mapped_column(ForeignKey("work_order_files.id"), nullable=True)
