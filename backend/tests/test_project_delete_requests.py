from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.project import Project
from app.models.project_delete_request import ProjectDeleteRequest
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.schemas.project_delete import ProjectDeleteRequestCreate


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _seed_user(db: Session, username: str, roles: list[str] | None = None) -> User:
    user = User(username=username, password_hash="x", real_name=username, is_active=True)
    db.add(user)
    db.flush()
    for code in roles or []:
        role = db.query(Role).filter(Role.code == code).first()
        if not role:
            role = Role(code=code, name=code, description="", is_system_fixed=True)
            db.add(role)
            db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    return user


def _seed_project(db: Session, leader: User, *, status: str = "WAIT_PRINT_ROOM") -> tuple[Project, WorkOrder]:
    project = Project(
        project_code=f"P-{status}",
        project_name="待删项目",
        client_name="客户",
        business_user_id=leader.id,
        project_leader_id=leader.id,
    )
    db.add(project)
    db.flush()
    work_order = WorkOrder(
        work_order_no=f"WO-{project.id}",
        project_id=project.id,
        title="工单",
        current_status=status,
        current_handler_user_id=leader.id,
        initiator_user_id=leader.id,
        project_leader_id=leader.id,
        priority="MEDIUM",
    )
    db.add(work_order)
    db.commit()
    return project, work_order


def test_project_owner_can_request_delete_after_report_issue() -> None:
    from app.api.v1.project_delete_requests import request_project_delete
    from app.api.v1.workbench import get_workbench

    db = _build_session()
    leader = _seed_user(db, "leader")
    approver = _seed_user(db, "admin", ["ADMIN"])
    project, _ = _seed_project(db, leader, status="THIRD_APPROVED_WAIT_PRINTROOM")

    result = request_project_delete(
        project_id=project.id,
        payload=ProjectDeleteRequestCreate(approver_user_id=approver.id, reason="测试数据"),
        db=db,
        current_user=leader,
    )

    db.refresh(project)
    assert result.status == "PENDING"
    assert result.current_step == "待确认删除"
    assert project.termination_status == "DELETE_PENDING"

    admin_workbench = get_workbench(db=db, current_user=approver)
    assert [item.id for item in admin_workbench.todo_projects] == [project.id]
    assert admin_workbench.todo_projects[0].current_step == "待确认删除"
    assert admin_workbench.todo_projects[0].can_approve_delete is True


def test_reject_then_reapply_overwrites_existing_request() -> None:
    from app.api.v1.project_delete_requests import reject_project_delete, request_project_delete

    db = _build_session()
    leader = _seed_user(db, "leader")
    approver = _seed_user(db, "admin", ["ADMIN"])
    project, _ = _seed_project(db, leader, status="THIRD_APPROVED_WAIT_PRINTROOM")

    first = request_project_delete(
        project_id=project.id,
        payload=ProjectDeleteRequestCreate(approver_user_id=approver.id, reason="第一次"),
        db=db,
        current_user=leader,
    )
    reject_project_delete(first.id, db=db, current_user=approver, _={"ADMIN"})

    second = request_project_delete(
        project_id=project.id,
        payload=ProjectDeleteRequestCreate(approver_user_id=approver.id, reason="第二次"),
        db=db,
        current_user=leader,
    )

    rows = db.query(ProjectDeleteRequest).filter(ProjectDeleteRequest.project_no == project.project_code).all()
    assert len(rows) == 1
    assert second.id == first.id
    assert second.status == "PENDING"
    assert second.reason == "第二次"


def test_pending_delete_request_cannot_be_repeated() -> None:
    from app.api.v1.project_delete_requests import request_project_delete

    db = _build_session()
    leader = _seed_user(db, "leader")
    approver = _seed_user(db, "admin", ["ADMIN"])
    project, _ = _seed_project(db, leader, status="THIRD_APPROVED_WAIT_PRINTROOM")

    payload = ProjectDeleteRequestCreate(approver_user_id=approver.id, reason=None)
    request_project_delete(project_id=project.id, payload=payload, db=db, current_user=leader)

    with pytest.raises(HTTPException) as exc:
        request_project_delete(project_id=project.id, payload=payload, db=db, current_user=leader)
    assert exc.value.status_code == 400
    assert "已有待确认删除申请" in exc.value.detail


def test_approve_deletes_project_but_keeps_request_summary() -> None:
    from app.api.v1.project_delete_requests import approve_project_delete, list_project_delete_requests, request_project_delete

    db = _build_session()
    leader = _seed_user(db, "leader")
    approver = _seed_user(db, "admin", ["ADMIN"])
    project, _ = _seed_project(db, leader, status="THIRD_APPROVED_WAIT_PRINTROOM")
    project_no = project.project_code

    row = request_project_delete(
        project_id=project.id,
        payload=ProjectDeleteRequestCreate(approver_user_id=approver.id, reason="清理"),
        db=db,
        current_user=leader,
    )
    approve_project_delete(row.id, db=db, current_user=approver, _={"ADMIN"})

    assert db.query(Project).filter(Project.project_code == project_no).first() is None
    approved_rows = list_project_delete_requests(status_filter="APPROVED", db=db, _={"ADMIN"}).items
    assert len(approved_rows) == 1
    assert approved_rows[0].project_id is None
    assert approved_rows[0].project_no == project_no
    assert approved_rows[0].current_step == "已删除"


def test_admin_export_allows_reapply_after_rejected_delete_request() -> None:
    from app.api.v1.project_exports import _collect_rows

    db = _build_session()
    leader = _seed_user(db, "leader")
    approver = _seed_user(db, "admin", ["ADMIN"])
    project, _ = _seed_project(db, leader, status="ARCHIVED")
    project.archived_at = datetime.now()
    db.add(
        ProjectDeleteRequest(
            project_id=project.id,
            project_no=project.project_code,
            project_name=project.project_name,
            client_name=project.client_name,
            current_step="已驳回",
            requester_user_id=leader.id,
            approver_user_id=approver.id,
            status="REJECTED",
            requested_at=datetime.now(),
        )
    )
    db.commit()

    rows = _collect_rows(db, None, None, None, None, None, None, None, None, None, None)

    assert rows[0]["delete_request_status"] == "REJECTED"
    assert rows[0]["can_admin_delete"] is True
