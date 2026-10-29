"""Add independent workpaper review and immutable workflow classification.

Classification is applied by the validated external manifest during startup.
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_operation_workpapers"
down_revision = "0006_project_handovers"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workflow_version" not in {c["name"] for c in inspector.get_columns("projects")}:
        op.add_column("projects", sa.Column("workflow_version", sa.String(32), nullable=True))
    if "operation_workpaper_reviewer_id" not in {c["name"] for c in inspector.get_columns("work_orders")}:
        op.add_column("work_orders", sa.Column("operation_workpaper_reviewer_id", sa.Integer(), nullable=True))
    metadata = sa.MetaData()
    for name in ("work_orders", "users", "work_order_files"):
        sa.Table(name, metadata, sa.Column("id", sa.Integer, primary_key=True))
    reviews = sa.Table("operation_workpaper_reviews", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("work_order_id", sa.Integer, sa.ForeignKey("work_orders.id"), unique=True, nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("current_submission_id", sa.Integer), sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    submissions = sa.Table("operation_workpaper_submissions", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("review_id", sa.Integer, sa.ForeignKey("operation_workpaper_reviews.id"), nullable=False),
        sa.Column("round_no", sa.Integer, nullable=False), sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("submitter_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("material_type", sa.String(16), nullable=False),
        sa.Column("cloud_url", sa.Text), sa.Column("cloud_code", sa.String(255)),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_entered_at", sa.DateTime(timezone=True)),
        sa.Column("entered_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)), sa.Column("decision_reason", sa.Text),
        sa.UniqueConstraint("review_id", "round_no"), sa.UniqueConstraint("review_id", "request_id"))
    files = sa.Table("operation_workpaper_submission_files", metadata,
        sa.Column("submission_id", sa.Integer, sa.ForeignKey("operation_workpaper_submissions.id"), primary_key=True),
        sa.Column("file_id", sa.Integer, sa.ForeignKey("work_order_files.id"), primary_key=True))
    for table in (reviews, submissions, files):
        table.create(bind, checkfirst=True)


def downgrade():
    raise RuntimeError("Preserve workpaper history; restore a verified backup for rollback instead of dropping review data")
