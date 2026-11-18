"""Retire invoice workflow and finance role while preserving invoice history."""

from alembic import op
import sqlalchemy as sa

revision = "0009_remove_invoice_flow"
down_revision = "0008_workpaper_passwords"
branch_labels = None
depends_on = None

OLD_STATES = ("WAIT_INVOICE_INFO", "INVOICE_INFO_REJECTED", "INVOICE_PROCESSING", "INVOICE_ISSUED")


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("CREATE TABLE IF NOT EXISTS invoice_flow_retirement_backup (work_order_id INTEGER PRIMARY KEY, previous_status VARCHAR(64) NOT NULL)"))
    bind.execute(sa.text("CREATE TABLE IF NOT EXISTS finance_role_retirement_backup (user_id INTEGER PRIMARY KEY)"))
    bind.execute(sa.text("INSERT INTO invoice_flow_retirement_backup (work_order_id, previous_status) SELECT id, current_status FROM work_orders WHERE current_status IN :states AND id NOT IN (SELECT work_order_id FROM invoice_flow_retirement_backup)").bindparams(sa.bindparam("states", expanding=True)), {"states": OLD_STATES})
    bind.execute(sa.text("INSERT INTO finance_role_retirement_backup (user_id) SELECT user_id FROM user_roles WHERE role_id IN (SELECT id FROM roles WHERE code = 'FINANCE') AND user_id NOT IN (SELECT user_id FROM finance_role_retirement_backup)"))
    bind.execute(sa.text("UPDATE work_orders SET current_status = CASE WHEN mailing_status = 'COMPLETED' THEN 'WAIT_ARCHIVE_SUBMIT' WHEN mailing_status IN ('PROJECT_EDITING', 'PRINT_ROOM_PENDING', 'PROJECT_CONFIRMING') THEN 'REPORT_MAILING' ELSE 'PAPER_REPORT_ISSUED' END, current_handler_user_id = COALESCE(project_leader_id, initiator_user_id) WHERE current_status IN :states").bindparams(sa.bindparam("states", expanding=True)), {"states": OLD_STATES})
    bind.execute(sa.text("DELETE FROM user_roles WHERE role_id IN (SELECT id FROM roles WHERE code = 'FINANCE')"))
    bind.execute(sa.text("DELETE FROM roles WHERE code = 'FINANCE'"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("INSERT INTO roles (code, name, description, is_system_fixed) VALUES ('FINANCE', '财务人员', '财务角色', 1)"))
    bind.execute(sa.text("INSERT INTO user_roles (user_id, role_id) SELECT user_id, (SELECT id FROM roles WHERE code = 'FINANCE') FROM finance_role_retirement_backup"))
    bind.execute(sa.text("UPDATE work_orders SET current_status = (SELECT previous_status FROM invoice_flow_retirement_backup WHERE work_order_id = work_orders.id) WHERE id IN (SELECT work_order_id FROM invoice_flow_retirement_backup)"))
    op.drop_table("finance_role_retirement_backup")
    op.drop_table("invoice_flow_retirement_backup")
