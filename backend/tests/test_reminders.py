from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.workflow_log import WorkflowLog
from app.models.work_order import WorkOrder
from app.services.reminder_policy import evaluate_reminder_eligibility
from app.services.reminder_service import create_reminder


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_role(db: Session, code: str) -> Role:
    role = db.query(Role).filter(Role.code == code).first()
    if role:
        return role
    role = Role(code=code, name=code, description="", is_system_fixed=True)
    db.add(role)
    db.flush()
    return role


def _seed_user(db: Session, username: str, role_codes: list[str]) -> User:
    user = User(username=username, password_hash="x", real_name=username, is_active=True)
    db.add(user)
    db.flush()
    for code in role_codes:
        role = _seed_role(db, code)
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    return user


def _seed_project_bundle(db: Session) -> tuple[Project, WorkOrder, User, User, User]:
    leader = _seed_user(db, "leader", ["PROJECT_LEADER"])
    member = _seed_user(db, "member", ["PROJECT_MEMBER"])
    handler = _seed_user(db, "handler", ["FIRST_REVIEWER"])
    project = Project(
        project_code="P-REMIND",
        project_name="Reminder Demo",
        client_name="Client",
        business_user_id=leader.id,
        project_leader_id=leader.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=member.id, member_role="MEMBER"))
    work_order = WorkOrder(
        work_order_no="WO-REMIND",
        project_id=project.id,
        title="Reminder Work Order",
        current_status="FIRST_REVIEWING",
        current_handler_user_id=handler.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.flush()
    work_order.created_at = work_order.created_at - timedelta(hours=49)
    work_order.updated_at = work_order.updated_at - timedelta(hours=49)
    db.add(
        WorkflowLog(
            work_order_id=work_order.id,
            from_status="WAIT_FIRST_REVIEW_SUBMIT",
            to_status="FIRST_REVIEWING",
            action_type="SUBMIT_FIRST",
            operator_user_id=leader.id,
        )
    )
    db.flush()
    latest_log = db.query(WorkflowLog).filter(WorkflowLog.work_order_id == work_order.id).order_by(WorkflowLog.id.desc()).first()
    latest_log.created_at = latest_log.created_at - timedelta(hours=49)
    return project, work_order, leader, member, handler


def test_reminder_eligibility_requires_48_hours() -> None:
    db = _build_session()
    project, work_order, leader, _, _ = _seed_project_bundle(db)
    latest_log = db.query(WorkflowLog).filter(WorkflowLog.work_order_id == work_order.id).order_by(WorkflowLog.id.desc()).first()
    latest_log.created_at = latest_log.created_at + timedelta(hours=10)
    db.commit()

    result = evaluate_reminder_eligibility(db, work_order=work_order, project=project, current_user=leader)

    assert result.can_remind is False
    assert result.reason_code == "NOT_OVERDUE"


def test_project_member_can_create_reminder_and_notify_leader() -> None:
    from app.models.reminder_receipt import ReminderReceipt
    from app.models.user_notification import UserNotification

    db = _build_session()
    project, work_order, leader, member, _ = _seed_project_bundle(db)
    event = create_reminder(db, project=project, work_order=work_order, current_user=member, comment="请尽快处理")

    receipts = db.query(ReminderReceipt).filter(ReminderReceipt.reminder_event_id == event.id).all()
    notifications = db.query(UserNotification).filter(UserNotification.biz_id == event.id).all()

    assert event.day_remind_seq == 1
    assert len(receipts) == 2
    assert len(notifications) == 2
    assert any(row.receiver_user_id == leader.id and row.receiver_type == "CC" for row in receipts)


def test_same_user_cannot_remind_self() -> None:
    db = _build_session()
    project, work_order, leader, _, _ = _seed_project_bundle(db)
    work_order.current_handler_user_id = leader.id
    db.commit()

    result = evaluate_reminder_eligibility(db, work_order=work_order, project=project, current_user=leader)

    assert result.can_remind is False
    assert result.reason_code == "SELF_HANDLER"
