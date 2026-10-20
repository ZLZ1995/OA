"""Explicit custodianship and reassignment; historical actions are never rewritten."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.project_handover import ProjectHandover
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.workflow_log import WorkflowLog
from app.models.invoice import Invoice
from app.services.chief_appraiser_service import get_project_chief_role_codes
from app.services.notification_service import create_notification

DUTIES = {
    "CREATOR": "创建人", "LEADER": "项目负责人",
    "contract_reviewer_id": "合同审核人", "first_reviewer_id": "一审老师",
    "second_reviewer_id": "二审老师", "third_reviewer_id": "三审老师",
    "chief_appraiser_user_id": "首席评估师", "archive_reviewer_id": "归档审核人",
    "print_room_handler_id": "文印办理人", "mailing_handler_user_id": "邮寄办理人",
    "current_handler_user_id": "当前办理人",
}
ROLE_CODES = {
    "contract_reviewer_id": {"CONTRACT_REVIEWER"}, "first_reviewer_id": {"FIRST_REVIEWER"},
    "second_reviewer_id": {"SECOND_REVIEWER"}, "third_reviewer_id": {"THIRD_REVIEWER"},
    "archive_reviewer_id": {"ARCHIVE_MANAGER"}, "print_room_handler_id": {"PRINT_ROOM"},
    "mailing_handler_user_id": {"PRINT_ROOM"},
}
REVIEW_DUTIES = set(ROLE_CODES) | {"chief_appraiser_user_id"}


def unfinished(project: Project, order: WorkOrder | None) -> bool:
    return not (project.deleted_at or project.archived_at or project.termination_status in {"APPROVED", "DELETE_PENDING"}
                or project.status in {"ARCHIVED", "TERMINATED", "DELETED"}
                or (order and order.current_status == "ARCHIVED"))


def project_orders(db: Session):
    for project in db.query(Project).filter(Project.deleted_at.is_(None)).order_by(Project.id).all():
        order = db.query(WorkOrder).filter(WorkOrder.project_id == project.id).order_by(WorkOrder.id.desc()).first()
        if unfinished(project, order):
            yield project, order


def duties_for(project, order, user_id):
    duties = []
    if project.business_user_id == user_id:
        duties.append("CREATOR")
    if project.project_leader_id == user_id or (order and order.project_leader_id == user_id):
        duties.append("LEADER")
    if order:
        duties.extend(field for field in sorted(REVIEW_DUTIES) if getattr(order, field) == user_id)
        if order.current_handler_user_id == user_id and not duties:
            duties.append("current_handler_user_id")
    return duties


def legacy_preview(db):
    inactive = {u.id: u for u in db.query(User).filter(User.is_active.is_(False)).all()}
    result = []
    for project, order in project_orders(db):
        for uid, user in inactive.items():
            duties = duties_for(project, order, uid)
            pending = {t.duty for t in db.query(ProjectHandover).filter_by(project_id=project.id, source_user_id=uid, status="PENDING").all()}
            duties = [d for d in duties if d not in pending]
            if duties:
                result.append({"project_id": project.id, "project_code": project.project_code,
                               "project_name": project.project_name, "source_user_id": uid,
                               "source_name": user.real_name, "duties": [DUTIES[d] for d in duties]})
    return result


def _notice(db, task, user_id, content):
    create_notification(db, user_id=user_id, biz_type="PROJECT_HANDOVER", biz_id=task.id,
                        title="项目职责交接", content=content, project_id=task.project_id,
                        work_order_id=task.work_order_id, link_type="PROJECT", link_target_id=task.project_id)


def _log(db, order, actor, remark):
    if order:
        db.add(WorkflowLog(work_order_id=order.id, from_status=order.current_status,
                           to_status=order.current_status, action_type="PROJECT_HANDOVER",
                           operator_user_id=actor.id, remark=remark))


def _set_party(db, project, order, duty, target_id):
    if duty == "CREATOR":
        project.business_user_id = target_id
    else:
        # Member rows must agree with the operational leader fields.
        for member in db.query(ProjectMember).filter_by(project_id=project.id).all():
            if member.member_role in {"LEADER", "PROJECT_LEADER", "项目负责人"}:
                member.member_role = "MEMBER"
        project.project_leader_id = target_id
        if order:
            order.project_leader_id = target_id
    member = db.query(ProjectMember).filter_by(project_id=project.id, user_id=target_id).first()
    if not member:
        db.add(ProjectMember(project_id=project.id, user_id=target_id, member_role="LEADER" if duty == "LEADER" else "MEMBER"))
    elif duty == "LEADER":
        member.member_role = "LEADER"
    db.flush()


def take_over(db: Session, source: User, admin: User, only_project_id: int | None = None):
    created = []
    # Serialize disable/recovery for the same account.
    db.query(User).filter(User.id == source.id).with_for_update().first()
    for project, order in project_orders(db):
        if only_project_id and project.id != only_project_id:
            continue
        db.query(Project).filter_by(id=project.id).with_for_update().first()
        duties = duties_for(project, order, source.id)
        current_duty = None
        if order and order.current_handler_user_id == source.id:
            # Preserve reviewer routing when the source holds several duties.
            status = order.current_status
            preferred = None
            for prefix, field in (("CONTRACT_REVIEWING", "contract_reviewer_id"), ("SIGNOFF_REVIEWING", "chief_appraiser_user_id"),
                                  ("ARCHIVE_REVIEWING", "archive_reviewer_id"), ("EXTERNAL_FIRST", "first_reviewer_id"),
                                  ("EXTERNAL_SECOND", "second_reviewer_id"), ("EXTERNAL_THIRD", "third_reviewer_id"),
                                  ("FIRST", "first_reviewer_id"), ("SECOND", "second_reviewer_id"), ("THIRD", "third_reviewer_id")):
                if status.startswith(prefix) and field in duties and ("REVIEWING" in status or "SELECT" in status or "RECALL" in status or "WAIT_OWNER_CONFIRM_SEND" in status or status == "THIRD_APPROVED_WAIT_PRINTROOM"):
                    preferred = field
                    break
            current_duty = preferred or ("LEADER" if "LEADER" in duties else next(iter(duties), None))
        for duty in duties:
            existing = db.query(ProjectHandover).filter_by(project_id=project.id, duty=duty, status="PENDING").first()
            if existing and existing.source_user_id == source.id:
                continue
            if existing:
                existing.status = "SUPERSEDED"
            task = ProjectHandover(project_id=project.id, work_order_id=order.id if order else None,
                                   duty=duty, source_user_id=source.id, custodian_user_id=admin.id,
                                   held_current_task=duty == current_duty, reason="账号停用，管理员接管并重新分配")
            db.add(task)
            if duty in {"CREATOR", "LEADER"}:
                task.custodian_member_created = not db.query(ProjectMember.id).filter_by(project_id=project.id, user_id=admin.id).first()
                _set_party(db, project, order, duty, admin.id)
            db.flush()
            _log(db, order, admin, f"{DUTIES[duty]}从账号 {source.id} 转入管理员 {admin.id} 接管，任务 {task.id}")
            _notice(db, task, admin.id, f"{project.project_code}：{DUTIES[duty]}待重新分配")
            created.append(task)
        if current_duty and order:
            order.current_handler_user_id = admin.id
    # An administrator may itself leave while holding pending review assignments.
    for task in db.query(ProjectHandover).filter_by(custodian_user_id=source.id, status="PENDING").all():
        if only_project_id and task.project_id != only_project_id:
            continue
        order = db.get(WorkOrder, task.work_order_id) if task.work_order_id else None
        if not unfinished(db.get(Project, task.project_id), order):
            continue
        task.custodian_user_id = admin.id
        if task.held_current_task and order and order.current_handler_user_id == source.id:
            order.current_handler_user_id = admin.id
        _log(db, order, admin, f"交接任务 {task.id} 的接管管理员由 {source.id} 改为 {admin.id}")
    db.flush()
    return created


def validate_target(db, task, project, order, target):
    if not target or not target.is_active:
        raise HTTPException(400, "请选择启用中的账号")
    codes = {r.role.code for r in target.roles}
    required = get_project_chief_role_codes(project) if task.duty == "chief_appraiser_user_id" else ROLE_CODES.get(task.duty, set())
    if task.duty == "current_handler_user_id" and order and order.current_status == "INVOICE_PROCESSING":
        required = {"FINANCE"}
    if task.duty == "chief_appraiser_user_id" and not required:
        raise HTTPException(400, "承做单位未配置首席角色")
    if required and not codes.intersection(required):
        raise HTTPException(400, "接任账号不具备该职责所需角色")
    if order:
        reviewer_ids = {getattr(order, d) for d in REVIEW_DUTIES if d != task.duty}
        if task.duty in {"CREATOR", "LEADER"} and target.id in reviewer_ids:
            raise HTTPException(400, "接任人已担任本项目审核或专职办理职责，请先重新分配该职责")
        if task.duty in REVIEW_DUTIES:
            parties = {project.business_user_id, project.project_leader_id, order.project_leader_id, order.initiator_user_id}
            parties.update(uid for uid, in db.query(ProjectMember.user_id).filter_by(project_id=project.id).all())
            if target.id in parties:
                raise HTTPException(400, "项目方人员不能承接本项目审核或专职办理职责")
            if task.duty in {"first_reviewer_id", "second_reviewer_id", "third_reviewer_id"}:
                others = {getattr(order, d) for d in ("first_reviewer_id", "second_reviewer_id", "third_reviewer_id") if d != task.duty}
                if target.id in others:
                    raise HTTPException(400, "同一账号不能兼任不同审核轮次")


def assign(db, task_id, target_id, admin, reason):
    task = db.query(ProjectHandover).filter_by(id=task_id).with_for_update().first()
    if not task or task.status != "PENDING":
        raise HTTPException(409, "交接任务不存在或已处理，请刷新")
    project = db.query(Project).filter_by(id=task.project_id).with_for_update().first()
    order = db.get(WorkOrder, task.work_order_id) if task.work_order_id else None
    if not unfinished(project, order):
        raise HTTPException(409, "项目已结束，无需重新分配")
    target = db.query(User).filter_by(id=target_id).with_for_update().first()
    validate_target(db, task, project, order, target)
    if task.duty in {"CREATOR", "LEADER"}:
        holder = project.business_user_id if task.duty == "CREATOR" else project.project_leader_id
        if holder != task.custodian_user_id:
            raise HTTPException(409, "项目职责已变化，请核对后处理")
        _set_party(db, project, order, task.duty, target_id)
    elif order:
        if task.duty != "current_handler_user_id" and getattr(order, task.duty) != task.source_user_id:
            raise HTTPException(409, "该职责已经变更，请核对交接任务")
        setattr(order, task.duty, target_id)
        if task.duty == "current_handler_user_id" and order.current_status == "INVOICE_PROCESSING":
            db.query(Invoice).filter(Invoice.work_order_id == order.id, Invoice.finance_handler_id == task.source_user_id,
                Invoice.status == "PENDING").update({Invoice.finance_handler_id: target_id}, synchronize_session="fetch")
    if task.held_current_task and order and order.current_handler_user_id == task.custodian_user_id:
        order.current_handler_user_id = target_id
    task.status, task.target_user_id, task.assigned_by = "ASSIGNED", target_id, admin.id
    task.reason = reason
    if task.duty in {"CREATOR", "LEADER"} and task.custodian_user_id not in {project.business_user_id, project.project_leader_id}:
        temporary_membership = db.query(ProjectHandover.id).filter_by(project_id=project.id,
            custodian_user_id=task.custodian_user_id, custodian_member_created=True).first()
        if temporary_membership:
            db.query(ProjectMember).filter_by(project_id=project.id, user_id=task.custodian_user_id).delete()
    _log(db, order, admin, f"交接任务 {task.id}：{DUTIES[task.duty]}重新分配给账号 {target_id}；{reason}")
    _notice(db, task, target_id, f"{project.project_code}：您已承接{DUTIES[task.duty]}，请查看当前项目流程")
    db.flush()
    return task


def pending_review_assignment(db, work_order_id):
    return db.query(ProjectHandover).filter(ProjectHandover.work_order_id == work_order_id,
        ProjectHandover.status == "PENDING", ProjectHandover.duty.in_(REVIEW_DUTIES)).first()


def assert_review_assignments_ready(db, work_order_id):
    if pending_review_assignment(db, work_order_id):
        raise HTTPException(409, "项目存在停用账号的审核或专职职责，请管理员先在“项目接管与交接”中重新分配")
