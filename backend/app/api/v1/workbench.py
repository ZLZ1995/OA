from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.workflow_log import WorkflowLog
from app.schemas.workbench import WorkbenchProjectItem, WorkbenchResponse

router = APIRouter(prefix="/workbench", tags=["项目工作台"])

STATUS_MAP = {
    "PROJECT_CREATED": "项目创建",
    "WORK_ORDER_CREATED": "工单创建",
    "WAIT_CONTRACT_UPLOAD": "合同上传",
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
    "THIRD_APPROVED_WAIT_PRINTROOM": "正式报告文件",
    "PRINTROOM_PROCESSING": "文印室出具",
    "PAPER_REPORT_ISSUED": "文印室出具",
    "WAIT_INVOICE_INFO": "发票开具",
    "INVOICE_INFO_REJECTED": "发票开具",
    "INVOICE_PROCESSING": "财务开票",
    "INVOICE_ISSUED": "发票已开具",
    "WAIT_ARCHIVE_SUBMIT": "报告归档",
    "ARCHIVE_REVIEWING": "底稿审核",
    "ARCHIVE_REJECTED": "报告归档",
    "ARCHIVED": "已归档",
}


def _step(status: str | None, archived: bool) -> str:
    if archived:
        return "已归档"
    return STATUS_MAP.get(status or "", "项目创建")


@router.get("", response_model=WorkbenchResponse)
def get_workbench(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> WorkbenchResponse:
    role_codes = {item.role.code for item in current_user.roles}
    base_query = db.query(Project).filter(Project.deleted_at.is_(None))
    my_projects: list[WorkbenchProjectItem] = []
    member_project_ids = db.query(ProjectMember.project_id).filter(ProjectMember.user_id == current_user.id)
    member_project_id_set = {item[0] for item in member_project_ids.all()}
    my_project_filter = or_(
        Project.business_user_id == current_user.id,
        Project.project_leader_id == current_user.id,
        Project.id.in_(member_project_id_set),
    )
    for p in base_query.filter(my_project_filter).order_by(Project.id.desc()).all():
        latest_work_order = db.query(WorkOrder).filter(WorkOrder.project_id == p.id).order_by(WorkOrder.id.desc()).first()
        step = _step(latest_work_order.current_status if latest_work_order else None, p.archived_at is not None)
        if p.termination_status == "PENDING":
            step = "项目终止/废止审核中"
        elif p.termination_status == "APPROVED" and p.archived_at is None:
            step = "项目终止/废止已通过"
        leader = db.query(User).filter(User.id == p.project_leader_id).first()
        my_projects.append(WorkbenchProjectItem(
            id=p.id, project_no=p.project_code, project_name=p.project_name, client_name=p.client_name,
            project_leader_name=leader.real_name if leader else None,
            current_step=step, status_display=step, todo_action=None,
            termination_status=p.termination_status,
            termination_reason=p.termination_reason,
            can_edit=p.archived_at is None and p.termination_status != "PENDING",
            can_delete=p.archived_at is None and p.termination_status != "PENDING",
            can_archive=p.archived_at is None and latest_work_order is not None and (latest_work_order.archive_submission_type == "APPROVED" or p.termination_status == "APPROVED"),
            can_request_termination=p.archived_at is None and p.termination_status not in {"PENDING", "APPROVED"},
            can_enter=True,
        ))

    role_pool_filters = []
    if "FINANCE" in role_codes or "ADMIN" in role_codes:
        role_pool_filters.append(WorkOrder.current_status == "INVOICE_PROCESSING")
    if "ARCHIVE_MANAGER" in role_codes or "ADMIN" in role_codes:
        role_pool_filters.append(
            and_(
                WorkOrder.archive_reviewer_id == current_user.id,
                WorkOrder.archive_submission_type.in_(["ONLINE", "OFFLINE"]),
            )
        )
    if "ADMIN" in role_codes:
        role_pool_filters.append(Project.termination_status == "PENDING")
    todo_rows = (
        db.query(Project, WorkOrder)
        .join(WorkOrder, WorkOrder.project_id == Project.id)
        .filter(
            Project.deleted_at.is_(None),
            Project.archived_at.is_(None),
            or_(Project.termination_status.is_(None), Project.termination_status != "APPROVED"),
            or_(
                WorkOrder.current_handler_user_id == current_user.id,
                WorkOrder.project_leader_id == current_user.id,
                WorkOrder.project_id.in_(member_project_id_set),
                WorkOrder.archive_submitter_id == current_user.id,
                *role_pool_filters,
            ),
        )
        .order_by(WorkOrder.id.desc())
        .all()
    )
    todo_projects: list[WorkbenchProjectItem] = []
    seen = set()
    for p, w in todo_rows:
        if p.id in seen:
            continue
        if p.business_user_id == current_user.id and w.current_handler_user_id != current_user.id:
            continue
        if w.current_status == "INVOICE_PROCESSING" and "FINANCE" not in role_codes and "ADMIN" not in role_codes:
            continue
        can_approve_termination = "ADMIN" in role_codes and p.termination_status == "PENDING"
        if can_approve_termination:
            step = "项目终止/废止审核"
        elif w.archive_reviewer_id == current_user.id and w.archive_submission_type in {"ONLINE", "OFFLINE"}:
            step = "底稿审核"
        elif w.archive_submitter_id == current_user.id and w.archive_submission_type == "APPROVED":
            step = "报告归档"
        elif w.archive_submitter_id == current_user.id and w.archive_submission_type == "REJECTED":
            step = "报告归档"
        else:
            step = _step(w.current_status, False)
        seen.add(p.id)
        leader = db.query(User).filter(User.id == p.project_leader_id).first()
        latest_log = (
            db.query(WorkflowLog, User)
            .join(User, User.id == WorkflowLog.operator_user_id)
            .filter(WorkflowLog.work_order_id == w.id)
            .order_by(WorkflowLog.id.desc())
            .first()
        )
        todo_projects.append(WorkbenchProjectItem(
            id=p.id, project_no=p.project_code, project_name=p.project_name, client_name=p.client_name,
            project_leader_name=leader.real_name if leader else None,
            transfer_user_name=latest_log[1].real_name if latest_log else None,
            current_step=step, status_display=step,
            todo_action=f"待审核：{p.termination_reason}" if can_approve_termination else f"待处理：{step}",
            termination_status=p.termination_status,
            termination_reason=p.termination_reason,
            can_edit=False, can_delete=False,
            can_archive=False, can_enter=True,
            can_approve_termination=can_approve_termination,
        ))

    return WorkbenchResponse(my_projects=my_projects, todo_projects=todo_projects)
