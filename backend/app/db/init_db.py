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
    ("PRINT_ROOM", "文印室", "文印室角色"),
    ("FINANCE", "财务人员", "财务角色"),
    ("ARCHIVE_MANAGER", "档案管理员", "档案管理角色"),
]

SUPER_ADMIN_USERNAME = settings.initial_admin_username
SUPER_ADMIN_PASSWORD = settings.initial_admin_password
SUPER_ADMIN_REAL_NAME = settings.initial_admin_real_name

LOCAL_BOOTSTRAP_USERS: list[dict[str, object]] = [
    {
        "username": "zhongqin123",
        "real_name": "系统管理员",
        "password_hash": "$2b$12$UJmlRxhp7L7WJy3GprgWOeRaAVF/B3ExkUhH3G3RfkhBV4owhXkm.",
        "role_codes": [
            "ADMIN",
            "SALES",
            "PROJECT_LEADER",
            "PROJECT_MEMBER",
            "CONTRACT_REVIEWER",
            "FIRST_REVIEWER",
            "SECOND_REVIEWER",
            "THIRD_REVIEWER",
            "PRINT_ROOM",
            "FINANCE",
            "ARCHIVE_MANAGER",
        ],
    },
    {
        "username": "张立志",
        "real_name": "张立志",
        "password_hash": "$2b$12$B3VjartK4zN0mprmk2otkuzFUtlPAFo/dW8L4g/IhGkjnJD/5vIn.",
        "role_codes": ["SALES", "PROJECT_LEADER", "PROJECT_MEMBER"],
    },
    {
        "username": "孙自现",
        "real_name": "孙自现",
        "password_hash": "$2b$12$kRAHe6hQ40ohGjTvMpFZgO7Hm/wdP/tU1olQt9vbte7uxeNHY2HVS",
        "role_codes": [
            "SALES",
            "PROJECT_LEADER",
            "PROJECT_MEMBER",
            "CONTRACT_REVIEWER",
            "FIRST_REVIEWER",
            "SECOND_REVIEWER",
            "THIRD_REVIEWER",
        ],
    },
    {
        "username": "付胜",
        "real_name": "付胜",
        "password_hash": "$2b$12$Te1rGmb0RbYumgah..LSw.GpB.NIKYaPZiYCqsuszeHM/Cc82.kRu",
        "role_codes": [
            "SALES",
            "PROJECT_LEADER",
            "PROJECT_MEMBER",
            "FIRST_REVIEWER",
            "SECOND_REVIEWER",
            "THIRD_REVIEWER",
        ],
    },
    {
        "username": "李利英",
        "real_name": "李利英",
        "password_hash": "$2b$12$Z6ecaghOLig1VbePF28jW.aEyt6pOuyrMzIz8sYTKNcMD1E80JLKC",
        "role_codes": ["CONTRACT_REVIEWER", "FIRST_REVIEWER", "SECOND_REVIEWER", "THIRD_REVIEWER"],
    },
    {
        "username": "李晓",
        "real_name": "李晓",
        "password_hash": "$2b$12$EDcZ7uZqXC0KkQYiCJkIj.DHAXg5VagKr9nEQHzehpN/liqmFJv1y",
        "role_codes": ["FINANCE"],
    },
    {
        "username": "王宇",
        "real_name": "王宇",
        "password_hash": "$2b$12$TbIZMEsC27ZNotunL7iCJeQZivzW.1itHP8.yxjCrGOfL1hy07M4e",
        "role_codes": ["PRINT_ROOM"],
    },
    {
        "username": "李彪",
        "real_name": "李彪",
        "password_hash": "$2b$12$0FBZrb1JrGy98PS5EnPbnezbgVHEIWJv3ohfmd6yJP.MH2K9BVQNW",
        "role_codes": ["ARCHIVE_MANAGER"],
    },
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        ensure_project_columns(db)
        ensure_work_order_columns(db)
        ensure_work_order_file_columns(db)
        ensure_contract_review_table(db)
        ensure_project_update_log_table(db)
        ensure_report_mailing_table(db)
        seed_fixed_roles(db)
        seed_initial_admin(db)
        sync_local_bootstrap_users(db)


def ensure_project_columns(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return

    existing_columns = {row[1] for row in db.execute(text("PRAGMA table_info('projects')")).fetchall()}
    if "undertaking_unit" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN undertaking_unit VARCHAR(32) DEFAULT '中勤' NOT NULL"))
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
    if "termination_status" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN termination_status VARCHAR(32) NULL"))
    if "termination_reason" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN termination_reason TEXT NULL"))
    if "termination_requested_by" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN termination_requested_by INTEGER NULL"))
    if "termination_requested_at" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN termination_requested_at TIMESTAMPTZ NULL"))
    if "termination_approved_by" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN termination_approved_by INTEGER NULL"))
    if "termination_approved_at" not in existing_columns:
        db.execute(text("ALTER TABLE projects ADD COLUMN termination_approved_at TIMESTAMPTZ NULL"))
    db.commit()


def ensure_work_order_file_columns(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return

    existing_columns = {row[1] for row in db.execute(text("PRAGMA table_info('work_order_files')")).fetchall()}
    if "file_size" not in existing_columns:
        db.execute(text("ALTER TABLE work_order_files ADD COLUMN file_size INTEGER NULL"))
    db.commit()


def ensure_work_order_columns(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return

    existing_columns = {row[1] for row in db.execute(text("PRAGMA table_info('work_orders')")).fetchall()}
    if "contract_reviewer_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN contract_reviewer_id INTEGER NULL"))
    if "signer_one" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN signer_one VARCHAR(64) NULL"))
    if "signer_two" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN signer_two VARCHAR(64) NULL"))
    if "formal_report_count" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN formal_report_count INTEGER NULL"))
    if "print_room_handler_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN print_room_handler_id INTEGER NULL"))
    if "mailing_handler_user_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN mailing_handler_user_id INTEGER NULL"))
    if "archive_reviewer_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN archive_reviewer_id INTEGER NULL"))
    if "archive_submitter_id" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN archive_submitter_id INTEGER NULL"))
    if "archive_submission_type" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN archive_submission_type VARCHAR(16) NULL"))
    if "mailing_status" not in existing_columns:
        db.execute(text("ALTER TABLE work_orders ADD COLUMN mailing_status VARCHAR(32) NULL"))

    invoice_columns = {row[1] for row in db.execute(text("PRAGMA table_info('invoices')")).fetchall()}
    if "invoice_info" not in invoice_columns:
        db.execute(text("ALTER TABLE invoices ADD COLUMN invoice_info TEXT NULL"))
    if "invoice_type" not in invoice_columns:
        db.execute(text("ALTER TABLE invoices ADD COLUMN invoice_type VARCHAR(16) NULL"))
    db.commit()


