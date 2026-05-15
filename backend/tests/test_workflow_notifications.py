from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.notifications import list_my_notifications
from app.db.base import Base
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_notification import UserNotification
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.workflow_log import WorkflowLog
from app.services.workflow_notification_service import send_workflow_notification


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_user(db: Session, username: str, role_codes: list[str]) -> User:
    user = User(username=username, password_hash="x", real_name=username.title(), is_active=True)
    db.add(user)
    db.flush()
    for role_code in role_codes:
        role = db.query(Role).filter(Role.code == role_code).first()
        if role is None:
            role = Role(code=role_code, name=role_code, description="", is_system_fixed=True)
            db.add(role)
            db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    return user


def test_workflow_notification_ccs_members_when_leader_is_receiver() -> None:
    db = _build_session()
    sender = _seed_user(db, "sender", ["FIRST_REVIEWER"])
    leader = _seed_user(db, "leader", ["PROJECT_LEADER"])
    member = _seed_user(db, "member", ["PROJECT_MEMBER"])
    project = Project(
        project_code="P-WF",
        undertaking_unit="中勤",
        project_name="Workflow",
        client_name="Client",
        report_type="评估报告",
        business_salesman="Sales",
        business_user_id=sender.id,
        project_leader_id=leader.id,
        project_source="INTERNAL",
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=member.id, member_role="MEMBER"))
    work_order = WorkOrder(
        work_order_no="WO-WF",
        project_id=project.id,
        title="Workflow Order",
        current_status="WAIT_SECOND_REVIEW_SUBMIT",
        current_handler_user_id=leader.id,
        initiator_user_id=sender.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.flush()

    send_workflow_notification(
        db,
        project=project,
        work_order=work_order,
        sender_user=sender,
        receiver_user_id=leader.id,
        action_name="FIRST_APPROVE",
    )
    db.commit()

    rows = db.query(UserNotification).order_by(UserNotification.id.asc()).all()
    assert len(rows) == 2
    assert rows[0].user_id == leader.id
    assert rows[0].cc_flag is False
    assert rows[0].message_type == "WORKFLOW"
    assert rows[0].title == "请处理二审流程"
    assert rows[1].user_id == member.id
    assert rows[1].cc_flag is True
    assert rows[1].message_type == "WORKFLOW"
    assert rows[1].title == "一审已完成"


def test_workflow_notification_skips_self_transfer() -> None:
    db = _build_session()
    user = _seed_user(db, "leader", ["PROJECT_LEADER"])
    project = Project(
        project_code="P-WF-SELF",
        undertaking_unit="中勤",
        project_name="Workflow",
        client_name="Client",
        report_type="评估报告",
        business_salesman="Sales",
        business_user_id=user.id,
        project_leader_id=user.id,
        project_source="INTERNAL",
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no="WO-WF-SELF",
        project_id=project.id,
        title="Workflow Order",
        current_status="WAIT_CONTRACT_UPLOAD",
        current_handler_user_id=user.id,
        initiator_user_id=user.id,
        project_leader_id=user.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.flush()

    send_workflow_notification(
        db,
        project=project,
        work_order=work_order,
        sender_user=user,
        receiver_user_id=user.id,
        action_name="WAIT_CONTRACT_UPLOAD_ASSIGNED",
    )
    db.commit()

    assert db.query(UserNotification).count() == 0


def test_workflow_notification_stays_read_not_processed() -> None:
    db = _build_session()
    user = _seed_user(db, "leader", ["PROJECT_LEADER"])
    project = Project(
        project_code="P-WF-2",
        undertaking_unit="中勤",
        project_name="Workflow",
        client_name="Client",
        report_type="评估报告",
        business_salesman="Sales",
        business_user_id=user.id,
        project_leader_id=user.id,
        project_source="INTERNAL",
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no="WO-WF-2",
        project_id=project.id,
        title="Workflow Order",
        current_status="CONTRACT_REVIEWING",
        current_handler_user_id=user.id,
        initiator_user_id=user.id,
        project_leader_id=user.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.flush()
    log = WorkflowLog(
        work_order_id=work_order.id,
        from_status="WAIT_CONTRACT_REVIEW_SUBMIT",
        to_status="CONTRACT_REVIEWING",
        action_type="SUBMIT_CONTRACT_REVIEW",
        operator_user_id=user.id,
        remark="submit",
    )
    db.add(log)
    db.flush()
    notification = UserNotification(
        user_id=user.id,
        biz_type="WORKFLOW_TRANSFER",
        biz_id=log.id,
        title="workflow",
        content="workflow content",
        message_type="WORKFLOW",
        priority="NORMAL",
        sender_user_id=user.id,
        project_id=project.id,
        work_order_id=work_order.id,
        process_status="PENDING",
        cc_flag=False,
        group_key=f"WORK_ORDER:{work_order.id}",
        is_read=True,
        popup_flag=True,
    )
    db.add(notification)
    db.commit()

    result = list_my_notifications(
        tab="all",
        keyword=None,
        message_type="WORKFLOW",
        priority=None,
        read_status=None,
        project_id=None,
        work_order_id=None,
        page=1,
        page_size=20,
        db=db,
        current_user=user,
    )

    assert result.total == 1
    assert result.items[0].process_status == "READ"


def test_workflow_notification_uses_new_titles_and_fallback() -> None:
    db = _build_session()
    sender = _seed_user(db, "sender", ["PROJECT_LEADER"])
    receiver = _seed_user(db, "receiver", ["FINANCE"])
    project = Project(
        project_code="P-WF-3",
        undertaking_unit="中勤",
        project_name="Workflow",
        client_name="Client",
        report_type="评估报告",
        business_salesman="Sales",
        business_user_id=sender.id,
        project_leader_id=sender.id,
        project_source="INTERNAL",
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no="WO-WF-3",
        project_id=project.id,
        title="Workflow Order",
        current_status="INVOICE_PROCESSING",
        current_handler_user_id=receiver.id,
        initiator_user_id=sender.id,
        project_leader_id=sender.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.flush()

    send_workflow_notification(
        db,
        project=project,
        work_order=work_order,
        sender_user=sender,
        receiver_user_id=receiver.id,
        action_name="FINANCE_COMPLETE_INVOICE",
    )
    send_workflow_notification(
        db,
        project=project,
        work_order=work_order,
        sender_user=sender,
        receiver_user_id=receiver.id,
        action_name="UNKNOWN_ACTION",
    )
    db.commit()

    rows = db.query(UserNotification).order_by(UserNotification.id.asc()).all()
    assert rows[0].title == "请核对并确认开票"
    assert rows[1].title == "请处理流程任务"
