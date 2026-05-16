from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import engine
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole

FIXED_ROLES: list[tuple[str, str, str]] = [
    ("ADMIN", "管理员", "系统管理员"),
    ("SALES", "市场业务员", "市场业务角色"),
    ("PROJECT_LEADER", "项目负责人", "项目负责人角色"),
    ("PROJECT_MEMBER", "项目组成员", "项目组成员角色"),
    ("CONTRACT_REVIEWER", "合同审核人", "合同审核角色"),
    ("FIRST_REVIEWER", "一审人员", "一审角色"),
    ("SECOND_REVIEWER", "二审人员", "二审角色"),
    ("THIRD_REVIEWER", "三审人员", "三审角色"),
    ("CHIEF_APPRAISER", "首席评估师", "签发审核角色"),
    ("PRINT_ROOM", "文印室", "文印室角色"),
    ("FINANCE", "财务人员", "财务角色"),
    ("ARCHIVE_MANAGER", "档案管理员", "档案管理角色"),
]

SUPER_ADMIN_USERNAME = settings.initial_admin_username
SUPER_ADMIN_PASSWORD = settings.initial_admin_password
SUPER_ADMIN_REAL_NAME = settings.initial_admin_real_name


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        ensure_project_columns(db)
        ensure_work_order_columns(db)
        ensure_work_order_file_columns(db)
        seed_fixed_roles(db)
        seed_initial_admin(db)


def ensure_project_columns(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return
    existing_columns = {row[1] for row in db.execute(text("PRAGMA table_info('projects')")).fetchall()}
    if "undertaking_unit" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN undertaking_unit VARCHAR(32) DEFAULT '中勤' NOT NULL"))
    if "evaluation_business_nature" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN evaluation_business_nature VARCHAR(64) NULL"))
    if "report_type" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN report_type VARCHAR(32) NULL"))
    if "valuation_base_date" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN valuation_base_date DATE NULL"))
    if "business_salesman" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN business_salesman VARCHAR(255) NULL"))
    if "project_amount" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN project_amount FLOAT NULL"))
    if "project_source" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN project_source VARCHAR(16) DEFAULT 'INTERNAL' NOT NULL"))
    if "external_project_leader_name" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN external_project_leader_name VARCHAR(255) NULL"))
    if "archived_at" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN archived_at TIMESTAMPTZ NULL"))
    if "deleted_at" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMPTZ NULL"))
    db.commit()


def ensure_work_order_columns(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return
    existing_columns = {row[1] for row in db.execute(text("PRAGMA table_info('work_orders')")).fetchall()}
    column_sql = {
        "contract_reviewer_id": "ALTER TABLE work_orders ADD COLUMN contract_reviewer_id INTEGER NULL",
        "signer_one": "ALTER TABLE work_orders ADD COLUMN signer_one VARCHAR(64) NULL",
        "signer_two": "ALTER TABLE work_orders ADD COLUMN signer_two VARCHAR(64) NULL",
        "formal_report_count": "ALTER TABLE work_orders ADD COLUMN formal_report_count INTEGER NULL",
        "print_room_handler_id": "ALTER TABLE work_orders ADD COLUMN print_room_handler_id INTEGER NULL",
        "mailing_handler_user_id": "ALTER TABLE work_orders ADD COLUMN mailing_handler_user_id INTEGER NULL",
        "archive_reviewer_id": "ALTER TABLE work_orders ADD COLUMN archive_reviewer_id INTEGER NULL",
        "archive_submitter_id": "ALTER TABLE work_orders ADD COLUMN archive_submitter_id INTEGER NULL",
        "archive_submission_type": "ALTER TABLE work_orders ADD COLUMN archive_submission_type VARCHAR(16) NULL",
        "mailing_status": "ALTER TABLE work_orders ADD COLUMN mailing_status VARCHAR(32) NULL",
        "signoff_status": "ALTER TABLE work_orders ADD COLUMN signoff_status VARCHAR(32) NULL",
        "chief_appraiser_user_id": "ALTER TABLE work_orders ADD COLUMN chief_appraiser_user_id INTEGER NULL",
    }
    for column, sql in column_sql.items():
        if column not in existing_columns:
            db.execute(text(sql))
    db.commit()


def ensure_work_order_file_columns(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return
    existing_columns = {row[1] for row in db.execute(text("PRAGMA table_info('work_order_files')")).fetchall()}
    if "file_size" not in existing_columns:
        db.execute(text("ALTER TABLE work_order_files ADD COLUMN file_size INTEGER NULL"))
    if "source_type" not in existing_columns:
        db.execute(text("ALTER TABLE work_order_files ADD COLUMN source_type VARCHAR(32) DEFAULT 'MANUAL' NOT NULL"))
    if "source_file_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_order_files ADD COLUMN source_file_id INTEGER NULL"))
    if "locked" not in existing_columns:
        db.execute(text("ALTER TABLE work_order_files ADD COLUMN locked BOOLEAN DEFAULT FALSE NOT NULL"))
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
        admin.password_hash = get_password_hash(SUPER_ADMIN_PASSWORD)
        admin.real_name = SUPER_ADMIN_REAL_NAME
        admin.is_active = True

    all_role_ids = [role.id for role in db.query(Role).all()]
    bound_role_ids = {item.role_id for item in db.query(UserRole).filter(UserRole.user_id == admin.id).all()}
    for role_id in all_role_ids:
        if role_id not in bound_role_ids:
            db.add(UserRole(user_id=admin.id, role_id=role_id))
    db.commit()
