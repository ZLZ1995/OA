from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.project_delete_request import ProjectDeleteRequest
from app.models.project_member import ProjectMember
from app.models.reminder_event import ReminderEvent
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.workflow_log import WorkflowLog
from app.schemas.workbench import WorkbenchProjectItem, WorkbenchResponse
from app.services.project_flow import get_project_leader_display_name, normalize_project_step

router = APIRouter(prefix="/workbench", tags=["项目工作台"])


def _todo_action_text(
    project: Project,
    work_order: WorkOrder,
    step: str,
    can_approve_delete: bool,
    can_approve_termination: bool,
    rejected_invoice: object | None,
    confirming_invoice: object | None,
    is_project_party: bool,
) -> str:
    if can_approve_delete:
        return "待确认删除"
    if can_approve_termination:
        return f"待审核：{project.termination_reason}"
    if work_order.current_status == "FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND":
        if work_order.current_handler_user_id == work_order.project_leader_id:
            return "请选择二审老师并提交审核"
        return "待一审老师决定二审流向"
    if work_order.current_status == "SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD":
        if work_order.current_handler_user_id == work_order.project_leader_id:
            return "请选择三审老师并提交审核"
        return "待二审老师决定三审流向"
    if rejected_invoice and is_project_party:
        return "开票信息被退回，请修改后重新提交"
    if confirming_invoice and is_project_party:
        return "财务已完成开票，请确认或退回修改"
    if step == "合同初稿审核" and work_order.contract_reviewer_id == work_order.current_handler_user_id:
        return "请处理合同初稿审核"
    if (
        step == "报告邮寄"
        and work_order.mailing_handler_user_id == work_order.current_handler_user_id
        and work_order.mailing_status == "PRINT_ROOM_PENDING"
    ):
        return "请填写快递单号"
    return f"待处理：{step}"


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

    for project in base_query.filter(my_project_filter).order_by(Project.id.desc()).all():
        latest_work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project.id).order_by(WorkOrder.id.desc()).first()
        delete_request = db.query(ProjectDeleteRequest).filter(ProjectDeleteRequest.project_id == project.id).first()
        step = normalize_project_step(
            latest_work_order.current_status if latest_work_order else None,
            project.archived_at is not None,
            project.project_source,
        )
        if project.termination_status == "DELETE_PENDING":
            step = "待确认删除"
        elif project.termination_status == "PENDING":
            step = "项目终止/废止审核中"
        elif project.termination_status == "APPROVED" and project.archived_at is None:
            step = "项目终止/废止已通过"

        leader = db.query(User).filter(User.id == project.project_leader_id).first()
        approver_name = db.query(User.real_name).filter(User.id == delete_request.approver_user_id).scalar() if delete_request else None
        requester_name = db.query(User.real_name).filter(User.id == delete_request.requester_user_id).scalar() if delete_request else None
        latest_reminder = (
            db.query(ReminderEvent)
            .filter(ReminderEvent.project_id == project.id)
            .order_by(ReminderEvent.created_at.desc(), ReminderEvent.id.desc())
            .first()
        )
        remind_count_today = 0
        if latest_work_order and latest_work_order.current_handler_user_id:
            start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            remind_count_today = (
                db.query(ReminderEvent)
                .filter(
                    ReminderEvent.work_order_id == latest_work_order.id,
                    ReminderEvent.current_handler_user_id == latest_work_order.current_handler_user_id,
                    ReminderEvent.created_at >= start_of_day,
                )
                .count()
            )
        my_projects.append(
            WorkbenchProjectItem(
                id=project.id,
                project_no=project.project_code,
                project_name=project.project_name,
                client_name=project.client_name,
                project_leader_name=get_project_leader_display_name(project, leader.real_name if leader else None),
                current_step=step,
                status_display=step,
                todo_action=None,
                termination_status=project.termination_status,
                termination_reason=project.termination_reason,
                delete_request_status=delete_request.status if delete_request else None,
                delete_request_id=delete_request.id if delete_request else None,
                delete_request_reason=delete_request.reason if delete_request else None,
                delete_approver_user_id=delete_request.approver_user_id if delete_request else None,
                delete_approver_user_name=approver_name,
                delete_requester_user_name=requester_name,
                delete_requested_at=delete_request.requested_at.strftime("%Y-%m-%d %H:%M:%S") if delete_request else None,
                can_edit=project.archived_at is None and project.termination_status not in {"PENDING", "DELETE_PENDING"},
                can_delete=project.archived_at is None and project.termination_status not in {"PENDING", "DELETE_PENDING"},
                can_archive=project.archived_at is None and latest_work_order is not None and (latest_work_order.archive_submission_type == "APPROVED" or project.termination_status == "APPROVED"),
                can_request_termination=project.archived_at is None and project.termination_status not in {"PENDING", "APPROVED", "DELETE_PENDING"},
                can_approve_delete=False,
                can_enter=True,
                is_reminded=latest_reminder is not None,
                remind_count_today=remind_count_today,
                latest_remind_at=latest_reminder.created_at.strftime("%Y-%m-%d %H:%M:%S") if latest_reminder else None,
            )
        )

    role_pool_filters = []
    if "FINANCE" in role_codes or "ADMIN" in role_codes:
        pending_invoice_work_orders = db.query(Invoice.work_order_id).filter(Invoice.status.in_(["SUBMITTED", "PROJECT_RETURNED"]))
        if "ADMIN" not in role_codes:
            pending_invoice_work_orders = pending_invoice_work_orders.filter(Invoice.finance_handler_id == current_user.id)
        role_pool_filters.append(WorkOrder.id.in_(pending_invoice_work_orders))
    if "ARCHIVE_MANAGER" in role_codes or "ADMIN" in role_codes:
        role_pool_filters.append(
            and_(
                WorkOrder.archive_reviewer_id == current_user.id,
                WorkOrder.archive_submission_type.in_(["ONLINE", "OFFLINE"]),
            )
        )
    if "CONTRACT_REVIEWER" in role_codes or "ADMIN" in role_codes:
        role_pool_filters.append(WorkOrder.contract_reviewer_id == current_user.id)
    if "CHIEF_APPRAISER" in role_codes or "ADMIN" in role_codes:
        role_pool_filters.append(WorkOrder.chief_appraiser_user_id == current_user.id)
    if "PRINT_ROOM" in role_codes or "ADMIN" in role_codes:
        role_pool_filters.append(
            and_(
                WorkOrder.print_room_handler_id == current_user.id,
                or_(
                    WorkOrder.current_status.notin_(["REPORT_MAILING", "REPORT_MAILING_COMPLETED"]),
                    WorkOrder.mailing_status == "PRINT_ROOM_PENDING",
                ),
            )
        )
        role_pool_filters.append(
            and_(
                WorkOrder.mailing_handler_user_id == current_user.id,
                WorkOrder.mailing_status == "PRINT_ROOM_PENDING",
            )
        )
    if "ADMIN" in role_codes:
        role_pool_filters.append(Project.termination_status == "PENDING")
        pending_delete_project_ids = db.query(ProjectDeleteRequest.project_id).filter(
            ProjectDeleteRequest.status == "PENDING",
            ProjectDeleteRequest.approver_user_id == current_user.id,
        )
        role_pool_filters.append(Project.id.in_(pending_delete_project_ids))

    archived_delete_project_ids: set[int] = set()
    if "ADMIN" in role_codes:
        archived_delete_project_ids = {
            item[0]
            for item in db.query(ProjectDeleteRequest.project_id)
            .filter(
                ProjectDeleteRequest.status == "PENDING",
                ProjectDeleteRequest.approver_user_id == current_user.id,
                ProjectDeleteRequest.project_id.is_not(None),
            )
            .all()
        }

    todo_rows = (
        db.query(Project, WorkOrder)
        .join(WorkOrder, WorkOrder.project_id == Project.id)
        .filter(
            Project.deleted_at.is_(None),
            or_(Project.archived_at.is_(None), Project.id.in_(archived_delete_project_ids)),
            or_(Project.termination_status.is_(None), Project.termination_status != "APPROVED", Project.id.in_(archived_delete_project_ids)),
            or_(
                WorkOrder.current_handler_user_id == current_user.id,
                WorkOrder.project_leader_id == current_user.id,
                WorkOrder.project_id.in_(member_project_id_set),
                WorkOrder.archive_submitter_id == current_user.id,
                WorkOrder.initiator_user_id == current_user.id,
                *role_pool_filters,
            ),
        )
        .order_by(WorkOrder.id.desc())
        .all()
    )

    todo_projects: list[WorkbenchProjectItem] = []
    seen = set()
    for project, work_order in todo_rows:
        if project.id in seen:
            continue
        rejected_invoice = db.query(Invoice.id).filter(Invoice.work_order_id == work_order.id, Invoice.status == "REJECTED").first()
        pending_invoice_filters = [
            Invoice.work_order_id == work_order.id,
            Invoice.status.in_(["SUBMITTED", "PROJECT_RETURNED"]),
        ]
        if "ADMIN" not in role_codes:
            pending_invoice_filters.append(Invoice.finance_handler_id == current_user.id)
        pending_invoice = db.query(Invoice.id).filter(*pending_invoice_filters).first()
        confirming_invoice = db.query(Invoice.id).filter(Invoice.work_order_id == work_order.id, Invoice.status == "FINANCE_COMPLETED").first()

        is_project_party = (
            work_order.project_leader_id == current_user.id
            or work_order.project_id in member_project_id_set
            or project.business_user_id == current_user.id
            or work_order.initiator_user_id == current_user.id
        )
        is_print_room_assignee = (
            ("PRINT_ROOM" in role_codes or "ADMIN" in role_codes)
            and (
                work_order.current_handler_user_id == current_user.id
                or (
                    work_order.print_room_handler_id == current_user.id
                    and (
                        work_order.current_status not in {"REPORT_MAILING", "REPORT_MAILING_COMPLETED"}
                        or work_order.mailing_status == "PRINT_ROOM_PENDING"
                    )
                )
                or (
                    work_order.mailing_handler_user_id == current_user.id
                    and work_order.mailing_status == "PRINT_ROOM_PENDING"
                )
            )
        )
        if project.business_user_id == current_user.id and work_order.current_handler_user_id != current_user.id and not rejected_invoice and not confirming_invoice:
            if work_order.current_status not in {"WAIT_CONTRACT_REVIEW_SUBMIT", "CONTRACT_REJECTED", "REPORT_MAILING", "REPORT_MAILING_COMPLETED", "WAIT_ARCHIVE_SUBMIT", "ARCHIVE_REJECTED"}:
                continue

        if (
            pending_invoice
            and "FINANCE" not in role_codes
            and "ADMIN" not in role_codes
            and not (
                work_order.current_status in {"REPORT_MAILING", "REPORT_MAILING_COMPLETED"}
                and work_order.mailing_handler_user_id == current_user.id
            )
        ):
            continue

        if (
            work_order.current_status in {"REPORT_MAILING", "REPORT_MAILING_COMPLETED"}
            and not is_project_party
            and not is_print_room_assignee
            and not (pending_invoice and ("FINANCE" in role_codes or "ADMIN" in role_codes))
            and not (confirming_invoice and is_project_party)
            and "ADMIN" not in role_codes
        ):
            continue

        delete_request = db.query(ProjectDeleteRequest).filter(ProjectDeleteRequest.project_id == project.id).first()
        can_approve_termination = "ADMIN" in role_codes and project.termination_status == "PENDING"
        can_approve_delete = bool(
            "ADMIN" in role_codes
            and delete_request
            and delete_request.status == "PENDING"
            and delete_request.approver_user_id == current_user.id
        )
        if can_approve_delete:
            step = "待确认删除"
        elif can_approve_termination:
            step = "项目终止/废止审核"
        elif work_order.current_status == "CONTRACT_REVIEWING" and work_order.contract_reviewer_id == current_user.id:
            step = "合同初稿审核"
        elif work_order.current_status == "SIGNOFF_REVIEWING" and work_order.chief_appraiser_user_id == current_user.id:
            step = "签发审核"
        elif pending_invoice and ("FINANCE" in role_codes or "ADMIN" in role_codes):
            step = "财务开票"
        elif confirming_invoice and is_project_party:
            step = "发票开具"
        elif work_order.current_status == "REPORT_MAILING":
            step = "报告邮寄"
        elif rejected_invoice and is_project_party:
            step = "发票开具"
        elif work_order.archive_reviewer_id == current_user.id and work_order.archive_submission_type in {"ONLINE", "OFFLINE"}:
            step = "底稿审核"
        elif work_order.archive_submitter_id == current_user.id and work_order.archive_submission_type in {"APPROVED", "REJECTED"}:
            step = "报告归档"
        else:
            step = normalize_project_step(work_order.current_status, False, project.project_source)

        seen.add(project.id)
        leader = db.query(User).filter(User.id == project.project_leader_id).first()
        approver_name = db.query(User.real_name).filter(User.id == delete_request.approver_user_id).scalar() if delete_request else None
        requester_name = db.query(User.real_name).filter(User.id == delete_request.requester_user_id).scalar() if delete_request else None
        latest_reminder = (
            db.query(ReminderEvent)
            .filter(ReminderEvent.project_id == project.id)
            .order_by(ReminderEvent.created_at.desc(), ReminderEvent.id.desc())
            .first()
        )
        remind_count_today = 0
        if work_order.current_handler_user_id:
            start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            remind_count_today = (
                db.query(ReminderEvent)
                .filter(
                    ReminderEvent.work_order_id == work_order.id,
                    ReminderEvent.current_handler_user_id == work_order.current_handler_user_id,
                    ReminderEvent.created_at >= start_of_day,
                )
                .count()
            )
        latest_log = (
            db.query(WorkflowLog, User)
            .join(User, User.id == WorkflowLog.operator_user_id)
            .filter(WorkflowLog.work_order_id == work_order.id)
            .order_by(WorkflowLog.id.desc())
            .first()
        )
        todo_action = _todo_action_text(
            project=project,
            work_order=work_order,
            step=step,
            can_approve_delete=can_approve_delete,
            can_approve_termination=can_approve_termination,
            rejected_invoice=rejected_invoice,
            confirming_invoice=confirming_invoice,
            is_project_party=is_project_party,
        )
        todo_projects.append(
            WorkbenchProjectItem(
                id=project.id,
                project_no=project.project_code,
                project_name=project.project_name,
                client_name=project.client_name,
                project_leader_name=get_project_leader_display_name(project, leader.real_name if leader else None),
                transfer_user_name=latest_log[1].real_name if latest_log else None,
                current_step=step,
                status_display=step,
                todo_action=todo_action,
                termination_status=project.termination_status,
                termination_reason=project.termination_reason,
                delete_request_status=delete_request.status if delete_request else None,
                delete_request_id=delete_request.id if delete_request else None,
                delete_request_reason=delete_request.reason if delete_request else None,
                delete_approver_user_id=delete_request.approver_user_id if delete_request else None,
                delete_approver_user_name=approver_name,
                delete_requester_user_name=requester_name,
                delete_requested_at=delete_request.requested_at.strftime("%Y-%m-%d %H:%M:%S") if delete_request else None,
                can_edit=False,
                can_delete=False,
                can_archive=False,
                can_enter=True,
                can_approve_termination=can_approve_termination,
                can_approve_delete=can_approve_delete,
                is_reminded=latest_reminder is not None,
                remind_count_today=remind_count_today,
                latest_remind_at=latest_reminder.created_at.strftime("%Y-%m-%d %H:%M:%S") if latest_reminder else None,
            )
        )

    return WorkbenchResponse(my_projects=my_projects, todo_projects=todo_projects)
