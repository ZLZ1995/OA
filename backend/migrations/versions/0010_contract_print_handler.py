"""Store contract printing assignment separately from report printing."""
from alembic import op
import sqlalchemy as sa

revision = "0010_contract_print_handler"
down_revision = "0009_remove_invoice_flow"
branch_labels = None
depends_on = None


def upgrade():
    columns = sa.inspect(op.get_bind()).get_columns("work_orders")
    if not any(column["name"] == "contract_print_handler_id" for column in columns):
        op.add_column("work_orders", sa.Column("contract_print_handler_id", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("work_orders", "contract_print_handler_id")
