from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ProjectUpdateLog(Base, TimestampMixin):
    __tablename__ = "project_update_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_fields: Mapped[str] = mapped_column(Text, nullable=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
