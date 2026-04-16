from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate and return JWT token."""
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout() -> dict[str, str]:
    """Stateless JWT logout endpoint for frontend compatibility."""
    return {"message": "已退出登录，请在前端清除令牌"}


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Get current logged-in user information."""
    roles = [r.role.code for r in current_user.roles]
    return CurrentUserResponse(
        id=current_user.id,
        username=current_user.username,
        real_name=current_user.real_name,
        roles=roles,
    )
