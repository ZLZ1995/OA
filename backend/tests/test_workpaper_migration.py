"""The additive migration must preserve existing projects and tolerate startup schema creation."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_migration_preserves_existing_rows_and_is_repeatable():
    path = Path(__file__).parents[1] / "migrations/versions/0007_operation_workpapers.py"
    spec = importlib.util.spec_from_file_location("workpaper_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for table in ("projects", "work_orders", "users", "work_order_files"):
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            connection.execute(text(f"INSERT INTO {table} (id) VALUES (7)"))
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
            module.upgrade()
        assert connection.execute(text("SELECT id, workflow_version FROM projects")).all() == [(7, None)]
        assert connection.execute(text("SELECT id, operation_workpaper_reviewer_id FROM work_orders")).all() == [(7, None)]
        inspector = inspect(connection)
        assert {"operation_workpaper_reviews", "operation_workpaper_submissions", "operation_workpaper_submission_files"}.issubset(inspector.get_table_names())
        assert len(inspector.get_unique_constraints("operation_workpaper_submissions")) == 2
    engine.dispose()