def ensure_contract_review_table(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return

    table_exists = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='contract_review_records'")).fetchone()
    if not table_exists:
        db.execute(
            text(
                """
                CREATE TABLE contract_review_records (
                    id INTEGER PRIMARY KEY,
                    work_order_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    action_type VARCHAR(32) NOT NULL,
                    operator_user_id INTEGER NOT NULL,
                    reviewer_user_id INTEGER NOT NULL,
                    comment TEXT NULL,
                    contract_file_id INTEGER NULL,
                    review_attachment_file_id INTEGER NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )
    db.commit()


def ensure_project_update_log_table(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return

    table_exists = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='project_update_logs'")).fetchone()
    if not table_exists:
        db.execute(
            text(
                """
                CREATE TABLE project_update_logs (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    operator_user_id INTEGER NOT NULL,
                    changed_fields TEXT NOT NULL,
                    remark VARCHAR(255) NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )
    db.commit()


def ensure_report_mailing_table(db: Session) -> None:
    if engine.dialect.name != "sqlite":
        return

    table_exists = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='report_mailing_records'")).fetchone()
    if not table_exists:
        db.execute(
            text(
                """
                CREATE TABLE report_mailing_records (
                    id INTEGER PRIMARY KEY,
                    work_order_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    action_type VARCHAR(32) NOT NULL,
                    operator_user_id INTEGER NOT NULL,
                    receiver_name VARCHAR(128) NULL,
                    receiver_phone VARCHAR(64) NULL,
                    receiver_address TEXT NULL,
                    receiver_remark TEXT NULL,
                    express_no VARCHAR(128) NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
                    invalidated_express_no VARCHAR(128) NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )
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


def sync_local_bootstrap_users(db: Session) -> None:
    roles_by_code = {role.code: role for role in db.query(Role).all()}
    for item in LOCAL_BOOTSTRAP_USERS:
        username = str(item["username"])
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                real_name=str(item["real_name"]),
                password_hash=str(item["password_hash"]),
                is_active=True,
            )
            db.add(user)
            db.flush()

        user.real_name = str(item["real_name"])
        user.password_hash = str(item["password_hash"])
        user.is_active = True

        role_codes = item["role_codes"]
        db.query(UserRole).filter(UserRole.user_id == user.id).delete()
        for code in role_codes if isinstance(role_codes, list) else []:
            role = roles_by_code.get(str(code))
            if role:
                db.add(UserRole(user_id=user.id, role_id=role.id))

    db.commit()
