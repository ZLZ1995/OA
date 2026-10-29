from datetime import date, datetime, timedelta, timezone
import io
import uuid
import zipfile

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import text
from test_operation_workpapers import bundle, send
from app.models.project import Project
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.models.operation_workpaper import OperationWorkpaperReview as Review, OperationWorkpaperSubmission as Submission, OperationWorkpaperSubmissionFile as Attachment
from app.services.project_delete_service import delete_project_related_data
from app.services.operation_workpaper import open_after_second, initialize_workflow_versions, WorkflowActivationError
from app.api.v1.operation_workpapers import enter, decide, Decision, Submit, submit, withdraw, get_state, upload_zip
from app.core.workflow_baseline import WorkflowBaseline
from app.core.config import settings


def zip_upload(db, order, leader):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as z:
        z.writestr('schedule.txt', 'test')
    data.seek(0)
    return upload_zip(order.id, UploadFile(filename='test.zip', file=data), db, leader)['id']


@pytest.mark.parametrize('stage', ['DRAFT', 'SUBMITTED', 'IN_REVIEW', 'APPROVED'])
def test_delete_cleans_all_workpaper_rows_and_new_order_starts_draft(bundle, stage):
    db, order, leader, reviewer, _, _ = bundle
    old_id = order.id
    if stage != 'DRAFT':
        sid = send(db, order, leader, reviewer)
        if stage in {'IN_REVIEW', 'APPROVED'}:
            enter(sid, db, reviewer)
        if stage == 'APPROVED':
            decide(sid, Decision(action='APPROVE'), db, reviewer)
    delete_project_related_data(db, db.get(Project, order.project_id))
    db.commit(); db.expunge_all()
    assert db.query(Review).count() == db.query(Submission).count() == db.query(Attachment).count() == 0
    leader = db.query(User).filter_by(username='leader').one()
    project = Project(project_code='P2', project_name='next', client_name='next', business_user_id=leader.id,
        project_leader_id=leader.id, project_amount=100, valuation_base_date=date(2026,10,29), workflow_version='PARALLEL_WORKPAPER_V1')
    db.add(project); db.flush()
    new_order = WorkOrder(project_id=project.id, work_order_no='P2', title='next', current_status='SECOND_REVIEWING', project_leader_id=leader.id, initiator_user_id=leader.id)
    db.add(new_order); db.flush()
    assert new_order.id == old_id  # SQLite's reuse must be harmless.
    result = open_after_second(db, new_order)
    assert result.status == 'DRAFT' and result.current_submission_id is None


@pytest.mark.parametrize('foreign_keys', [False, True])
def test_delete_zip_rollback_preserves_file_and_history(bundle, tmp_path, monkeypatch, foreign_keys):
    db, order, leader, reviewer, _, _ = bundle
    monkeypatch.setattr(settings, 'local_storage_dir', str(tmp_path))
    db.commit()
    db.execute(text(f'PRAGMA foreign_keys={int(foreign_keys)}'))
    fid = zip_upload(db, order, leader)
    submit(order.id, Submit(reviewer_id=reviewer.id, request_id=str(uuid.uuid4()), revision=0,
        material_type='ZIP', file_ids=[fid]), db, leader)
    path = tmp_path / db.get(WorkOrderFile, fid).storage_key
    project_id = order.project_id
    delete_project_related_data(db, db.get(Project, project_id))
    assert path.exists()
    db.rollback(); db.expire_all()
    assert path.exists() and db.query(Attachment).count() == 1
    db.commit()  # cancelled cleanup must not run during another transaction
    assert path.exists()
    delete_project_related_data(db, db.get(Project, project_id))
    db.commit()
    assert not path.exists()


def test_create_reused_legacy_id_is_new_even_after_restart(bundle, monkeypatch):
    from app.api.v1.projects import create_project
    from app.schemas.project import ProjectCreate
    from app.services import operation_workpaper as service
    db, order, leader, *_ = bundle
    old_id = order.project_id
    baseline = WorkflowBaseline(frozenset({old_id}), datetime.now(timezone.utc), 'test', 'test')
    monkeypatch.setattr(service, 'configured_baseline', lambda: baseline)
    delete_project_related_data(db, db.get(Project, old_id))
    db.commit(); db.expunge_all()
    leader = db.query(User).filter_by(username='leader').one()
    response = create_project(ProjectCreate(project_code='P2', undertaking_unit='中勤', project_name='next', client_name='next',
        business_user_id=leader.id, project_leader_id=leader.id, project_amount=100, valuation_base_date=date(2026,10,29)), db, leader)
    assert response.id == old_id
    assert db.get(Project, response.id).workflow_version == 'PARALLEL_WORKPAPER_V1'
    initialize_workflow_versions(db); db.commit(); db.expire_all()
    assert db.get(Project, response.id).workflow_version == 'PARALLEL_WORKPAPER_V1'


def test_orphan_review_blocks_startup(bundle):
    db, order, *_ = bundle
    db.query(WorkOrder).delete(); db.commit()
    with pytest.raises(WorkflowActivationError, match='Orphan'):
        initialize_workflow_versions(db)


