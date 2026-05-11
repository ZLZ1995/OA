from app.core.security import get_password_hash, verify_password


def test_get_password_hash_and_verify_with_short_password() -> None:
    password = "zhongqin123"
    hashed = get_password_hash(password)

    assert isinstance(hashed, str)
    assert hashed
    assert verify_password(password, hashed)
