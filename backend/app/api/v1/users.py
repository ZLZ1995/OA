from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserRoleBindRequest,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["用户"])


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


@router.get("", response_model=UserListResponse)
def list_users(
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> UserListResponse:
    users = db.query(User).order_by(User.id.asc()).all()
    return UserListResponse(items=[_to_user_response(item) for item in users])


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
    _: set[str] = Depends(require_roles("ADMIN")),
) -> UserResponse:
    row = db.query(User).filter(User.id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return _to_user_response(row)


@router.put("/{user_id}/roles", response_model=UserResponse)
def bind_user_roles(
    user_id: int,
    payload: UserRoleBindRequest,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> UserResponse:
    row = db.query(User).filter(User.id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    db.query(UserRole).filter(UserRole.user_id == user_id).delete()
    if payload.role_codes:
        roles = db.query(Role).filter(Role.code.in_(payload.role_codes)).all()
        for role in roles:
            db.add(UserRole(user_id=user_id, role_id=role.id))

    db.commit()
    db.refresh(row)
    return _to_user_response(row)
