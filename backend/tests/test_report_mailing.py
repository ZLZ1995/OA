from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.schemas.report_mailing import ReportMailingSubmitRequest
from app.workflows.states import WorkOrderStatus


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_role(db: Session, code: str, name: str) -> Role:
    role = Role(code=code, name=name, description="", is_system_fixed=True)
    db.add(role)
    db.flush()
    return role


def _seed_user(db: Session, username: str, roles: list[Role]) -> User:
    user = User(username=username, password_hash="x", real_name=username, is_active=True)
    db.add(user)
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    return user


def test_submit_report_mailing_moves_to_print_room_pending() -> None:
    from app.api.v1.report_mailing import submit_report_mailing

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    print_room_role = _seed_role(db, "PRINT_ROOM", "文印室")
    leader = _seed_user(db, "leader", [leader_role])
    print_room = _seed_user(db, "printroom", [print_room_role])

    project = Project(
        project_code="P-MAIL",
        undertaking_unit="中勤",
        project_name="Mail Demo",
        client_name="Client",
        report_type="评估报告",
        business_salesman="Sales",
        business_user_id=leader.id,
        project_leader_id=leader.id,
        project_source="INTERNAL",
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=leader.id))
    work_order = WorkOrder(
        work_order_no="WO-MAIL",
        project_id=project.id,
        title="WO",
        current_status=WorkOrderStatus.REPORT_MAILING.value,
        current_handler_user_id=leader.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        print_room_handler_id=print_room.id,
        mailing_status="PROJECT_EDITING",
    )
    db.add(work_order)
    db.commit()
    db.refresh(work_order)

    row = submit_report_mailing(
        work_order_id=work_order.id,
        payload=ReportMailingSubmitRequest(
            receiver_name="张三",
            receiver_phone="13800138000",
            receiver_address="测试地址",
            receiver_remark="测试备注",
        ),
        db=db,
        current_user=leader,
    )

    db.refresh(work_order)
    assert row.action_type == "SUBMIT_MAILING"
    assert work_order.current_status == WorkOrderStatus.REPORT_MAILING.value
    assert work_order.mailing_status == "PRINT_ROOM_PENDING"
    assert work_order.current_handler_user_id == print_room.id
