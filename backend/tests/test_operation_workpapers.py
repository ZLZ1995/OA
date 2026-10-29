from datetime import date, datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.db.base import Base
from app.models.operation_workpaper import OperationWorkpaperReview as Review, OperationWorkpaperSubmission as Submission
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.review_record import ReviewRecord
from app.api.v1.operation_workpapers import Submit, Decision, submit, enter, withdraw, decide, get_state, candidates
from app.services.operation_workpaper import open_after_second, assert_signoff_ready, signoff_destination, transition


@pytest.fixture
def bundle(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False, "timeout": 10})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        role = Role(code="ARCHIVE_MANAGER", name="archive", is_system_fixed=True)
        leader = User(username="leader", real_name="leader", password_hash="x", is_active=True)
        reviewer = User(username="reviewer", real_name="reviewer", password_hash="x", is_active=True)
        other = User(username="other", real_name="other", password_hash="x", is_active=True)
        db.add_all([role, leader, reviewer, other]); db.flush()
        db.add_all([UserRole(user_id=leader.id, role_id=role.id), UserRole(user_id=reviewer.id, role_id=role.id)])
        project = Project(project_code="P1", project_name="test", client_name="test", business_user_id=leader.id,
            project_leader_id=leader.id, project_amount=100, valuation_base_date=date(2026, 10, 29),
            workflow_version="PARALLEL_WORKPAPER_V1")
        db.add(project); db.flush()
        order = WorkOrder(project_id=project.id, work_order_no="P1", title="test", current_status="THIRD_REVIEWING",
            current_handler_user_id=other.id, project_leader_id=leader.id, initiator_user_id=leader.id)
        db.add(order); db.flush()
        open_after_second(db, order); db.commit()
        yield db, order, leader, reviewer, other, engine
    engine.dispose()


def send(db, order, leader, reviewer, revision=0):
    payload = Submit(reviewer_id=reviewer.id, request_id=str(uuid.uuid4()), revision=revision,
        material_type="CLOUD_LINK", cloud_url="https://example.com/workpapers", cloud_code="1234")
    return submit(order.id, payload, db, leader)["submission_id"]


def test_cloud_submission_http_validation_and_valid_link(bundle):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1.operation_workpapers import router, tasks
    from app.api.deps import get_current_user
    from app.db.session import get_db

    db, order, leader, reviewer, _, _ = bundle
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: leader
    client = TestClient(app)
    payload = dict(reviewer_id=reviewer.id, request_id=str(uuid.uuid4()), revision=0,
        material_type="CLOUD_LINK", cloud_url="111", cloud_code="111")
    response = client.post(f"/operation-workpapers/work-orders/{order.id}/submit", json=payload)
    assert response.status_code == 422
    assert "HTTP" in response.json()["detail"][0]["msg"]
    assert get_state(order.id, db, leader)["status"] == "DRAFT"
    assert tasks(db, leader)[0]["client_name"] == "test"
    payload["cloud_url"] = "https://pan.baidu.com/s/test"
    response = client.post(f"/operation-workpapers/work-orders/{order.id}/submit", json=payload)
    assert response.status_code == 200, response.text
    assert get_state(order.id, db, leader)["status"] == "SUBMITTED"
    assert tasks(db, leader) == []
    assert tasks(db, reviewer)[0]["panel"] == "operationWorkpaperReview"


def test_owner_view_does_not_start_review_and_reviewer_entry_blocks_withdraw(bundle):
    db, order, leader, reviewer, _, _ = bundle
    sid = send(db, order, leader, reviewer)
    assert get_state(order.id, db, leader)["status"] == "SUBMITTED"
    assert get_state(order.id, db, reviewer)["history"][0]["cloud_url"] is None
    enter(sid, db, reviewer)
    assert get_state(order.id, db, reviewer)["history"][0]["cloud_code"] == "1234"
    with pytest.raises(HTTPException) as exc:
        withdraw(sid, db, leader)
    assert exc.value.status_code == 409
    assert db.get(Submission, sid).status == "IN_REVIEW"


def test_withdraw_resubmit_retains_history_and_stale_entry_fails(bundle):
    db, order, leader, reviewer, _, _ = bundle
    old = send(db, order, leader, reviewer)
    withdraw(old, db, leader)
    state = get_state(order.id, db, leader)
    new = send(db, order, leader, reviewer, state["revision"])
    with pytest.raises(HTTPException):
        enter(old, db, reviewer)
    assert db.get(Submission, new).first_entered_at is None
    assert db.get(Submission, old).status == "WITHDRAWN"
    assert db.get(Submission, new).round_no == 2


def test_self_review_allowed_but_nonassigned_user_rejected(bundle):
    db, order, leader, reviewer, other, _ = bundle
    assert leader.id in [p["id"] for p in candidates(order.id, db, leader)]
    sid = send(db, order, leader, leader)
    with pytest.raises(HTTPException):
        enter(sid, db, reviewer)
    with pytest.raises(HTTPException):
        get_state(order.id, db, other)
    enter(sid, db, leader)
    decide(sid, Decision(action="APPROVE"), db, leader)
    assert get_state(order.id, db, leader)["status"] == "APPROVED"
    assert order.current_status == "THIRD_REVIEWING"