@pytest.mark.parametrize('workpaper_first', [False, True])
def test_external_third_withdraw_and_workpaper_pass_do_not_override_each_other(bundle, workpaper_first):
    from app.api.v1.reviews import decide_review, withdraw_latest_review_step
    from app.schemas.review import ReviewDecisionRequest
    db, order, leader, reviewer, third, _ = bundle
    order.third_reviewer_id = third.id
    order.current_status = 'EXTERNAL_THIRD_REVIEWING'; db.commit()
    sid = send(db, order, leader, reviewer); enter(sid, db, reviewer)
    decide_review(ReviewDecisionRequest(work_order_id=order.id, review_round='EXTERNAL_THIRD', action='APPROVE'), db, third, {'THIRD_REVIEWER'})
    assert order.current_status == 'WAIT_PARALLEL_WORKPAPER'
    if workpaper_first:
        decide(sid, Decision(action='APPROVE'), db, reviewer)
    withdraw_latest_review_step(order.id, db, third, {'THIRD_REVIEWER'})
    if not workpaper_first:
        decide(sid, Decision(action='APPROVE'), db, reviewer)
    assert order.current_status == 'EXTERNAL_THIRD_REVIEWING'
    assert get_state(order.id, db, leader)['status'] == 'APPROVED'


def test_retry_is_idempotent_but_closed_round_cannot_report_new_success(bundle):
    db, order, leader, reviewer, *_ = bundle
    payload = Submit(reviewer_id=reviewer.id, request_id='lost-response-id', revision=0,
        material_type='CLOUD_LINK', cloud_url='https://example.com/test', cloud_code='1234')
    sid = submit(order.id, payload, db, leader)['submission_id']
    assert submit(order.id, payload, db, leader)['submission_id'] == sid
    withdraw(sid, db, leader)
    payload.revision = get_state(order.id, db, leader)['revision']
    with pytest.raises(HTTPException) as exc:
        submit(order.id, payload, db, leader)
    assert exc.value.status_code == 409
    db.rollback()
    payload.request_id = str(uuid.uuid4())
    new_sid = submit(order.id, payload, db, leader)['submission_id']
    assert new_sid != sid and db.get(Submission, new_sid).round_no == 2


def test_gc_only_removes_expired_unreferenced_files_after_commit(bundle, tmp_path, monkeypatch):
    from app.services.workpaper_temporary_files import collect_expired_workpaper_files
    db, order, leader, reviewer, *_ = bundle
    monkeypatch.setattr(settings, 'local_storage_dir', str(tmp_path))
    abandoned, recent, historical = [zip_upload(db, order, leader) for _ in range(3)]
    now = datetime.now(timezone.utc)
    for fid in [abandoned, historical]:
        db.get(WorkOrderFile, fid).uploaded_at = now - timedelta(hours=25)
    db.commit()
    sid = submit(order.id, Submit(reviewer_id=reviewer.id, request_id=str(uuid.uuid4()), revision=0,
        material_type='ZIP', file_ids=[historical]), db, leader)['submission_id']
    withdraw(sid, db, leader)
    paths = {fid: tmp_path / db.get(WorkOrderFile, fid).storage_key for fid in [abandoned, recent, historical]}
    assert collect_expired_workpaper_files(db, now=now) == 1
    assert paths[abandoned].exists()
    db.rollback()
    assert db.get(WorkOrderFile, abandoned) and paths[abandoned].exists()
    assert collect_expired_workpaper_files(db, now=now) == 1
    db.commit()
    assert not paths[abandoned].exists()
    assert all(paths[fid].exists() for fid in [recent, historical])


def test_gc_rechecks_references_when_submission_wins_the_lock(bundle, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy.orm import Session
    from app.services import workpaper_temporary_files as gc
    db, order, leader, reviewer, _, engine = bundle
    monkeypatch.setattr(settings, 'local_storage_dir', str(tmp_path))
    fid = zip_upload(db, order, leader)
    db.get(WorkOrderFile, fid).uploaded_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db.commit()
    waiting, resume = Event(), Event()
    original_lock = gc.lock_order
    def delayed_lock(session, order_id):
        waiting.set()
        assert resume.wait(timeout=10)
        original_lock(session, order_id)
    monkeypatch.setattr(gc, 'lock_order', delayed_lock)
    def cleanup():
        with Session(engine) as session:
            count = gc.collect_expired_workpaper_files(session)
            session.commit()
            return count
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(cleanup)
        try:
            assert waiting.wait(timeout=10)
            submit(order.id, Submit(reviewer_id=reviewer.id, request_id=str(uuid.uuid4()), revision=0,
                material_type='ZIP', file_ids=[fid]), db, leader)
        finally:
            resume.set()
        assert future.result(timeout=10) == 0
    assert (tmp_path / db.get(WorkOrderFile, fid).storage_key).exists()


def test_external_withdraw_concurrent_with_workpaper_approval(bundle):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import Session
    from app.api.v1.reviews import decide_review, withdraw_latest_review_step
    from app.schemas.review import ReviewDecisionRequest
    db, order, leader, reviewer, third, engine = bundle
    order.third_reviewer_id = third.id
    order.current_status = 'EXTERNAL_THIRD_REVIEWING'; db.commit()
    sid = send(db, order, leader, reviewer); enter(sid, db, reviewer)
    decide_review(ReviewDecisionRequest(work_order_id=order.id, review_round='EXTERNAL_THIRD', action='APPROVE'), db, third, {'THIRD_REVIEWER'})
    oid, rid, tid = order.id, reviewer.id, third.id
    db.rollback()
    barrier = Barrier(2)
    def action(kind):
        with Session(engine) as session:
            user = session.get(User, rid if kind == 'approve' else tid)
            barrier.wait(timeout=10)
            if kind == 'approve':
                decide(sid, Decision(action='APPROVE'), session, user)
            else:
                withdraw_latest_review_step(oid, session, user, {'THIRD_REVIEWER'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(action, ['approve', 'withdraw']))
    db.expire_all()
    assert db.get(WorkOrder, oid).current_status == 'EXTERNAL_THIRD_REVIEWING'
    assert db.query(Review).filter_by(work_order_id=oid).one().status == 'APPROVED'
