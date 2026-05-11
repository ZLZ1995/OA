import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.auth import reset_password
from app.core.security import get_password_hash, verify_password
from app.db.base import Base
from app.models.user import User
from app.schemas.auth import PasswordResetRequest


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_user(db: Session) -> User:
    user = User(
        username="leader",
        password_hash=get_password_hash("Old123"),
        real_name="Leader",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_reset_password_updates_hash_after_old_password_check() -> None:
    db = _build_session()
    user = _seed_user(db)

    payload = PasswordResetRequest(
        username="leader",
        old_password="Old123",
        new_password="New789",
    )
    resp = reset_password(payload=payload, db=db)
    db.refresh(user)

    assert resp["message"] == "密码更改成功"
    assert verify_password("New789", user.password_hash)


def test_reset_password_rejects_wrong_old_password() -> None:
    db = _build_session()
    _seed_user(db)

    payload = PasswordResetRequest(
        username="leader",
        old_password="Wrong1",
        new_password="New789",
    )
    with pytest.raises(HTTPException) as exc_info:
        reset_password(payload=payload, db=db)

    assert exc_info.value.detail == "原密码验证失败"


def test_reset_password_requires_six_to_eight_ascii_letters_or_digits() -> None:
    with pytest.raises(ValidationError):
        PasswordResetRequest(
            username="leader",
            old_password="Old123",
            new_password="含中文123",
        )

    with pytest.raises(ValidationError):
        PasswordResetRequest(
            username="leader",
            old_password="Old123",
            new_password="abc123456",
        )
