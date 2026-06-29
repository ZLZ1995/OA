from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder

CHIEF_APPRAISER_ROLE_BY_UNIT: dict[str, str] = {
    "中勤": "CHIEF_APPRAISER_ZQ",
    "中立国际": "CHIEF_APPRAISER_ZLGJ",
}

CHIEF_APPRAISER_ROLE_CODES: set[str] = {
    "CHIEF_APPRAISER",
    *CHIEF_APPRAISER_ROLE_BY_UNIT.values(),
}


def get_project_chief_role_code(project: Project | None) -> str | None:
    if project is None:
        return None
    return CHIEF_APPRAISER_ROLE_BY_UNIT.get((project.undertaking_unit or "").strip())


def get_project_chief_role_codes(project: Project | None) -> set[str]:
    role_code = get_project_chief_role_code(project)
    if role_code:
        return {role_code}
    return set()


def user_has_role_code(user: User, role_codes: set[str]) -> bool:
    return any(item.role.code in role_codes for item in user.roles)


def get_project_chief_appraiser(db: Session, project: Project | None, *, exclude_username: str | None = None) -> User | None:
    role_codes = get_project_chief_role_codes(project)
    query = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            User.is_active.is_(True),
            Role.code.in_(role_codes),
        )
    )
    if exclude_username:
        query = query.filter(User.username != exclude_username)
    return query.order_by(User.id.asc()).first()


def work_order_matches_project_chief(current_user: User, project: Project | None, work_order: WorkOrder | None = None) -> bool:
    if any(item.role.code == "ADMIN" for item in current_user.roles):
        return True
    role_codes = get_project_chief_role_codes(project)
    if not user_has_role_code(current_user, role_codes):
        return False
    if work_order is None:
        return True
    if work_order.chief_appraiser_user_id and work_order.chief_appraiser_user_id != current_user.id:
        return False
    return True


def ensure_project_chief_permission(current_user: User, project: Project | None, work_order: WorkOrder | None = None) -> None:
    if not work_order_matches_project_chief(current_user, project, work_order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权执行该签发审核操作")


def ensure_supported_chief_unit(project: Project | None) -> str:
    role_code = get_project_chief_role_code(project)
    if not role_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前项目承做单位未配置签发首席角色")
    return role_code
