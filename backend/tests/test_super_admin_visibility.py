import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.users import bind_user_roles, list_users
from app.api.v1.users import delete_user, reset_user_password
from app.db.base import Base
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import UserPasswordResetRequest, UserRoleBindRequest
from app.core.security import get_password_hash, verify_password


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_users_and_roles(db: Session) -> tuple[User, User, User]:
    roles = [
        Role(code="ADMIN", name="管理员", description="", is_system_fixed=True),
        Role(code="PROJECT_LEADER", name="项目负责人", description="", is_system_fixed=True),
    ]
    db.add_all(roles)
    db.flush()

    super_admin = User(username="zhongqin123", password_hash=get_password_hash("oldpass1"), real_name="SuperAdmin", is_active=True)
    another_admin = User(username="admin2", password_hash=get_password_hash("oldpass2"), real_name="AnotherAdmin", is_active=True)
    leader = User(username="leader", password_hash=get_password_hash("oldpass3"), real_name="Leader", is_active=True)
    db.add_all([super_admin, another_admin, leader])
    db.flush()

    admin_role = roles[0]
    leader_role = roles[1]
    db.add_all(
        [
            UserRole(user_id=super_admin.id, role_id=admin_role.id),
            UserRole(user_id=another_admin.id, role_id=admin_role.id),
            UserRole(user_id=leader.id, role_id=leader_role.id),
        ]
    )
    db.commit()
    return super_admin, another_admin, leader


def test_non_super_user_cannot_see_super_admin_in_list() -> None:
    db = _build_session()
    super_admin, another_admin, _ = _seed_users_and_roles(db)

    resp = list_users(db=db, current_user=another_admin, _={"ADMIN"})
    usernames = [item.username for item in resp.items]

    assert super_admin.username not in usernames
    assert another_admin.username in usernames


def test_super_admin_can_see_self_in_list() -> None:
    db = _build_session()
    super_admin, _, _ = _seed_users_and_roles(db)

    resp = list_users(db=db, current_user=super_admin, _={"ADMIN"})
    usernames = [item.username for item in resp.items]

    assert super_admin.username in usernames


def test_non_super_admin_cannot_bind_roles_for_super_admin() -> None:
    db = _build_session()
    super_admin, another_admin, _ = _seed_users_and_roles(db)

    payload = UserRoleBindRequest(role_codes=["ADMIN"])
    with pytest.raises(HTTPException) as exc_info:
        bind_user_roles(
            user_id=super_admin.id,
            payload=payload,
            db=db,
            current_user=another_admin,
            _={"ADMIN"},
        )
    assert exc_info.value.status_code == 404


def test_admin_can_reset_user_password() -> None:
    db = _build_session()
    _, another_admin, leader = _seed_users_and_roles(db)

    payload = UserPasswordResetRequest(password="newpass123")
    resp = reset_user_password(
        user_id=leader.id,
        payload=payload,
        db=db,
        current_user=another_admin,
        _={"ADMIN"},
    )

    db.refresh(leader)
    assert resp.id == leader.id
    assert verify_password("newpass123", leader.password_hash)
    assert not verify_password("oldpass3", leader.password_hash)


def test_non_super_admin_cannot_reset_super_admin_password() -> None:
    db = _build_session()
    super_admin, another_admin, _ = _seed_users_and_roles(db)

    payload = UserPasswordResetRequest(password="newpass123")
    with pytest.raises(HTTPException) as exc_info:
        reset_user_password(
            user_id=super_admin.id,
            payload=payload,
            db=db,
            current_user=another_admin,
            _={"ADMIN"},
        )

    assert exc_info.value.status_code == 404


def test_delete_user_deactivates_account_and_removes_roles() -> None:
    db = _build_session()
    _, another_admin, leader = _seed_users_and_roles(db)

    resp = delete_user(
        user_id=leader.id,
        db=db,
        current_user=another_admin,
        _={"ADMIN"},
    )

    db.refresh(leader)
    assert resp["message"] == "账号已删除"
    assert leader.is_active is False
    assert db.query(UserRole).filter(UserRole.user_id == leader.id).count() == 0

    listed = list_users(db=db, current_user=another_admin, _={"ADMIN"})
    assert leader.username not in [item.username for item in listed.items]


def test_admin_cannot_delete_self() -> None:
    db = _build_session()
    _, another_admin, _ = _seed_users_and_roles(db)

    with pytest.raises(HTTPException) as exc_info:
        delete_user(
            user_id=another_admin.id,
            db=db,
            current_user=another_admin,
            _={"ADMIN"},
        )

    assert exc_info.value.status_code == 400
