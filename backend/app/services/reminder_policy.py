from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.reminder_event import ReminderEvent
from app.models.user import User
from app.models.workflow_log import WorkflowLog
from app.models.work_order import WorkOrder

REMIND_AFTER = timedelta(hours=48)
REMIND_COOLDOWN = timedelta(hours=6)
MAX_REMINDS_PER_DAY = 3

EFFECTIVE_ACTION_PREFIXES = (
    "SUBMIT",
    "APPROVE",
    "REJECT",
    "RETURN",
    "FORWARD",
    "ISSUE",
    "ARCHIVE",
    "CONFIRM",
    "PROJECT_TERMINATION",
    "PROJECT_DELETE",
)
EFFECTIVE_ACTION_TYPES = {
    "CONTRACT_REVIEW_SUBMIT",
    "CONTRACT_REVIEW_APPROVE",
    "CONTRACT_REVIEW_REJECT",
    "REPORT_MAILING_SUBMIT",
    "REPORT_MAILING_CONFIRM",
    "REPORT_MAILING_RETURN",
}


@dataclass
class ReminderEligibility:
    can_remind: bool
    reason_code: str | None
    reason_message: str | None
    current_handler_user_id: int | None
    current_handler_name: str | None
    elapsed_seconds: int
    remaining_seconds_to_48h: int
    today_remind_count: int
    remaining_seconds_to_next_remind: int
    current_status: str | None


def _is_effective_action(action_type: str | None) -> bool:
    if not action_type:
        return False
    if action_type in EFFECTIVE_ACTION_TYPES:
        return True
    return any(action_type.startswith(prefix) for prefix in EFFECTIVE_ACTION_PREFIXES)


def build_handler_cycle_key(work_order: WorkOrder) -> str:
    return f"{work_order.id}:{work_order.current_handler_user_id}:{work_order.current_status}"


def get_project_membership(db: Session, project_id: int, user_id: int) -> bool:
    return db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id).first() is not None


def get_last_effective_action_time(db: Session, work_order: WorkOrder) -> datetime:
    latest_log = (
        db.query(WorkflowLog)
        .filter(WorkflowLog.work_order_id == work_order.id)
        .order_by(WorkflowLog.created_at.desc(), WorkflowLog.id.desc())
        .all()
    )
    for log in latest_log:
        if _is_effective_action(log.action_type):
            return log.created_at
    return work_order.updated_at or work_order.created_at


def evaluate_reminder_eligibility(
    db: Session,
    *,
    work_order: WorkOrder,
    project: Project,
    current_user: User,
    now: datetime | None = None,
) -> ReminderEligibility:
    now = now or datetime.now()
    role_codes = {item.role.code for item in current_user.roles}
    is_project_member = get_project_membership(db, project.id, current_user.id)
    can_initiate = project.project_leader_id == current_user.id or is_project_member or "ADMIN" in role_codes
    if not can_initiate:
        return ReminderEligibility(False, "FORBIDDEN", "当前用户无权催办该项目", work_order.current_handler_user_id, None, 0, 0, 0, 0, work_order.current_status)

    if not work_order.current_handler_user_id:
        return ReminderEligibility(False, "NO_HANDLER", "当前待办未指派到具体人员，暂不可催办", None, None, 0, 0, 0, 0, work_order.current_status)

    handler = db.query(User).filter(User.id == work_order.current_handler_user_id).first()
    if work_order.current_handler_user_id == current_user.id:
        return ReminderEligibility(False, "SELF_HANDLER", "当前待办人为自己，不能自己催自己", work_order.current_handler_user_id, handler.real_name if handler else None, 0, 0, 0, 0, work_order.current_status)

    last_action_at = get_last_effective_action_time(db, work_order)
    elapsed_seconds = max(0, int((now - last_action_at).total_seconds()))
    remaining_seconds_to_48h = max(0, int((REMIND_AFTER - (now - last_action_at)).total_seconds()))
    cycle_key = build_handler_cycle_key(work_order)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_remind_count = (
        db.query(ReminderEvent)
        .filter(
            ReminderEvent.work_order_id == work_order.id,
            ReminderEvent.current_handler_user_id == work_order.current_handler_user_id,
            ReminderEvent.handler_cycle_key == cycle_key,
            ReminderEvent.created_at >= start_of_day,
        )
        .count()
    )
    latest_reminder = (
        db.query(ReminderEvent)
        .filter(
            ReminderEvent.work_order_id == work_order.id,
            ReminderEvent.current_handler_user_id == work_order.current_handler_user_id,
            ReminderEvent.handler_cycle_key == cycle_key,
        )
        .order_by(ReminderEvent.created_at.desc(), ReminderEvent.id.desc())
        .first()
    )
    remaining_seconds_to_next_remind = 0
    if latest_reminder:
        remaining_seconds_to_next_remind = max(0, int((REMIND_COOLDOWN - (now - latest_reminder.created_at)).total_seconds()))

    if remaining_seconds_to_48h > 0:
        return ReminderEligibility(False, "NOT_OVERDUE", f"当前待办人最近一次有效操作距今 {elapsed_seconds // 3600} 小时，还需 {remaining_seconds_to_48h // 3600} 小时后才可催办", work_order.current_handler_user_id, handler.real_name if handler else None, elapsed_seconds, remaining_seconds_to_48h, today_remind_count, remaining_seconds_to_next_remind, work_order.current_status)
    if remaining_seconds_to_next_remind > 0:
        return ReminderEligibility(False, "COOLDOWN", "距上次催办未满6小时", work_order.current_handler_user_id, handler.real_name if handler else None, elapsed_seconds, 0, today_remind_count, remaining_seconds_to_next_remind, work_order.current_status)
    if today_remind_count >= MAX_REMINDS_PER_DAY:
        return ReminderEligibility(False, "DAILY_LIMIT", "今日对该处理人的催办已达3次上限，请明天再试", work_order.current_handler_user_id, handler.real_name if handler else None, elapsed_seconds, 0, today_remind_count, 0, work_order.current_status)
    return ReminderEligibility(True, None, None, work_order.current_handler_user_id, handler.real_name if handler else None, elapsed_seconds, 0, today_remind_count, 0, work_order.current_status)
