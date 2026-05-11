from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserPasswordResetRequest,
    UserResponse,
    UserRoleBindRequest,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["用户"])
SUPER_ADMIN_USERNAME = settings.initial_admin_username


def _is_super_admin(user: User) -> bool:
    return user.username == SUPER_ADMIN_USERNAME


def _to_user_response(row: User) -> UserResponse:
    return UserResponse(
        id=row.id,
        username=row.username,
        real_name=row.real_name,
        email=row.email,
        phone=row.phone,
        is_active=row.is_active,
        roles=[ur.role.code for ur in row.roles],
    )


def _get_visible_active_user_or_404(
    db: Session, user_id: int, current_user: User
) -> User:
    row = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    if row.username == SUPER_ADMIN_USERNAME and not _is_super_admin(current_user):
        raise HTTPException(status_code=404, detail="用户不存在")
    return row


@router.get("", response_model=UserListResponse)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN", "PROJECT_LEADER")),
) -> UserListResponse:
    query = db.query(User).filter(User.is_active.is_(True))
    if not _is_super_admin(current_user):
        query = query.filter(User.username != SUPER_ADMIN_USERNAME)
    users = query.order_by(User.id.asc()).all()
    return UserListResponse(items=[_to_user_response(item) for item in users])


@router.get("/candidates", response_model=UserListResponse)
def list_user_candidates(
    role_code: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> UserListResponse:
    rows = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.code == role_code, User.is_active.is_(True))
        .order_by(User.id.asc())
        .all()
    )
    return UserListResponse(items=[_to_user_response(item) for item in rows])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> UserResponse:
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")

    row = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        real_name=payload.real_name,
        email=payload.email,
        phone=payload.phone,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()

    if payload.role_codes:
        roles = db.query(Role).filter(Role.code.in_(payload.role_codes)).all()
        for role in roles:
            db.add(UserRole(user_id=row.id, role_id=role.id))

    db.commit()
    db.refresh(row)
    return _to_user_response(row)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> UserResponse:
    row = _get_visible_active_user_or_404(db, user_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return _to_user_response(row)


@router.put("/{user_id}/password", response_model=UserResponse)
def reset_user_password(
    user_id: int,
    payload: UserPasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> UserResponse:
    row = _get_visible_active_user_or_404(db, user_id, current_user)
    row.password_hash = get_password_hash(payload.password)
    db.commit()
    db.refresh(row)
    return _to_user_response(row)


@router.put("/{user_id}/roles", response_model=UserResponse)
def bind_user_roles(
    user_id: int,
    payload: UserRoleBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> UserResponse:
    row = _get_visible_active_user_or_404(db, user_id, current_user)

    db.query(UserRole).filter(UserRole.user_id == user_id).delete()
    if payload.role_codes:
        roles = db.query(Role).filter(Role.code.in_(payload.role_codes)).all()
        for role in roles:
            db.add(UserRole(user_id=user_id, role_id=role.id))

    db.commit()
    db.refresh(row)
    return _to_user_response(row)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict[str, str]:
    row = _get_visible_active_user_or_404(db, user_id, current_user)
    if row.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    if row.username == SUPER_ADMIN_USERNAME:
        raise HTTPException(status_code=400, detail="不能删除超级管理员账号")

    db.query(UserRole).filter(UserRole.user_id == row.id).delete()
    row.is_active = False
    db.commit()
    return {"message": "账号已删除"}
