from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401  # Import all models for metadata registration.
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole

FIXED_ROLES: list[tuple[str, str, str]] = [
    ("ADMIN", "管理员", "系统管理员"),
    ("SALES", "市场业务人员", "市场业务角色"),
    ("PROJECT_LEADER", "项目负责人", "项目负责人角色"),
    ("PROJECT_MEMBER", "项目组成员", "项目组成员角色"),
    ("FIRST_REVIEWER", "一审人员", "一审角色"),
    ("SECOND_REVIEWER", "二审人员", "二审角色"),
    ("THIRD_REVIEWER", "三审人员", "三审角色"),
    ("PRINT_ROOM", "文印室", "文印室角色"),
    ("FINANCE", "财务人员", "财务角色"),
    ("ARCHIVE_MANAGER", "档案管理员", "档案管理角色"),
]
SUPER_ADMIN_USERNAME = settings.initial_admin_username
SUPER_ADMIN_PASSWORD = settings.initial_admin_password
SUPER_ADMIN_REAL_NAME = settings.initial_admin_real_name


def init_db() -> None:
    """Create all tables and initialize fixed roles + admin account."""
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        ensure_project_columns(db)
        ensure_work_order_columns(db)
        ensure_work_order_file_columns(db)
        seed_fixed_roles(db)
        seed_initial_admin(db)


def ensure_project_columns(db: Session) -> None:
    """Ensure newly introduced project lifecycle columns exist for existing deployments."""
    if engine.dialect.name != "sqlite":
        return

    existing_columns = {
        row[1]
        for row in db.execute(text("PRAGMA table_info('projects')")).fetchall()
    }
    if 'undertaking_unit' not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN undertaking_unit VARCHAR(32) DEFAULT '中勤' NOT NULL"))
    if 'archived_at' not in existing_columns:
        db.execute(text('ALTER TABLE projects ADD COLUMN archived_at TIMESTAMPTZ NULL'))
    if 'deleted_at' not in existing_columns:
        db.execute(text('ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMPTZ NULL'))
    if 'termination_status' not in existing_columns:
        db.execute(text('ALTER TABLE projects ADD COLUMN termination_status VARCHAR(32) NULL'))
    if 'termination_reason' not in existing_columns:
        db.execute(text('ALTER TABLE projects ADD COLUMN termination_reason TEXT NULL'))
    if 'termination_requested_by' not in existing_columns:
        db.execute(text('ALTER TABLE projects ADD COLUMN termination_requested_by INTEGER NULL'))
    if 'termination_requested_at' not in existing_columns:
        db.execute(text('ALTER TABLE projects ADD COLUMN termination_requested_at TIMESTAMPTZ NULL'))
    if 'termination_approved_by' not in existing_columns:
        db.execute(text('ALTER TABLE projects ADD COLUMN termination_approved_by INTEGER NULL'))
    if 'termination_approved_at' not in existing_columns:
        db.execute(text('ALTER TABLE projects ADD COLUMN termination_approved_at TIMESTAMPTZ NULL'))
    db.commit()


def ensure_work_order_file_columns(db: Session) -> None:
    """Ensure file metadata columns exist for existing SQLite deployments."""
    if engine.dialect.name != "sqlite":
        return

    existing_columns = {
        row[1]
        for row in db.execute(text("PRAGMA table_info('work_order_files')")).fetchall()
    }
    if "file_size" not in existing_columns:
        db.execute(text("ALTER TABLE work_order_files ADD COLUMN file_size INTEGER NULL"))
    db.commit()


def ensure_work_order_columns(db: Session) -> None:
    """Ensure newly introduced work order metadata columns exist for SQLite."""
    if engine.dialect.name != "sqlite":
        return

    existing_columns = {
        row[1]
        for row in db.execute(text("PRAGMA table_info('work_orders')")).fetchall()
    }
    if "signer_one" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN signer_one VARCHAR(64) NULL"))
    if "signer_two" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN signer_two VARCHAR(64) NULL"))
    if "formal_report_count" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN formal_report_count INTEGER NULL"))
    if "print_room_handler_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN print_room_handler_id INTEGER NULL"))
    if "archive_reviewer_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN archive_reviewer_id INTEGER NULL"))
    if "archive_submitter_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN archive_submitter_id INTEGER NULL"))
    if "archive_submission_type" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN archive_submission_type VARCHAR(16) NULL"))
    invoice_columns = {
        row[1]
        for row in db.execute(text("PRAGMA table_info('invoices')")).fetchall()
    }
    if "invoice_info" not in invoice_columns:
        db.execute(text("ALTER TABLE invoices ADD COLUMN invoice_info TEXT NULL"))
    if "invoice_type" not in invoice_columns:
        db.execute(text("ALTER TABLE invoices ADD COLUMN invoice_type VARCHAR(16) NULL"))
    db.commit()


def seed_fixed_roles(db: Session) -> None:
    for code, name, desc in FIXED_ROLES:
        exists = db.query(Role).filter(Role.code == code).first()
        if not exists:
            db.add(Role(code=code, name=name, description=desc, is_system_fixed=True))
    db.commit()


def seed_initial_admin(db: Session) -> None:
    admin = db.query(User).filter(User.username == SUPER_ADMIN_USERNAME).first()
    if not admin:
        admin = User(
            username=SUPER_ADMIN_USERNAME,
            password_hash=get_password_hash(SUPER_ADMIN_PASSWORD),
            real_name=SUPER_ADMIN_REAL_NAME,
            is_active=True,
        )
        db.add(admin)
        db.flush()
    else:
        # Keep super admin credential aligned with configured bootstrap credential.
        admin.password_hash = get_password_hash(SUPER_ADMIN_PASSWORD)
        admin.real_name = SUPER_ADMIN_REAL_NAME
        admin.is_active = True

    # Ensure super admin has all fixed roles.
    all_role_ids = [role.id for role in db.query(Role).all()]
    bound_role_ids = {
        item.role_id
        for item in db.query(UserRole).filter(UserRole.user_id == admin.id).all()
    }
    for role_id in all_role_ids:
        if role_id not in bound_role_ids:
            db.add(UserRole(user_id=admin.id, role_id=role_id))

    db.commit()
