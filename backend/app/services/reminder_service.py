from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.reminder_event import ReminderEvent
from app.models.reminder_receipt import ReminderReceipt
from app.models.user import User
from app.models.work_order import WorkOrder
from app.services.notification_service import create_notification
from app.services.reminder_policy import build_handler_cycle_key, evaluate_reminder_eligibility


def create_reminder(
    db: Session,
    *,
    project: Project,
    work_order: WorkOrder,
    current_user: User,
    comment: str | None = None,
) -> ReminderEvent:
    eligibility = evaluate_reminder_eligibility(db, work_order=work_order, project=project, current_user=current_user)
    if not eligibility.can_remind:
        raise ValueError(eligibility.reason_message or "当前不可催办")

    role_codes = {item.role.code for item in current_user.roles}
    initiator_role_type = "PROJECT_LEADER" if project.project_leader_id == current_user.id else "PROJECT_MEMBER"
    if "ADMIN" in role_codes and initiator_role_type not in {"PROJECT_LEADER", "PROJECT_MEMBER"}:
        initiator_role_type = "ADMIN"

    event = ReminderEvent(
        project_id=project.id,
        work_order_id=work_order.id,
        current_handler_user_id=work_order.current_handler_user_id,
        initiator_user_id=current_user.id,
        initiator_role_type=initiator_role_type,
        trigger_type="MANUAL",
        current_status=work_order.current_status,
        overdue_seconds=eligibility.elapsed_seconds,
        comment=comment,
        day_remind_seq=eligibility.today_remind_count + 1,
        handler_cycle_key=build_handler_cycle_key(work_order),
    )
    db.add(event)
    db.flush()

    primary_receipt = ReminderReceipt(
        reminder_event_id=event.id,
        receiver_user_id=work_order.current_handler_user_id,
        receiver_type="PRIMARY",
        channel="IN_APP",
        delivery_status="SENT",
        read_status="UNREAD",
    )
    db.add(primary_receipt)

    handler_content = (
        f"{current_user.real_name}催办你尽快处理工单【{work_order.work_order_no}】\n"
        f"项目：{project.project_name}\n"
        f"当前节点：{work_order.current_status}\n"
        f"已超过 {eligibility.elapsed_seconds // 3600} 小时未发生业务操作"
    )
    if comment:
        handler_content = f"{handler_content}\n补充说明：{comment}"

    create_notification(
        db,
        user_id=work_order.current_handler_user_id,
        biz_type="WORK_ORDER_REMINDER",
        biz_id=event.id,
        title="你有一条工单催办提醒",
        content=handler_content,
        message_type="REMINDER",
        priority="IMPORTANT",
        sender_user_id=current_user.id,
        project_id=project.id,
        work_order_id=work_order.id,
        process_status="PENDING",
        cc_flag=False,
        group_key=f"WORK_ORDER:{work_order.id}",
        link_type="PROJECT",
        link_target_id=project.id,
    )

    if project.project_leader_id and project.project_leader_id != current_user.id:
        leader_receipt = ReminderReceipt(
            reminder_event_id=event.id,
            receiver_user_id=project.project_leader_id,
            receiver_type="CC",
            channel="IN_APP",
            delivery_status="SENT",
            read_status="UNREAD",
        )
        db.add(leader_receipt)
        create_notification(
            db,
            user_id=project.project_leader_id,
            biz_type="WORK_ORDER_REMINDER",
            biz_id=event.id,
            title="项目催办同步通知",
            content=f"{current_user.real_name}已对工单【{work_order.work_order_no}】当前处理人发起催办",
            message_type="REMINDER",
            priority="NORMAL",
            sender_user_id=current_user.id,
            project_id=project.id,
            work_order_id=work_order.id,
            process_status="PENDING",
            cc_flag=True,
            group_key=f"WORK_ORDER:{work_order.id}",
            link_type="PROJECT",
            link_target_id=project.id,
        )

    db.commit()
    db.refresh(event)
    return event
