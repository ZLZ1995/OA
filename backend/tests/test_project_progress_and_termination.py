from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_user(db: Session, username: str = "leader") -> User:
    user = User(username=username, password_hash="x", real_name=username.title(), is_active=True)
    db.add(user)
    db.flush()
    return user


def _seed_role_user(db: Session, username: str, role_code: str) -> User:
    user = _seed_user(db, username)
    role = db.query(Role).filter(Role.code == role_code).first()
    if not role:
        role = Role(code=role_code, name=role_code, description="", is_system_fixed=True)
        db.add(role)
        db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    return user


def _seed_project(
    db: Session,
    leader: User,
    *,
    project_code: str,
    termination_status: str | None = None,
    current_status: str = "PAPER_REPORT_ISSUED",
) -> tuple[Project, WorkOrder]:
    project = Project(
        project_code=project_code,
        project_name="Demo",
        client_name="Client",
        business_user_id=leader.id,
        project_leader_id=leader.id,
        project_amount=1000,
        termination_status=termination_status,
        termination_reason="reason" if termination_status else None,
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no=f"WO-{project.id}",
        project_id=project.id,
        title="WO",
        current_status=current_status,
        current_handler_user_id=leader.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.commit()
    return project, work_order


def test_project_export_includes_progress_labels() -> None:
    from app.api.v1.project_exports import _collect_rows

    db = _build_session()
    leader = _seed_user(db)
    active_project, _ = _seed_project(db, leader, project_code="P-ACTIVE")
    archived_project, _ = _seed_project(db, leader, project_code="P-ARCHIVED")
    archived_project.archived_at = active_project.created_at
    voided_project, _ = _seed_project(db, leader, project_code="P-VOIDED", termination_status="APPROVED")
    db.commit()

    rows = _collect_rows(db, None, None, None, None, None, None, None, None, None, None)
    progress_by_no = {row["project_no"]: row["project_progress"] for row in rows}

    assert progress_by_no[active_project.project_code] == "纸质报告已出具，待邮寄"
    assert progress_by_no[archived_project.project_code] == "已归档"
    assert progress_by_no[voided_project.project_code] == "已作废"


def test_project_export_displays_specific_review_submit_progress() -> None:
    from app.api.v1.project_exports import _collect_rows

    db = _build_session()
    leader = _seed_user(db)
    contract_approved, _ = _seed_project(
        db,
        leader,
        project_code="P-CONTRACT-APPROVED",
        current_status="CONTRACT_APPROVED",
    )
    wait_first, _ = _seed_project(
        db,
        leader,
        project_code="P-WAIT-FIRST",
        current_status="WAIT_FIRST_REVIEW_SUBMIT",
    )
    first_rejected, _ = _seed_project(
        db,
        leader,
        project_code="P-FIRST-REJECTED",
        current_status="FIRST_REVIEW_REJECTED",
    )

    rows = _collect_rows(db, None, None, None, None, None, None, None, None, None, None)
    progress_by_no = {row["project_no"]: row["project_progress"] for row in rows}

    assert progress_by_no[contract_approved.project_code] == "合同审核通过，待上传待审报告"
    assert progress_by_no[wait_first.project_code] == "待提交一审"
    assert progress_by_no[first_rejected.project_code] == "一审退回待回复"


def test_approved_termination_is_excluded_from_todo_projects() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    approved_project, _ = _seed_project(db, leader, project_code="P-APPROVED", termination_status="APPROVED")

    result = get_workbench(db=db, current_user=leader)

    assert approved_project.id not in [item.id for item in result.todo_projects]


def test_admin_sees_pending_termination_todo() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    admin = _seed_user(db, "admin")
    admin_role = Role(code="ADMIN", name="管理员", description="", is_system_fixed=True)
    db.add(admin_role)
    db.flush()
    db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    pending_project, _ = _seed_project(db, leader, project_code="P-PENDING", termination_status="PENDING")
    db.commit()

    result = get_workbench(db=db, current_user=admin)

    assert [item.id for item in result.todo_projects] == [pending_project.id]
    assert result.todo_projects[0].can_approve_termination is True


def test_print_room_mailing_todo_clears_after_express_submitted() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    print_room = _seed_user(db, "printroom")
    print_room_role = Role(code="PRINT_ROOM", name="文印室", description="", is_system_fixed=True)
    db.add(print_room_role)
    db.flush()
    db.add(UserRole(user_id=print_room.id, role_id=print_room_role.id))
    project, work_order = _seed_project(db, leader, project_code="P-MAIL-PRINTROOM")
    work_order.current_status = "REPORT_MAILING"
    work_order.current_handler_user_id = leader.id
    work_order.print_room_handler_id = print_room.id
    work_order.mailing_handler_user_id = print_room.id
    work_order.mailing_status = "PROJECT_CONFIRMING"
    db.commit()

    result = get_workbench(db=db, current_user=print_room)

    assert result.todo_projects == []


def test_project_party_todo_moves_to_archive_after_mailing_confirmed() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    project, work_order = _seed_project(db, leader, project_code="P-MAIL-ARCHIVE")
    work_order.current_status = "WAIT_ARCHIVE_SUBMIT"
    work_order.current_handler_user_id = leader.id
    work_order.mailing_status = "COMPLETED"
    db.commit()

    result = get_workbench(db=db, current_user=leader)

    assert [item.id for item in result.todo_projects] == [project.id]
    assert result.todo_projects[0].current_step == "报告归档"


def test_legacy_mailing_completed_todo_displays_archive_step() -> None:
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db)
    project, work_order = _seed_project(db, leader, project_code="P-LEGACY-MAIL")
    work_order.current_status = "REPORT_MAILING_COMPLETED"
    work_order.current_handler_user_id = leader.id
    work_order.mailing_status = "COMPLETED"
    db.commit()

    result = get_workbench(db=db, current_user=leader)

    assert [item.id for item in result.todo_projects] == [project.id]
    assert result.todo_projects[0].current_step == "报告归档"
