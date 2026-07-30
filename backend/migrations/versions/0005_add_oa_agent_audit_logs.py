"""add oa agent audit logs

Revision ID: 0005_add_oa_agent_audit_logs
Revises: 0004_add_org_chief_appraiser_roles
Create Date: 2026-07-30 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_oa_agent_audit_logs"
down_revision = "0004_add_org_chief_appraiser_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oa_agent_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_oa_agent_audit_logs_id"), "oa_agent_audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_oa_agent_audit_logs_project_id"), "oa_agent_audit_logs", ["project_id"], unique=False)
    op.create_index(op.f("ix_oa_agent_audit_logs_session_id"), "oa_agent_audit_logs", ["session_id"], unique=False)
    op.create_index(op.f("ix_oa_agent_audit_logs_user_id"), "oa_agent_audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_oa_agent_audit_logs_user_id"), table_name="oa_agent_audit_logs")
    op.drop_index(op.f("ix_oa_agent_audit_logs_session_id"), table_name="oa_agent_audit_logs")
    op.drop_index(op.f("ix_oa_agent_audit_logs_project_id"), table_name="oa_agent_audit_logs")
    op.drop_index(op.f("ix_oa_agent_audit_logs_id"), table_name="oa_agent_audit_logs")
    op.drop_table("oa_agent_audit_logs")
