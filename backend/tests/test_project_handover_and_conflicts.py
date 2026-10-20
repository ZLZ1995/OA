from datetime import date, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.db.base import Base
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.project import Project
from app.models.work_order import WorkOrder
from app.models.project_member import ProjectMember
from app.models.project_conflict import ProjectConflictRecord
from app.models.project_handover import ProjectHandover, ProjectConflictEvaluation
from app.models.workflow_log import WorkflowLog
from app.models.work_order_file import WorkOrderFile
from app.services.project_handover import take_over, assign, legacy_preview
from app.services.project_conflicts import upsert_conflict_snapshot_and_detect, get_unresolved_conflicts, bootstrap_legacy_conflicts
from app.api.v1.project_conflicts import mark_not_conflict
from app.api.v1.projects import get_project_flow
from app.api.v1.users import delete_user, update_user
from app.schemas.user import UserUpdate


@pytest.fixture
def db():
    from sqlalchemy.pool import StaticPool
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        yield session
    engine.dispose()


def user(db, name, *codes):
    u = User(username=name, real_name=name, password_hash="x", is_active=True)
    db.add(u); db.flush()
    for code in codes:
        r = db.query(Role).filter_by(code=code).first()
        if not r:
            r = Role(code=code, name=code, is_system_fixed=True)
            db.add(r); db.flush()
        db.add(UserRole(user_id=u.id, role_id=r.id))
    db.flush()
    return u


def project(db, owner, code="P1"):
    p = Project(project_code=code, project_name=code, client_name="北京海淀供电实业开发有限公司",
                project_amount=100, valuation_base_date=date(2026, 10, 1), business_user_id=owner.id, project_leader_id=owner.id)
    db.add(p); db.flush()
    w = WorkOrder(work_order_no=code, project_id=p.id, title=code, current_status="WAIT_FIRST_REVIEW_SUBMIT",
                  current_handler_user_id=owner.id, initiator_user_id=owner.id, project_leader_id=owner.id)
    db.add(w); db.flush()
    return p, w


@pytest.mark.parametrize("via_patch", [True, False])
def test_disabling_transfers_owner_leader_and_keeps_history(db, via_patch):
    old, admin = user(db, "old"), user(db, "admin", "ADMIN")
    p, w = project(db, old)
    archived, _ = project(db, old, "ARCHIVED")
    archived.archived_at = datetime.now()
    ended, _ = project(db, old, "ENDED")
    ended.termination_status = "APPROVED"
    db.commit()
    if via_patch:
        update_user(old.id, UserUpdate(is_active=False), db, admin)
    else:
        delete_user(old.id, db, admin)
    assert not old.is_active
    assert p.business_user_id == p.project_leader_id == w.project_leader_id == w.current_handler_user_id == admin.id
    assert w.initiator_user_id == old.id
    assert w.current_status == "WAIT_FIRST_REVIEW_SUBMIT"
    assert archived.business_user_id == ended.business_user_id == old.id
    assert db.query(ProjectHandover).count() == 2
    assert db.query(WorkflowLog).count() == 2


def test_recovery_is_idempotent_and_preserves_other_reviewers_turn(db):
    old, admin, reviewer = user(db, "old"), user(db, "admin", "ADMIN"), user(db, "reviewer", "FIRST_REVIEWER")
    p, w = project(db, old)
    w.current_status, w.current_handler_user_id, w.first_reviewer_id = "FIRST_REVIEWING", reviewer.id, reviewer.id
    old.is_active = False
    db.commit()
    assert len(legacy_preview(db)) == 1
    take_over(db, old, admin); take_over(db, old, admin)
    assert db.query(ProjectHandover).count() == 2
    assert w.current_handler_user_id == reviewer.id
    assert not legacy_preview(db)
    new = user(db, "new")
    creator = db.query(ProjectHandover).filter_by(duty="CREATOR").one()
    assign(db, creator.id, new.id, admin, "交接")
    assert p.business_user_id == new.id
    assert w.current_handler_user_id == reviewer.id
    with pytest.raises(HTTPException) as exc:
        assign(db, creator.id, new.id, admin, "重复请求")
    assert exc.value.status_code == 409


def test_review_reassignment_checks_roles_and_avoidance(db):
    owner, old, admin = user(db, "owner"), user(db, "old", "FIRST_REVIEWER"), user(db, "admin", "ADMIN")
    p, w = project(db, owner)
    w.first_reviewer_id, w.current_handler_user_id, w.current_status = old.id, old.id, "FIRST_REVIEWING"
    old.is_active = False
    db.flush()
    task = take_over(db, old, admin)[0]
    assert w.current_handler_user_id == admin.id
    with pytest.raises(HTTPException):
        assign(db, task.id, admin.id, admin, "没有审核角色")
    new = user(db, "new", "FIRST_REVIEWER")
    assign(db, task.id, new.id, admin, "重新指定审核人")
    assert w.first_reviewer_id == w.current_handler_user_id == new.id
    assert w.current_status == "FIRST_REVIEWING"


