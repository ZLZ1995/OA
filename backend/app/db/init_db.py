from sqlalchemy.orm import Session

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
SUPER_ADMIN_USERNAME = "zhongqin123"
SUPER_ADMIN_PASSWORD = "zhongqin123"
SUPER_ADMIN_REAL_NAME = "超级管理员"


def init_db() -> None:
    """Create all tables and initialize fixed roles + admin account."""
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_fixed_roles(db)
        seed_initial_admin(db)


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
