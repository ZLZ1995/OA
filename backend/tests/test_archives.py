from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.print_room_record import PrintRoomRecord
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.schemas.archive import ArchiveSubmitRequest
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


def test_offline_archive_submission_routes_to_selected_archive_manager() -> None:
    from app.api.v1.archives import submit_archive
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    archive_role = _seed_role(db, "ARCHIVE_MANAGER", "档案管理员")
    leader = _seed_user(db, "leader", [leader_role])
    archive_manager = _seed_user(db, "libiao", [archive_role])

    project = Project(
        project_code="ZQ-TEST-ARCHIVE",
        project_name="Archive Demo",
        client_name="Client",
        business_user_id=leader.id,
        project_leader_id=leader.id,
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no="WO-ARCHIVE",
        project_id=project.id,
        title="WO",
        current_status=WorkOrderStatus.WAIT_ARCHIVE_SUBMIT.value,
        current_handler_user_id=leader.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.flush()
    db.add(
        PrintRoomRecord(
            work_order_id=work_order.id,
            handled_by=leader.id,
            paper_report_no="R-ARCHIVE-001",
            copy_count=1,
        )
    )
    db.commit()

    submit_archive(
        payload=ArchiveSubmitRequest(
            work_order_id=work_order.id,
            reviewer_user_id=archive_manager.id,
            submission_type="OFFLINE",
        ),
        db=db,
        current_user=leader,
    )

    db.refresh(work_order)
    result = get_workbench(db=db, current_user=archive_manager)

    assert work_order.current_status == WorkOrderStatus.ARCHIVE_REVIEWING.value
    assert work_order.current_handler_user_id == archive_manager.id
    assert work_order.archive_reviewer_id == archive_manager.id
    assert work_order.archive_submission_type == "OFFLINE"
    assert [item.id for item in result.todo_projects] == [project.id]
    assert result.todo_projects[0].current_step == "底稿审核"


def test_archive_submit_requires_print_room_issue_completed() -> None:
    from fastapi import HTTPException
    from app.api.v1.archives import submit_archive

    db = _build_session()
    leader_role = _seed_role(db, "PROJECT_LEADER", "项目负责人")
    archive_role = _seed_role(db, "ARCHIVE_MANAGER", "档案管理员")
    leader = _seed_user(db, "leader", [leader_role])
    archive_manager = _seed_user(db, "libiao", [archive_role])

    project = Project(
        project_code="ZQ-TEST-ARCHIVE-GUARD",
        project_name="Archive Guard Demo",
        client_name="Client",
        business_user_id=leader.id,
        project_leader_id=leader.id,
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no="WO-ARCHIVE-GUARD",
        project_id=project.id,
        title="WO",
        current_status=WorkOrderStatus.WAIT_ARCHIVE_SUBMIT.value,
        current_handler_user_id=leader.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.commit()

    try:
        submit_archive(
            payload=ArchiveSubmitRequest(
                work_order_id=work_order.id,
                reviewer_user_id=archive_manager.id,
                submission_type="ONLINE",
            ),
            db=db,
            current_user=leader,
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "未完成文印" in exc.detail
    else:
        raise AssertionError("expected archive submission to be blocked before print room issue")

    db.add(
        PrintRoomRecord(
            work_order_id=work_order.id,
            handled_by=leader.id,
            paper_report_no="R-GUARD-001",
            copy_count=1,
        )
    )
    db.commit()

    result = submit_archive(
        payload=ArchiveSubmitRequest(
            work_order_id=work_order.id,
            reviewer_user_id=archive_manager.id,
            submission_type="ONLINE",
        ),
        db=db,
        current_user=leader,
    )

    assert result["message"] == "已提交底稿，待审查"