def test_not_conflict_survives_repeated_detection_and_personnel_changes(db):
    a, b, admin = user(db, "a"), user(db, "b"), user(db, "admin", "ADMIN")
    p, w = project(db, a); q, v = project(db, b, "P2")
    upsert_conflict_snapshot_and_detect(db, p, w, datetime.now())
    upsert_conflict_snapshot_and_detect(db, q, v, datetime.now())
    db.commit()
    record = db.query(ProjectConflictRecord).one()
    mark_not_conflict(record.id, db, admin)
    p.business_user_id = admin.id
    for _ in range(3):
        upsert_conflict_snapshot_and_detect(db, p, w, datetime.now())
        upsert_conflict_snapshot_and_detect(db, q, v, datetime.now())
    assert not get_unresolved_conflicts(db, p.id)
    assert db.query(ProjectConflictRecord).count() == 1
    # Material business changes require a new decision.
    p.project_amount = q.project_amount = 200
    upsert_conflict_snapshot_and_detect(db, p, w, datetime.now())
    upsert_conflict_snapshot_and_detect(db, q, v, datetime.now())
    assert len(get_unresolved_conflicts(db, p.id)) == 1
    assert db.query(ProjectConflictEvaluation).count() == 2


def test_old_pending_decision_cannot_apply_to_changed_business_evidence(db):
    from app.api.v1.project_conflicts import _query_conflicts
    a, b, admin = user(db, "a"), user(db, "b"), user(db, "admin", "ADMIN")
    p, w = project(db, a)
    q, v = project(db, b, "P2")
    upsert_conflict_snapshot_and_detect(db, p, w, datetime.now())
    upsert_conflict_snapshot_and_detect(db, q, v, datetime.now())
    db.commit()
    old = db.query(ProjectConflictRecord).one()
    p.project_amount = 300
    upsert_conflict_snapshot_and_detect(db, p, w, datetime.now())
    db.commit()
    assert not _query_conflicts(db, "PENDING")
    with pytest.raises(HTTPException) as exc:
        mark_not_conflict(old.id, db, admin)
    assert exc.value.status_code == 409
    assert old.status == "PENDING"


def test_flow_read_does_not_create_phantom_conflicts(db):
    a, b = user(db, "a"), user(db, "b")
    p, w = project(db, a); q, v = project(db, b, "P2")
    upsert_conflict_snapshot_and_detect(db, q, v, datetime.now())
    db.add(WorkOrderFile(work_order_id=w.id, file_category="CONTRACT_DRAFT", business_stage="CONTRACT_DRAFT",
                        origin_file_name="contract.pdf", storage_key="unused", uploaded_by=a.id,
                        version_no=1, is_current=True, file_size=1, uploaded_at=datetime.now()))
    db.commit()
    for _ in range(2):
        flow = get_project_flow(p.id, db, a)
        assert not flow.review_submit_locked
    assert not db.new
    assert db.query(ProjectConflictRecord).count() == 0


def test_legacy_not_conflict_supersedes_generated_pending_duplicate(db):
    a, b = user(db, "a"), user(db, "b")
    p, w = project(db, a); q, v = project(db, b, "P2")
    upsert_conflict_snapshot_and_detect(db, p, w, datetime.now())
    upsert_conflict_snapshot_and_detect(db, q, v, datetime.now())
    r = db.query(ProjectConflictRecord).one()
    db.query(ProjectConflictEvaluation).delete()
    r.status, r.decision, r.decided_at = "RESOLVED", "NOT_CONFLICT", datetime.now()
    db.add(ProjectConflictRecord(project_a_id=p.id, project_b_id=q.id, snapshot_a_id=r.snapshot_a_id, snapshot_b_id=r.snapshot_b_id, status="PENDING"))
    db.flush()
    bootstrap_legacy_conflicts(db)
    assert not get_unresolved_conflicts(db, p.id)
    assert db.query(ProjectConflictRecord).count() == 2


