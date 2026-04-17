from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import RoleBindRequest, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["账号管理"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserOut]:
    require_roles(current_user, {"ADMIN"})
    users = db.query(User).order_by(User.id.desc()).all()
    return [
        UserOut(
            id=u.id,
            username=u.username,
            real_name=u.real_name,
            email=u.email,
            phone=u.phone,
            is_active=u.is_active,
            roles=[item.role.code for item in u.roles],
        )
        for u in users
    ]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    require_roles(current_user, {"ADMIN"})
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="账号已存在")

    user = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        real_name=payload.real_name,
        email=payload.email,
        phone=payload.phone,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        roles=[],
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    require_roles(current_user, {"ADMIN"})
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        roles=[item.role.code for item in user.roles],
    )


@router.put("/{user_id}/roles", response_model=UserOut)
def bind_user_roles(
    user_id: int,
    payload: RoleBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    require_roles(current_user, {"ADMIN"})
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    roles = db.query(Role).filter(Role.code.in_(payload.role_codes)).all()
    if len(roles) != len(set(payload.role_codes)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="存在无效角色编码")

    db.query(UserRole).filter(UserRole.user_id == user_id).delete()
    for role in roles:
        db.add(UserRole(user_id=user_id, role_id=role.id))

    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        roles=[item.role.code for item in user.roles],
    )
