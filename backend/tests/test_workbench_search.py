from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.v1.workbench import router, search_workbench_projects
from app.db.base import Base
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.workflow_log import WorkflowLog


@pytest.fixture
def data():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        me = User(username="me", password_hash="x", real_name="张三", is_active=True)
        other = User(username="other", password_hash="x", real_name="李四", is_active=True)
        db.add_all([me, other])
        db.flush()
        projects = {}
        for kind in ("created", "leader", "member", "history", "unrelated", "deleted"):
            project = Project(project_code=f"ZQ-{kind}", project_name=f"评估{kind}", client_name="测试客户",
                              business_user_id=me.id if kind in {"created", "deleted"} else other.id,
                              project_leader_id=me.id if kind == "leader" else other.id,
                              archived_at=datetime.now() if kind == "history" else None,
                              deleted_at=datetime.now() if kind == "deleted" else None)
            db.add(project)
            db.flush()
            projects[kind] = project
        db.add(ProjectMember(project_id=projects["member"].id, user_id=me.id, member_role="MEMBER"))
        order = WorkOrder(work_order_no="history", project_id=projects["history"].id, title="历史项目",
                          current_status="ARCHIVED", initiator_user_id=other.id, project_leader_id=other.id,
                          current_handler_user_id=other.id)
        db.add(order)
        db.flush()
        for _ in range(2):
            db.add(WorkflowLog(work_order_id=order.id, from_status="FIRST_REVIEWING", to_status="SECOND_REVIEWING",
                               action_type="APPROVE", operator_user_id=me.id))
        db.commit()
        yield db, me, projects
    engine.dispose()


def test_scope_includes_members_and_historical_operators_without_duplicates(data):
    db, me, projects = data
    result = search_workbench_projects(db=db, current_user=me)
    assert {row.id for row in result.items} == {projects[k].id for k in ("created", "leader", "member", "history")}
    assert result.total == 4
    history = next(row for row in result.items if row.id == projects["history"].id)
    assert history.current_step == "已归档"
    assert history.todo_action == "无待办"
    assert history.can_enter is False  # Searching does not grant revoked flow permissions.


def test_admin_search_does_not_expand_to_unrelated_projects(data):
    db, me, projects = data
    role = Role(code="ADMIN", name="管理员", is_system_fixed=True)
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=me.id, role_id=role.id))
    db.commit()
    result = search_workbench_projects(keyword="ZQ-unrelated", db=db, current_user=me)
    assert result.total == 0


@pytest.mark.parametrize("filters, expected", [
    ({"keyword": " 张三 "}, ["created"]),
    ({"project_no": "CREATED"}, ["created"]),
    ({"project_name": "评估history", "client_name": "测试", "creator": "李四"}, ["history"]),
    ({"keyword": "history", "creator": "张三"}, []),
    ({"keyword": "%"}, []),
    ({"keyword": "_"}, []),
    ({"keyword": "deleted"}, []),
    ({"keyword": "unrelated"}, []),
])
def test_search_matching_and_security(data, filters, expected):
    db, me, projects = data
    result = search_workbench_projects(db=db, current_user=me, **filters)
    assert {row.id for row in result.items} == {projects[k].id for k in expected}


def test_pagination_has_stable_order_and_total(data):
    db, me, _ = data
    first = search_workbench_projects(page=1, page_size=2, db=db, current_user=me)
    second = search_workbench_projects(page=2, page_size=2, db=db, current_user=me)
    assert first.total == second.total == 4
    assert len(first.items) == len(second.items) == 2
    assert min(row.id for row in first.items) > max(row.id for row in second.items)
    assert search_workbench_projects(page=3, page_size=2, db=db, current_user=me).items == []


def test_http_search_validation_and_authentication(data):
    db, me, _ = data
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        assert client.get("/workbench/projects/search").status_code in (401, 403)
        app.dependency_overrides[get_current_user] = lambda: me
        response = client.get("/workbench/projects/search", params={"creator": "张三"})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        for params in ({"page": 0}, {"page_size": 101}, {"keyword": "x" * 201}):
            assert client.get("/workbench/projects/search", params=params).status_code == 422
