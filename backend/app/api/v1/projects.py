from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["项目"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectListResponse:
    rows = db.query(Project).order_by(Project.id.desc()).all()
    return ProjectListResponse(items=[ProjectResponse.model_validate(row, from_attributes=True) for row in rows])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER")),
) -> ProjectResponse:
    exists = db.query(Project).filter(Project.project_code == payload.project_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="项目编号已存在")

    row = Project(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ProjectResponse.model_validate(row, from_attributes=True)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectResponse:
    row = db.query(Project).filter(Project.id == project_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ProjectResponse.model_validate(row, from_attributes=True)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER")),
) -> ProjectResponse:
    row = db.query(Project).filter(Project.id == project_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ProjectResponse.model_validate(row, from_attributes=True)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> None:
    row = db.query(Project).filter(Project.id == project_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.delete(row)
    db.commit()
