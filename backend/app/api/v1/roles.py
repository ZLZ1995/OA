from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleOut

router = APIRouter(prefix="/roles", tags=["角色"])


@router.get("", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RoleOut]:
    require_roles(current_user, {"ADMIN"})
    roles = db.query(Role).order_by(Role.id.asc()).all()
    return [RoleOut(id=item.id, code=item.code, name=item.name, description=item.description) for item in roles]
