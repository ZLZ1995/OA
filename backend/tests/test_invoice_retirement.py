from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import retire_invoice_flow as retirement


def test_startup_retirement_preserves_history_and_backs_up_sqlite(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'oa.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE roles (id INTEGER PRIMARY KEY, code VARCHAR(64))"))
        connection.execute(text("CREATE TABLE user_roles (id INTEGER PRIMARY KEY, user_id INTEGER, role_id INTEGER)"))
        connection.execute(text("CREATE TABLE work_orders (id INTEGER PRIMARY KEY, current_status VARCHAR(64), mailing_status VARCHAR(32), current_handler_user_id INTEGER, project_leader_id INTEGER, initiator_user_id INTEGER)"))
        connection.execute(text("CREATE TABLE invoices (id INTEGER PRIMARY KEY, work_order_id INTEGER)"))
        connection.execute(text("INSERT INTO roles VALUES (1, 'FINANCE')"))
        connection.execute(text("INSERT INTO user_roles VALUES (1, 9, 1)"))
        connection.execute(text("INSERT INTO work_orders VALUES (1, 'WAIT_INVOICE_INFO', NULL, 9, 2, 3), (2, 'INVOICE_PROCESSING', 'PROJECT_CONFIRMING', 9, 2, 3), (3, 'INVOICE_ISSUED', 'COMPLETED', 9, 2, 3)"))
        connection.execute(text("INSERT INTO invoices VALUES (1, 1)"))

    monkeypatch.setattr(retirement, "engine", engine)
    retirement.backup_sqlite_if_needed()
    with Session(engine) as session:
        retirement.retire_invoice_flow(session)
        retirement.retire_invoice_flow(session)
        assert session.execute(text("SELECT id, current_status FROM work_orders ORDER BY id")).all() == [
            (1, "PAPER_REPORT_ISSUED"), (2, "REPORT_MAILING"), (3, "WAIT_ARCHIVE_SUBMIT")
        ]
        assert session.execute(text("SELECT count(*) FROM roles")).scalar() == 0
        assert session.execute(text("SELECT count(*) FROM user_roles")).scalar() == 0
        assert session.execute(text("SELECT count(*) FROM invoices")).scalar() == 1
        assert session.execute(text("SELECT count(*) FROM invoice_flow_retirement_backup")).scalar() == 3
        assert session.execute(text("SELECT count(*) FROM finance_role_retirement_backup")).scalar() == 1
    assert len(list(tmp_path.glob("oa.before-invoice-retirement-*.db"))) == 1
