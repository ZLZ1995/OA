"""Idempotent retirement for deployments that initialize schema on startup."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.db.session import engine

OLD_STATES = ("WAIT_INVOICE_INFO", "INVOICE_INFO_REJECTED", "INVOICE_PROCESSING", "INVOICE_ISSUED")


def backup_sqlite_if_needed() -> None:
    if engine.dialect.name != "sqlite" or not engine.url.database or engine.url.database == ":memory:":
        return
    source = Path(engine.url.database)
    if not source.is_file():
        return
    with sqlite3.connect(source) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"roles", "work_orders"}.issubset(tables):
            return
        needs_retirement = connection.execute("SELECT 1 FROM roles WHERE code = 'FINANCE' LIMIT 1").fetchone()
        if not needs_retirement:
            needs_retirement = connection.execute(
                "SELECT 1 FROM work_orders WHERE current_status IN (?,?,?,?) LIMIT 1", OLD_STATES
            ).fetchone()
        if not needs_retirement:
            return
        destination = source.with_name(source.stem + ".before-invoice-retirement-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + ".db")
        with sqlite3.connect(destination) as backup:
            connection.backup(backup)


def retire_invoice_flow(db: Session) -> None:
    db.execute(text("CREATE TABLE IF NOT EXISTS invoice_flow_retirement_backup (work_order_id INTEGER PRIMARY KEY, previous_status VARCHAR(64) NOT NULL)"))
    db.execute(text("CREATE TABLE IF NOT EXISTS finance_role_retirement_backup (user_id INTEGER PRIMARY KEY)"))
    db.execute(text("INSERT INTO invoice_flow_retirement_backup (work_order_id, previous_status) SELECT id, current_status FROM work_orders WHERE current_status IN :states AND id NOT IN (SELECT work_order_id FROM invoice_flow_retirement_backup)").bindparams(bindparam("states", expanding=True)), {"states": OLD_STATES})
    db.execute(text("INSERT INTO finance_role_retirement_backup (user_id) SELECT user_id FROM user_roles WHERE role_id IN (SELECT id FROM roles WHERE code = 'FINANCE') AND user_id NOT IN (SELECT user_id FROM finance_role_retirement_backup)"))
    db.execute(text("UPDATE work_orders SET current_status = CASE WHEN mailing_status = 'COMPLETED' THEN 'WAIT_ARCHIVE_SUBMIT' WHEN mailing_status IN ('PROJECT_EDITING', 'PRINT_ROOM_PENDING', 'PROJECT_CONFIRMING') THEN 'REPORT_MAILING' ELSE 'PAPER_REPORT_ISSUED' END, current_handler_user_id = COALESCE(project_leader_id, initiator_user_id) WHERE current_status IN :states").bindparams(bindparam("states", expanding=True)), {"states": OLD_STATES})
    db.execute(text("DELETE FROM user_roles WHERE role_id IN (SELECT id FROM roles WHERE code = 'FINANCE')"))
    db.execute(text("DELETE FROM roles WHERE code = 'FINANCE'"))
    db.commit()
