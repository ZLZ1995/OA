from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project_member import ProjectMemberCreate, ProjectMemberListResponse, ProjectMemberResponse

router = APIRouter(prefix="/project-members", tags=["项目成员"])


@router.get("", response_model=ProjectMemberListResponse)
def list_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectMemberListResponse:
    rows = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.id.desc())
        .all()
    )
    return ProjectMemberListResponse(
        items=[ProjectMemberResponse.model_validate(item, from_attributes=True) for item in rows]
    )


@router.post("", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def create_project_member(
    payload: ProjectMemberCreate,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN", "PROJECT_LEADER")),
) -> ProjectMemberResponse:
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    exists = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == payload.project_id, ProjectMember.user_id == payload.user_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="成员已存在")

    row = ProjectMember(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ProjectMemberResponse.model_validate(row, from_attributes=True)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_member(
    member_id: int,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN", "PROJECT_LEADER")),
) -> None:
    row = db.query(ProjectMember).filter(ProjectMember.id == member_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="成员不存在")
    db.delete(row)
    db.commit()