def test_rejection_requires_reason_and_does_not_reset_third(bundle):
    db, order, leader, reviewer, _, _ = bundle
    sid = send(db, order, leader, reviewer)
    enter(sid, db, reviewer)
    with pytest.raises(HTTPException):
        decide(sid, Decision(action="REJECT", reason="  "), db, reviewer)
    db.rollback()
    decide(sid, Decision(action="REJECT", reason="Missing schedule"), db, reviewer)
    assert order.current_status == "THIRD_REVIEWING"
    new = send(db, order, leader, reviewer, get_state(order.id, db, leader)["revision"])
    assert db.get(Submission, new).first_entered_at is None
    assert db.get(Submission, sid).decision_reason == "Missing schedule"


def test_both_pass_required_and_waiting_converges(bundle):
    db, order, leader, reviewer, _, _ = bundle
    with pytest.raises(HTTPException):
        assert_signoff_ready(db, order)
    assert signoff_destination(db, order).value == "WAIT_PARALLEL_WORKPAPER"
    db.add(ReviewRecord(work_order_id=order.id, review_round="THIRD", reviewer_user_id=reviewer.id,
        action="APPROVE", acted_at=datetime.now(timezone.utc)))
    order.current_status = "WAIT_PARALLEL_WORKPAPER"; db.commit()
    sid = send(db, order, leader, reviewer)
    enter(sid, db, reviewer); decide(sid, Decision(action="APPROVE"), db, reviewer)
    assert order.current_status == "WAIT_OWNER_SIGNOFF_UPLOAD"
    assert_signoff_ready(db, order)


@pytest.mark.parametrize("status", ["WORK_ORDER_CREATED", "FIRST_REVIEWING", "SECOND_REVIEWING", "THIRD_REVIEWING", "SIGNOFF_REVIEWING", "ARCHIVED"])
def test_legacy_projects_unchanged_at_every_stage(bundle, status):
    db, order, leader, reviewer, _, _ = bundle
    db.get(Project, order.project_id).workflow_version = "LEGACY"
    order.current_status = status; db.commit()
    assert open_after_second(db, order) is None
    assert_signoff_ready(db, order)
    assert get_state(order.id, db, leader)["enabled"] is False
    with pytest.raises(HTTPException):
        send(db, order, leader, reviewer)
    assert order.current_status == status


@pytest.mark.parametrize("material", [
    dict(material_type="ZIP", file_ids=[]),
    dict(material_type="ZIP", file_ids=[1], cloud_url="https://example.com", cloud_code="1234"),
    dict(material_type="CLOUD_LINK", cloud_url="https://example.com"),
    dict(material_type="CLOUD_LINK", cloud_url="javascript:alert(1)", cloud_code="1234"),
    dict(material_type="CLOUD_LINK", cloud_url="https://example.com", cloud_code="1234", file_ids=[1]),
])
def test_material_xor_validation(material):
    with pytest.raises(ValidationError):
        Submit(reviewer_id=1, request_id="request-123", revision=0, **material)


def test_entry_withdraw_race_uses_separate_database_sessions(bundle):
    db, order, leader, reviewer, _, engine = bundle
    sid = send(db, order, leader, reviewer)
    ids = leader.id, reviewer.id
    db.rollback()
    barrier = Barrier(2)
    def action(target):
        with Session(engine) as session:
            row = session.get(Submission, sid)
            review = session.get(Review, row.review_id)
            barrier.wait(timeout=5)
            try:
                transition(session, review, row, "SUBMITTED", target, ids[0] if target == "WITHDRAWN" else ids[1])
                session.commit()
                return target
            except HTTPException as exc:
                assert exc.status_code == 409
                return "CONFLICT"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(action, ["IN_REVIEW", "WITHDRAWN"]))
    assert results.count("CONFLICT") == 1
    db.expire_all()
    row = db.get(Submission, sid)
    assert (row.first_entered_at is not None) != (row.withdrawn_at is not None)


def test_third_approval_waits_for_workpapers_through_real_review_endpoint(bundle):
    from app.api.v1.reviews import decide_review
    from app.schemas.review import ReviewDecisionRequest
    db, order, leader, reviewer, third, _ = bundle
    order.third_reviewer_id = third.id
    db.commit()
    decide_review(ReviewDecisionRequest(work_order_id=order.id, review_round="THIRD", action="APPROVE"), db, third, {"THIRD_REVIEWER"})
    assert order.current_status == "WAIT_PARALLEL_WORKPAPER"
    sid = send(db, order, leader, reviewer)
    enter(sid, db, reviewer)
    decide(sid, Decision(action="APPROVE"), db, reviewer)
    assert order.current_status == "WAIT_OWNER_SIGNOFF_UPLOAD"


