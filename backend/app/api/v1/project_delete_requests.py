import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.project_delete_request import ProjectDeleteRequest
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.schemas.project_delete import (
    ProjectDeleteRequestCreate,
    ProjectDeleteRequestListResponse,
    ProjectDeleteRequestResponse,
)
from app.services.project_delete_service import (
    can_project_owner_delete_direct,
    delete_project_related_data,
    ensure_admin_approver_not_self,
    now_local,
)
from app.services.project_flow import normalize_project_step

router = APIRouter(prefix="/project-delete-requests", tags=["项目删除审核"])
logger = logging.getLogger(__name__)


def _is_admin(user: User) -> bool:
    return any(item.role.code == "ADMIN" for item in user.roles)


def _is_archive_project(project: Project, work_order: WorkOrder | None) -> bool:
    return project.archived_at is not None or (work_order and work_order.current_status == "ARCHIVED")


def _serialize(db: Session, row: ProjectDeleteRequest) -> ProjectDeleteRequestResponse:
    project = db.query(Project).filter(Project.id == row.project_id).first() if row.project_id else None
    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == row.project_id).order_by(WorkOrder.id.desc()).first() if row.project_id else None
    requester_name = db.query(User.real_name).filter(User.id == row.requester_user_id).scalar()
    approver_name = db.query(User.real_name).filter(User.id == row.approver_user_id).scalar()
    current_step = (
        "待确认删除"
        if row.status == "PENDING"
        else row.current_step
        if not project
        else normalize_project_step(work_order.current_status if work_order else None, False)
    )
    return ProjectDeleteRequestResponse(
        id=row.id,
        project_id=row.project_id,
        project_no=project.project_code if project else row.project_no,
        project_name=project.project_name if project else row.project_name,
        client_name=project.client_name if project else row.client_name,
        current_step=current_step,
        requester_user_id=row.requester_user_id,
        requester_user_name=requester_name,
        approver_user_id=row.approver_user_id,
        approver_user_name=approver_name,
        reason=row.reason,
        status=row.status,
        requested_at=row.requested_at,
        reviewed_at=row.reviewed_at,
    )


@router.get("", response_model=ProjectDeleteRequestListResponse)
def list_project_delete_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> ProjectDeleteRequestListResponse:
    status_rank = case(
        (ProjectDeleteRequest.status == "PENDING", 0),
        (ProjectDeleteRequest.status == "REJECTED", 1),
        (ProjectDeleteRequest.status == "APPROVED", 2),
        else_=3,
    )
    query = db.query(ProjectDeleteRequest).order_by(status_rank, ProjectDeleteRequest.requested_at.desc())
    if status_filter:
        query = query.filter(ProjectDeleteRequest.status == status_filter)
    return ProjectDeleteRequestListResponse(items=[_serialize(db, row) for row in query.all()])


@router.post("/projects/{project_id}", response_model=ProjectDeleteRequestResponse)
def request_project_delete(
    project_id: int,
    payload: ProjectDeleteRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDeleteRequestResponse:
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project_id).order_by(WorkOrder.id.desc()).first()
    existing = db.query(ProjectDeleteRequest).filter(ProjectDeleteRequest.project_id == project_id).first()
    if existing and existing.status == "PENDING":
        raise HTTPException(status_code=400, detail="已有待确认删除申请")

    approver = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(User.id == payload.approver_user_id, User.is_active.is_(True), Role.code == "ADMIN")
        .first()
    )
    if not approver:
        raise HTTPException(status_code=400, detail="请选择有效的管理员共同认证")
    ensure_admin_approver_not_self(current_user.id, payload.approver_user_id)

    is_project_leader = project.project_leader_id == current_user.id or (work_order and work_order.project_leader_id == current_user.id)
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None
    is_project_owner = is_project_leader or is_member

    if is_project_owner:
        if not _is_archive_project(project, work_order) and can_project_owner_delete_direct(work_order):
            raise HTTPException(status_code=400, detail="当前项目状态可直接删除，无需管理员确认")
    elif _is_admin(current_user):
        if not _is_archive_project(project, work_order):
            raise HTTPException(status_code=400, detail="管理员只能删除已归档项目")
    else:
        raise HTTPException(status_code=403, detail="仅项目负责人或管理员可申请删除该项目")

    if existing:
        existing.requester_user_id = current_user.id
        existing.approver_user_id = payload.approver_user_id
        existing.reason = payload.reason
        existing.status = "PENDING"
        existing.requested_at = now_local()
        existing.reviewed_at = None
        existing.project_no = project.project_code
        existing.project_name = project.project_name
        existing.client_name = project.client_name
        existing.current_step = "待确认删除"
        row = existing
    else:
        row = ProjectDeleteRequest(
            project_id=project_id,
            project_no=project.project_code,
            project_name=project.project_name,
            client_name=project.client_name,
            current_step="待确认删除",
            requester_user_id=current_user.id,
            approver_user_id=payload.approver_user_id,
            status="PENDING",
            reason=payload.reason,
            requested_at=now_local(),
        )
        db.add(row)

    project.termination_status = "DELETE_PENDING"
    project.termination_reason = payload.reason
    db.commit()
    db.refresh(row)
    logger.warning(
        "PROJECT_DELETE_REQUEST requester=%s approver=%s project_id=%s reason=%s",
        current_user.username,
        approver.username,
        project_id,
        payload.reason or "",
    )
    return _serialize(db, row)


@router.post("/{request_id}/approve")
def approve_project_delete(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict[str, str]:
    row = db.query(ProjectDeleteRequest).filter(ProjectDeleteRequest.id == request_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="删除申请不存在")
    if row.approver_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅共同认证管理员可确认删除")
    if row.status != "PENDING":
        raise HTTPException(status_code=400, detail="当前删除申请不可确认")
    project = db.query(Project).filter(Project.id == row.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    logger.warning(
        "PROJECT_DELETE_APPROVED approver=%s requester_user_id=%s project_id=%s project_no=%s",
        current_user.username,
        row.requester_user_id,
        project.id,
        project.project_code,
    )
    delete_project_related_data(db, project)
    db.commit()
    return {"message": "已确认删除并完成删除"}


@router.post("/{request_id}/reject")
def reject_project_delete(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict[str, str]:
    row = db.query(ProjectDeleteRequest).filter(ProjectDeleteRequest.id == request_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="删除申请不存在")
    if row.approver_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅共同认证管理员可驳回删除")
    if row.status != "PENDING":
        raise HTTPException(status_code=400, detail="当前删除申请不可驳回")

    project = db.query(Project).filter(Project.id == row.project_id).first()
    if project:
        project.termination_status = None
        project.termination_reason = None
    row.status = "REJECTED"
    row.reviewed_at = now_local()
    row.current_step = "已驳回"
    logger.warning("PROJECT_DELETE_REJECTED approver=%s project_id=%s", current_user.username, row.project_id)
    db.commit()
    return {"message": "删除申请已驳回"}
