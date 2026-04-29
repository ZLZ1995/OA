from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project_member import ProjectMemberBatchCreate, ProjectMemberListResponse, ProjectMemberResponse

router = APIRouter(prefix="/project-members", tags=["项目成员"])
ROLE_MAP = {"项目负责人": "LEADER", "项目组成员": "MEMBER"}
ROLE_LABEL_MAP = {"LEADER": "项目负责人", "MEMBER": "项目组成员"}


def _to_response(item: ProjectMember, user: User) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        id=item.id,
        project_id=item.project_id,
        user_id=item.user_id,
        username=user.username,
        real_name=user.real_name,
        member_role=ROLE_LABEL_MAP.get(item.member_role, item.member_role),
        created_at=item.created_at,
    )


@router.get("", response_model=ProjectMemberListResponse)
def list_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectMemberListResponse:
    rows = (
        db.query(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .filter(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.id.desc())
        .all()
    )
    return ProjectMemberListResponse(items=[_to_response(item, user) for item, user in rows])


@router.post("/batch", response_model=ProjectMemberListResponse, status_code=status.HTTP_201_CREATED)
def batch_create_project_member(
    payload: ProjectMemberBatchCreate,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN", "PROJECT_LEADER")),
) -> ProjectMemberListResponse:
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    db_role = ROLE_MAP.get(payload.member_role)
    if not db_role:
        raise HTTPException(status_code=400, detail="成员角色仅支持：项目负责人、项目组成员")

    if db_role == "LEADER" and len(payload.user_ids) != 1:
        raise HTTPException(status_code=400, detail="项目负责人一次只能设置1人")

    if db_role == "LEADER":
        existing_leader = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == payload.project_id, ProjectMember.member_role == "LEADER")
            .first()
        )
        if existing_leader and existing_leader.user_id != payload.user_ids[0]:
            raise HTTPException(status_code=400, detail="当前项目已有项目负责人，请先更换原负责人")

    created: list[tuple[ProjectMember, User]] = []
    for user_id in payload.user_ids:
        exists = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == payload.project_id, ProjectMember.user_id == user_id)
            .first()
        )
        if exists:
            continue
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            continue
        row = ProjectMember(project_id=payload.project_id, user_id=user_id, member_role=db_role)
        db.add(row)
        db.flush()
        created.append((row, user))

    db.commit()
    for row, _ in created:
        db.refresh(row)

    return ProjectMemberListResponse(items=[_to_response(item, user) for item, user in created])


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