def test_second_approval_opens_review_without_changing_third_handler(bundle):
    from app.api.v1.reviews import decide_review
    from app.schemas.review import ReviewDecisionRequest
    db, order, leader, reviewer, second, _ = bundle
    db.query(Review).delete()
    order.current_status = "SECOND_REVIEWING"
    order.second_reviewer_id = second.id
    order.current_handler_user_id = second.id
    db.commit()
    decide_review(ReviewDecisionRequest(work_order_id=order.id, review_round="SECOND", action="APPROVE"), db, second, {"SECOND_REVIEWER"})
    assert db.query(Review).filter_by(work_order_id=order.id).one().status == "DRAFT"
    assert order.current_handler_user_id == second.id
    assert order.current_status == "SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD"


def test_handover_reassigns_current_review_preserving_entry_time(bundle):
    from app.services.project_handover import take_over, assign
    db, order, leader, reviewer, admin, _ = bundle
    sid = send(db, order, leader, reviewer)
    enter(sid, db, reviewer)
    timestamp = db.get(Submission, sid).first_entered_at
    reviewer.is_active = False
    handovers = take_over(db, reviewer, admin)
    db.commit()
    task = next(t for t in handovers if t.duty == "operation_workpaper_reviewer_id")
    assign(db, task.id, leader.id, admin, "Reassign to qualified project leader")
    db.commit()
    assert db.get(Submission, sid).reviewer_id == leader.id
    assert db.get(Submission, sid).first_entered_at == timestamp
    decide(sid, Decision(action="APPROVE"), db, leader)


def test_zip_upload_and_xor_storage_access(bundle, tmp_path, monkeypatch):
    import io
    import zipfile
    from fastapi import UploadFile
    from app.core.config import settings
    from app.api.v1.operation_workpapers import upload_zip, discard_temporary_file
    from app.api.v1.files import download_work_order_file, list_work_order_files
    db, order, leader, reviewer, other, _ = bundle
    monkeypatch.setattr(settings, "local_storage_dir", str(tmp_path))
    with pytest.raises(HTTPException):
        upload_zip(order.id, UploadFile(filename="fake.zip", file=io.BytesIO(b"not a zip")), db, leader)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("schedule.txt", "sample")
    payload.seek(0)
    file_id = upload_zip(order.id, UploadFile(filename="workpaper.zip", file=payload), db, leader)["id"]
    sid = submit(order.id, Submit(reviewer_id=reviewer.id, request_id=str(uuid.uuid4()), revision=0,
        material_type="ZIP", file_ids=[file_id]), db, leader)["submission_id"]
    assert list_work_order_files(order.id, db, reviewer).items == []
    with pytest.raises(HTTPException):
        download_work_order_file(file_id, db, reviewer)
    enter(sid, db, reviewer)
    assert download_work_order_file(file_id, db, reviewer).filename == "workpaper.zip"
    with pytest.raises(HTTPException):
        discard_temporary_file(file_id, db, leader)
    with pytest.raises(HTTPException):
        download_work_order_file(file_id, db, other)


@pytest.mark.parametrize("legacy", [True, False])
def test_activation_uses_manifest_membership_and_bootstraps_gate(bundle, monkeypatch, legacy):
    from types import SimpleNamespace
    from app.services import operation_workpaper as service
    db, order, leader, reviewer, _, _ = bundle
    project = db.get(Project, order.project_id)
    project.workflow_version = None
    db.query(Review).delete()
    order.current_status = "WAIT_OWNER_SIGNOFF_UPLOAD"
    db.add(ReviewRecord(work_order_id=order.id, review_round="SECOND", reviewer_user_id=reviewer.id,
        action="APPROVE", acted_at=datetime.now(timezone.utc)))
    db.commit()
    version = "LEGACY" if legacy else "PARALLEL_WORKPAPER_V1"
    monkeypatch.setattr(service, "configured_baseline", lambda: SimpleNamespace(version_for=lambda pid: version))
    service.initialize_workflow_versions(db)
    db.commit()
    assert project.workflow_version == version
    assert order.current_status == ("WAIT_OWNER_SIGNOFF_UPLOAD" if legacy else "WAIT_PARALLEL_WORKPAPER")
    assert db.query(Review).count() == (0 if legacy else 1)
    service.initialize_workflow_versions(db)
    assert db.query(Review).count() == (0 if legacy else 1)


def test_activation_cannot_reclassify_existing_projects(bundle, monkeypatch):
    from types import SimpleNamespace
    from app.services import operation_workpaper as service
    db, order, *_ = bundle
    monkeypatch.setattr(service, "configured_baseline", lambda: SimpleNamespace(version_for=lambda pid: "LEGACY"))
    service.initialize_workflow_versions(db)
    db.commit()
    assert db.get(Project, order.project_id).workflow_version == "PARALLEL_WORKPAPER_V1"
