from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ReportMailingRecord(Base, TimestampMixin):
    __tablename__ = "report_mailing_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    receiver_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    receiver_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    receiver_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    receiver_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    express_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    invalidated_express_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
