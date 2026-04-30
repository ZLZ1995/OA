from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.workbench import WorkbenchProjectItem, WorkbenchResponse
from app.services.project_flow import build_todo_action, get_user_role_in_project, is_system_admin, normalize_project_step

router = APIRouter(prefix="/workbench", tags=["项目工作台"])


@router.get("", response_model=WorkbenchResponse)
def get_workbench(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> WorkbenchResponse:
    if is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="系统管理员不参与业务流程")

    base_query = db.query(Project).filter(Project.deleted_at.is_(None))
    my_projects: list[WorkbenchProjectItem] = []
    for p in base_query.filter(Project.business_user_id == current_user.id).order_by(Project.id.desc()).all():
        latest = db.query(WorkOrder).filter(WorkOrder.project_id == p.id).order_by(WorkOrder.id.desc()).first()
        step = normalize_project_step(latest.current_status if latest else None, p.archived_at is not None)
        my_projects.append(WorkbenchProjectItem(
            id=p.id, project_no=p.project_code, project_name=p.project_name, client_name=p.client_name,
            current_step=step, status_display=step, todo_action=None,
            can_edit=p.archived_at is None, can_delete=p.archived_at is None, can_archive=p.archived_at is None, can_enter=True,
        ))

    todo_projects: list[WorkbenchProjectItem] = []
    seen: set[int] = set()
    member_ids = {r[0] for r in db.query(ProjectMember.project_id).filter(ProjectMember.user_id == current_user.id).all()}
    work_orders = db.query(WorkOrder).order_by(WorkOrder.id.desc()).all()
    for w in work_orders:
        p = db.query(Project).filter(Project.id == w.project_id, Project.deleted_at.is_(None), Project.archived_at.is_(None)).first()
        if not p or p.id in seen or p.business_user_id == current_user.id:
            continue
        is_member = p.id in member_ids
        role = get_user_role_in_project(p, w, current_user, is_member)
        step = normalize_project_step(w.current_status, False)
        action = build_todo_action(step, role)
        if action is None:
            continue
        seen.add(p.id)
        todo_projects.append(WorkbenchProjectItem(
            id=p.id, project_no=p.project_code, project_name=p.project_name, client_name=p.client_name,
            current_step=step, status_display=step, todo_action=action,
            can_edit=False, can_delete=False, can_archive=False, can_enter=True,
        ))

    return WorkbenchResponse(my_projects=my_projects, todo_projects=todo_projects)
