from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.role import Role
from app.schemas.role import RoleListResponse, RoleResponse

router = APIRouter(prefix="/roles", tags=["角色"])


@router.get("", response_model=RoleListResponse)
def list_roles(
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> RoleListResponse:
    rows = db.query(Role).order_by(Role.id.asc()).all()
    return RoleListResponse(
        items=[
            RoleResponse(id=row.id, code=row.code, name=row.name, description=row.description)
            for row in rows
        ]
    )