def test_distinct_conflicts_are_independent_and_keeper_can_continue(db):
    a, b, c, admin = user(db, "a"), user(db, "b"), user(db, "c"), user(db, "admin", "ADMIN")
    for owner, code in ((a, "P1"), (b, "P2"), (c, "P3")):
        p, w = project(db, owner, code)
        upsert_conflict_snapshot_and_detect(db, p, w, datetime.now())
    db.commit()
    p = db.query(Project).filter_by(project_code="P1").one()
    records = get_unresolved_conflicts(db, p.id)
    assert len(records) == 2
    mark_not_conflict(records[0].id, db, admin)
    assert len(get_unresolved_conflicts(db, p.id)) == 1
    other = get_unresolved_conflicts(db, p.id)[0]
    other.status, other.decision, other.kept_project_id = "CONFIRMED", "CONFLICT", p.id
    db.flush()
    assert not get_unresolved_conflicts(db, p.id)


def test_review_http_guard_blocks_admin_shortcut_and_regular_user_cannot_assign(db):
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    from app.api.deps import get_current_user
    from app.api.handover_guard import require_ready_assignments
    from app.api.v1.project_handovers import router
    from app.db.session import get_db
    owner, old, admin = user(db, "owner"), user(db, "old", "FIRST_REVIEWER"), user(db, "admin", "ADMIN")
    p, w = project(db, owner)
    w.first_reviewer_id, w.current_handler_user_id, w.current_status = old.id, old.id, "FIRST_REVIEWING"
    old.is_active = False
    task = take_over(db, old, admin)[0]
    db.commit()
    app = FastAPI()
    app.include_router(router)
    @app.post("/decision", dependencies=[Depends(require_ready_assignments)])
    def decision():
        return {"executed": True}
    from app.models.contract_review_record import ContractReviewRecord
    record = ContractReviewRecord(work_order_id=w.id, project_id=p.id, action_type="SUBMIT",
                                  operator_user_id=owner.id, reviewer_user_id=old.id)
    db.add(record); db.commit()
    @app.post("/contract-reviews/{record_id}/approve", dependencies=[Depends(require_ready_assignments)])
    def approve(record_id: int):
        return {"executed": True}
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: admin
    with TestClient(app) as client:
        assert client.post("/decision", json={"work_order_id": w.id}).status_code == 409
        assert client.post(f"/contract-reviews/{record.id}/approve", json={"work_order_id": 99999}).status_code == 409
        assert client.post(f"/contract-reviews/{record.id}/approve", json={"work_order_id": "invalid"}).status_code == 400
        app.dependency_overrides[get_current_user] = lambda: owner
        assert client.get("/project-handovers").status_code == 403
        assert client.post(f"/project-handovers/{task.id}/assign", json={"target_user_id": owner.id, "reason": "越权"}).status_code == 403


def test_role_and_round_avoidance_rejects_project_member(db):
    owner, old, admin, new = user(db, "owner"), user(db, "old"), user(db, "admin", "ADMIN"), user(db, "new", "FIRST_REVIEWER")
    p, w = project(db, owner)
    w.first_reviewer_id = old.id
    task = take_over(db, old, admin)[0]
    db.add(ProjectMember(project_id=p.id, user_id=new.id, member_role="MEMBER")); db.flush()
    with pytest.raises(HTTPException):
        assign(db, task.id, new.id, admin, "回避校验")
    db.query(ProjectMember).filter_by(user_id=new.id).delete()
    w.second_reviewer_id = new.id
    with pytest.raises(HTTPException):
        assign(db, task.id, new.id, admin, "轮次回避")


def test_custodian_temporary_membership_removed_after_both_assignments(db):
    old, admin, target = user(db, "old"), user(db, "admin", "ADMIN"), user(db, "target")
    p, w = project(db, old)
    tasks = take_over(db, old, admin)
    for task in tasks:
        assign(db, task.id, target.id, admin, "完整交接")
    assert not db.query(ProjectMember).filter_by(project_id=p.id, user_id=admin.id).first()
    flow = get_project_flow(p.id, db, target)
    assert flow.project.original_creator_name == old.real_name
    assert flow.project.current_creator_name == target.real_name


def test_handover_migration_is_idempotent(db):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    path = Path(__file__).parents[1] / "migrations/versions/0006_project_handovers.py"
    spec = importlib.util.spec_from_file_location("handover_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    connection = db.connection()
    ProjectConflictEvaluation.__table__.drop(connection)
    ProjectHandover.__table__.drop(connection)
    migration.op = Operations(MigrationContext.configure(connection))
    migration.upgrade(); migration.upgrade()
    assert "custodian_member_created" in {c["name"] for c in inspect(connection).get_columns("project_handovers")}
    assert inspect(connection).get_unique_constraints("project_conflict_evaluations")[0]["name"] == "uq_conflict_evaluation"
