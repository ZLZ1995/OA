"""add reminder tables

Revision ID: 0002_add_reminder_tables
Revises: 0001_initial_schema
Create Date: 2026-05-14 00:00:00
"""

from alembic import op

from app import models  # noqa: F401
from app.db.base import Base

revision = "0002_add_reminder_tables"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in ("user_notifications", "reminder_receipts", "reminder_events"):
        table = Base.metadata.tables.get(table_name)
        if table is not None:
            table.drop(bind=bind, checkfirst=True)
