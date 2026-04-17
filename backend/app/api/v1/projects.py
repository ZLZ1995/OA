from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectOut]:
    require_roles(current_user, {"ADMIN", "SALES", "PROJECT_LEADER"})
    rows = db.query(Project).order_by(Project.id.desc()).all()
    return [
        ProjectOut(
            id=row.id,
            project_code=row.project_code,
            project_name=row.project_name,
            client_name=row.client_name,
            business_user_id=row.business_user_id,
            project_leader_id=row.project_leader_id,
            department_id=row.department_id,
            status=row.status,
            description=row.description,
        )
        for row in rows
    ]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectOut:
    require_roles(current_user, {"ADMIN", "SALES", "PROJECT_LEADER"})
    exists = db.query(Project).filter(Project.project_code == payload.project_code).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="项目编号已存在")

    row = Project(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ProjectOut(**row.__dict__)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectOut:
    require_roles(current_user, {"ADMIN", "SALES", "PROJECT_LEADER", "PROJECT_MEMBER"})
    row = db.query(Project).filter(Project.id == project_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return ProjectOut(**row.__dict__)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectOut:
    require_roles(current_user, {"ADMIN", "SALES", "PROJECT_LEADER"})
    row = db.query(Project).filter(Project.id == project_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ProjectOut(**row.__dict__)
