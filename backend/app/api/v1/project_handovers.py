from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.project_handover import ProjectHandover
from app.models.user import User
from app.models.work_order import WorkOrder
from app.services.project_handover import DUTIES, assign, legacy_preview, take_over, validate_target

router = APIRouter(prefix="/project-handovers", tags=["项目接管"], dependencies=[Depends(require_roles("ADMIN"))])


class Assignment(BaseModel):
    target_user_id: int
    reason: str = Field(min_length=1, max_length=1000)


class Recovery(BaseModel):
    project_id: int
    source_user_id: int


@router.get("")
def list_handovers(db: Session = Depends(get_db)):
    rows = []
    for task in db.query(ProjectHandover).order_by(ProjectHandover.id.desc()).all():
        project = db.get(Project, task.project_id)
        def name(uid):
            user = db.get(User, uid) if uid else None
            return user.real_name if user else "-"
        rows.append({"id": task.id, "project_id": task.project_id, "project_code": project.project_code,
                     "project_name": project.project_name, "duty": DUTIES[task.duty], "status": task.status,
                     "source_name": name(task.source_user_id), "custodian_name": name(task.custodian_user_id),
                     "target_name": name(task.target_user_id), "reason": task.reason,
                     "created_at": task.created_at, "updated_at": task.updated_at})
    return {"items": rows, "legacy": legacy_preview(db)}


@router.post("/recover")
def recover(payload: Recovery, db: Session = Depends(get_db), admin: User = Depends(get_current_user)):
    source = db.get(User, payload.source_user_id)
    if not source or source.is_active:
        raise HTTPException(400, "仅可接管已停用账号的遗留职责")
    tasks = take_over(db, source, admin, payload.project_id)
    db.commit()
    return {"count": len(tasks)}


@router.get("/{task_id}/candidates")
def candidates(task_id: int, db: Session = Depends(get_db)):
    task = db.get(ProjectHandover, task_id)
    if not task:
        raise HTTPException(404, "交接任务不存在")
    project = db.get(Project, task.project_id)
    order = db.get(WorkOrder, task.work_order_id) if task.work_order_id else None
    items = []
    for user in db.query(User).filter(User.is_active.is_(True)).order_by(User.id).all():
        try:
            validate_target(db, task, project, order, user)
        except HTTPException:
            continue
        items.append({"id": user.id, "name": user.real_name, "username": user.username})
    return {"items": items}


@router.post("/{task_id}/assign")
def assign_handover(task_id: int, payload: Assignment, db: Session = Depends(get_db), admin: User = Depends(get_current_user)):
    if not payload.reason.strip():
        raise HTTPException(400, "请填写交接说明")
    assign(db, task_id, payload.target_user_id, admin, payload.reason.strip())
    db.commit()
    return {"status": "ok"}
