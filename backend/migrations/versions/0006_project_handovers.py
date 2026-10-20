"""Add project custodianship and versioned duplicate decisions."""
from alembic import op
import sqlalchemy as sa

revision = "0006_project_handovers"
down_revision = "0005_add_oa_agent_audit_logs"
branch_labels = None
depends_on = None


def upgrade():
    # checkfirst also supports installations initialized by application create_all.
    metadata = sa.MetaData()
    for name in ("projects", "work_orders", "users", "project_conflict_records"):
        sa.Table(name, metadata, sa.Column("id", sa.Integer, primary_key=True))
    def dates():
        return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
                sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]
    handovers = sa.Table("project_handovers", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("work_order_id", sa.Integer, sa.ForeignKey("work_orders.id")),
        sa.Column("duty", sa.String(64), nullable=False),
        sa.Column("source_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("custodian_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(16), nullable=False, index=True),
        sa.Column("held_current_task", sa.Boolean, nullable=False),
        sa.Column("custodian_member_created", sa.Boolean, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("assigned_by", sa.Integer, sa.ForeignKey("users.id")), *dates())
    evaluations = sa.Table("project_conflict_evaluations", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_a_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("project_b_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("evidence", sa.Text, nullable=False),
        sa.Column("conflict_id", sa.Integer, sa.ForeignKey("project_conflict_records.id"), nullable=False, index=True),
        sa.UniqueConstraint("project_a_id", "project_b_id", "fingerprint", name="uq_conflict_evaluation"), *dates())
    handovers.create(op.get_bind(), checkfirst=True)
    evaluations.create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("project_conflict_evaluations")
    op.drop_table("project_handovers")
