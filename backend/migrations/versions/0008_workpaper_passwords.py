"""Preserve optional archive passwords per submission."""
from alembic import op
import sqlalchemy as sa
revision = '0008_workpaper_passwords'
down_revision = '0007_operation_workpapers'
branch_labels = None
depends_on = None
def upgrade():
    if 'archive_passwords' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('operation_workpaper_submissions')}:
        op.add_column('operation_workpaper_submissions', sa.Column('archive_passwords', sa.JSON(), nullable=True))
def downgrade():
    raise RuntimeError('Preserve submission passwords; restore a verified backup instead')
