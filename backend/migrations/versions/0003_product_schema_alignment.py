"""product schema alignment

Revision ID: 0003_product_schema_alignment
Revises: 0002_add_reminder_tables, 0002_project_conflicts
Create Date: 2026-05-16 00:00:00
"""

from alembic import op
import sqlalchemy as sa

from app import models  # noqa: F401
from app.db.base import Base

revision = "0003_product_schema_alignment"
down_revision = ("0002_add_reminder_tables", "0002_project_conflicts")
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    if table_name not in _table_names(inspector):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(inspector: sa.Inspector, table_name: str, column: sa.Column) -> None:
    if table_name not in _table_names(inspector):
        return
    if column.name not in _columns(inspector, table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    Base.metadata.create_all(bind=bind)

    _add_column_if_missing(inspector, "projects", sa.Column("undertaking_unit", sa.String(length=32), nullable=False, server_default="中勤"))
    _add_column_if_missing(inspector, "projects", sa.Column("evaluation_business_nature", sa.String(length=64), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("report_type", sa.String(length=32), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("valuation_base_date", sa.Date(), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("business_salesman", sa.String(length=255), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("project_amount", sa.Float(), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("project_source", sa.String(length=16), nullable=False, server_default="INTERNAL"))
    _add_column_if_missing(inspector, "projects", sa.Column("external_project_leader_name", sa.String(length=255), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("termination_status", sa.String(length=32), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("termination_reason", sa.Text(), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("termination_requested_by", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("termination_requested_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("termination_approved_by", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("termination_approved_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(inspector, "projects", sa.Column("duplicate_delete_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing(inspector, "projects", sa.Column("duplicate_delete_reason", sa.Text(), nullable=True))

    _add_column_if_missing(inspector, "work_orders", sa.Column("contract_reviewer_id", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("signer_one", sa.String(length=64), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("signer_two", sa.String(length=64), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("formal_report_count", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("print_room_handler_id", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("mailing_handler_user_id", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("archive_reviewer_id", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("archive_submitter_id", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("archive_submission_type", sa.String(length=16), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("mailing_status", sa.String(length=32), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("signoff_status", sa.String(length=32), nullable=True))
    _add_column_if_missing(inspector, "work_orders", sa.Column("chief_appraiser_user_id", sa.Integer(), nullable=True))

    _add_column_if_missing(inspector, "work_order_files", sa.Column("file_size", sa.Integer(), nullable=True))
    _add_column_if_missing(inspector, "invoices", sa.Column("invoice_info", sa.Text(), nullable=True))
    _add_column_if_missing(inspector, "invoices", sa.Column("invoice_type", sa.String(length=16), nullable=True))
    _add_column_if_missing(inspector, "invoices", sa.Column("finance_handler_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    pass
