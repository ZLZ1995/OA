from fastapi import HTTPException, status


def require_any_role(user_role_codes: set[str], required_role_codes: set[str]) -> None:
    """Raise 403 if user roles do not intersect with required role set."""
    if user_role_codes.isdisjoint(required_role_codes):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限执行该操作")
