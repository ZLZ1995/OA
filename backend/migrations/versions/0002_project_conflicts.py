"""project conflict alerts

Revision ID: 0002_project_conflicts
Revises: 0001_initial_schema
Create Date: 2026-05-14 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_project_conflicts"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    if "duplicate_delete_required" not in project_columns:
        op.add_column("projects", sa.Column("duplicate_delete_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "duplicate_delete_reason" not in project_columns:
        op.add_column("projects", sa.Column("duplicate_delete_reason", sa.Text(), nullable=True))

    if "project_conflict_snapshots" not in inspector.get_table_names():
        op.create_table(
            "project_conflict_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, unique=True),
            sa.Column("work_order_id", sa.Integer(), nullable=False),
            sa.Column("project_no", sa.String(length=64), nullable=False),
            sa.Column("project_name", sa.String(length=255), nullable=False),
            sa.Column("client_name", sa.String(length=255), nullable=False),
            sa.Column("normalized_client_name", sa.String(length=255), nullable=False),
            sa.Column("project_amount", sa.Float(), nullable=False),
            sa.Column("valuation_base_date", sa.Date(), nullable=False),
            sa.Column("project_leader_display_name", sa.String(length=255), nullable=False),
            sa.Column("creator_user_id", sa.Integer(), nullable=True),
            sa.Column("creator_username", sa.String(length=255), nullable=True),
            sa.Column("contract_uploaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if "project_conflict_records" not in inspector.get_table_names():
        op.create_table(
            "project_conflict_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_a_id", sa.Integer(), nullable=False),
            sa.Column("project_b_id", sa.Integer(), nullable=False),
            sa.Column("snapshot_a_id", sa.Integer(), nullable=False),
            sa.Column("snapshot_b_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
            sa.Column("decision", sa.String(length=32), nullable=True),
            sa.Column("kept_project_id", sa.Integer(), nullable=True),
            sa.Column("delete_project_id", sa.Integer(), nullable=True),
            sa.Column("decided_by", sa.Integer(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolve_comment", sa.Text(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("project_conflict_records")
    op.drop_table("project_conflict_snapshots")
    op.drop_column("projects", "duplicate_delete_reason")
    op.drop_column("projects", "duplicate_delete_required")
