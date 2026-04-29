from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.workbench import WorkbenchProjectItem, WorkbenchResponse

router = APIRouter(prefix="/workbench", tags=["项目工作台"])

STATUS_MAP = {
    "PROJECT_CREATED": "项目创建",
    "WORK_ORDER_CREATED": "工单创建",
    "CONTRACT_UPLOADED": "合同上传",
    "WAIT_PRINTROOM_OFFICIAL_CONTRACT": "合同上传",
    "WAIT_FIRST_REVIEW_SUBMIT": "一审",
    "FIRST_REVIEWING": "一审",
    "FIRST_REVIEW_REJECTED": "一审",
    "FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND": "二审",
    "WAIT_SECOND_REVIEW_SUBMIT": "二审",
    "SECOND_REVIEWING": "二审",
    "SECOND_REVIEW_REJECTED": "二审",
    "SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD": "三审",
    "WAIT_THIRD_REVIEW_SUBMIT": "三审",
    "THIRD_REVIEWING": "三审",
    "THIRD_REVIEW_REJECTED": "三审",
    "THIRD_APPROVED_WAIT_PRINTROOM": "文印室出具",
    "PRINTROOM_PROCESSING": "文印室出具",
    "PAPER_REPORT_ISSUED": "文印室出具",
}


def _step(status: str | None, archived: bool) -> str:
    if archived:
        return "已归档"
    return STATUS_MAP.get(status or "", "项目创建")


@router.get("", response_model=WorkbenchResponse)
def get_workbench(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> WorkbenchResponse:
    base_query = db.query(Project).filter(Project.deleted_at.is_(None))
    my_projects: list[WorkbenchProjectItem] = []
    for p in base_query.filter(Project.business_user_id == current_user.id).order_by(Project.id.desc()).all():
        latest_status = db.query(WorkOrder.current_status).filter(WorkOrder.project_id == p.id).order_by(WorkOrder.id.desc()).limit(1).scalar()
        step = _step(latest_status, p.archived_at is not None)
        my_projects.append(WorkbenchProjectItem(
            id=p.id, project_no=p.project_code, project_name=p.project_name, client_name=p.client_name,
            current_step=step, status_display=step, todo_action=None, can_edit=True, can_delete=True,
            can_archive=p.archived_at is None, can_enter=True,
        ))

    member_project_ids = db.query(ProjectMember.project_id).filter(ProjectMember.user_id == current_user.id)
    todo_rows = (
        db.query(Project, WorkOrder)
        .join(WorkOrder, WorkOrder.project_id == Project.id)
        .filter(
            Project.deleted_at.is_(None),
            Project.archived_at.is_(None),
            or_(
                WorkOrder.current_handler_user_id == current_user.id,
                WorkOrder.project_leader_id == current_user.id,
                WorkOrder.project_id.in_(member_project_ids),
                WorkOrder.first_reviewer_id == current_user.id,
                WorkOrder.second_reviewer_id == current_user.id,
                WorkOrder.third_reviewer_id == current_user.id,
            ),
        )
        .order_by(WorkOrder.id.desc())
        .all()
    )
    todo_projects: list[WorkbenchProjectItem] = []
    seen = set()
    for p, w in todo_rows:
        if p.id in seen or p.business_user_id == current_user.id:
            continue
        seen.add(p.id)
        step = _step(w.current_status, False)
        todo_projects.append(WorkbenchProjectItem(
            id=p.id, project_no=p.project_code, project_name=p.project_name, client_name=p.client_name,
            current_step=step, status_display=step, todo_action=f"待处理：{step}", can_edit=False, can_delete=False,
            can_archive=False, can_enter=True,
        ))

    return WorkbenchResponse(my_projects=my_projects, todo_projects=todo_projects)
