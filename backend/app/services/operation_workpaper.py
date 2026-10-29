"""Parallel workpaper operations. Callers commit the complete business transaction."""
from datetime import datetime, timezone
from functools import lru_cache
import os

from fastapi import HTTPException
from sqlalchemy import update, text
from sqlalchemy.orm import Session

from app.core.workflow_baseline import LEGACY, PARALLEL_WORKPAPER_V1, load_baseline
from app.models.operation_workpaper import OperationWorkpaperReview, OperationWorkpaperSubmission
from app.models.project import Project
from app.models.review_record import ReviewRecord


class WorkflowActivationError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def configured_baseline():
    path = os.environ.get("OA_WORKFLOW_BASELINE_PATH")
    if not path:
        return None
    try:
        return load_baseline(path, expected_service_id=os.environ.get("OA_WORKFLOW_SOURCE_SERVICE_ID", ""))
    except (OSError, ValueError, KeyError) as exc:
        raise WorkflowActivationError("Workflow baseline could not be validated") from exc


def initialize_workflow_versions(db: Session):
    from app.models.work_order import WorkOrder
    orphan = db.query(OperationWorkpaperReview.id).outerjoin(WorkOrder, WorkOrder.id == OperationWorkpaperReview.work_order_id).filter(WorkOrder.id.is_(None)).first()
    if orphan:
        raise WorkflowActivationError("Orphan workpaper review detected; repair before activation")
    baseline = configured_baseline()
    if baseline is None:
        if db.query(Project.id).filter(Project.workflow_version == PARALLEL_WORKPAPER_V1).first():
            raise WorkflowActivationError("Workflow baseline must remain configured after activation")
        return
    for project in db.query(Project).all():
        if project.workflow_version is None:
            project.workflow_version = baseline.version_for(project.id)
        elif project.workflow_version not in {LEGACY, PARALLEL_WORKPAPER_V1}:
            raise WorkflowActivationError("Unknown persisted project workflow version")
    db.flush()
    from app.models.work_order import WorkOrder
    for order in db.query(WorkOrder).join(Project).filter(Project.workflow_version == PARALLEL_WORKPAPER_V1).all():
        review = db.query(OperationWorkpaperReview).filter_by(work_order_id=order.id).first()
        if review is not None:
            continue
        if order.current_status in {"SIGNOFF_REVIEWING", "THIRD_APPROVED_WAIT_PRINTROOM", "PRINTROOM_PROCESSING", "PAPER_REPORT_ISSUED",
                "REPORT_MAILING", "REPORT_MAILING_COMPLETED", "WAIT_INVOICE_INFO", "INVOICE_PROCESSING", "INVOICE_ISSUED",
                "WAIT_ARCHIVE_SUBMIT", "ARCHIVE_REVIEWING", "ARCHIVED"}:
            raise WorkflowActivationError(f"New project {order.project_id} advanced beyond the new gate before activation; activation aborted")
        second = db.query(ReviewRecord.id).filter_by(work_order_id=order.id, review_round="SECOND", action="APPROVE").first()
        if second:
            open_after_second(db, order)
            if order.current_status == "WAIT_OWNER_SIGNOFF_UPLOAD":
                order.current_status = "WAIT_PARALLEL_WORKPAPER"
    db.flush()


def uses_parallel(db: Session, work_order) -> bool:
    project = db.get(Project, work_order.project_id)
    if project is None:
        raise HTTPException(404, "项目不存在")
    if project.workflow_version is None:
        baseline = configured_baseline()
        if baseline is None:
            return False
        project.workflow_version = baseline.version_for(project.id)
    return project.workflow_version == PARALLEL_WORKPAPER_V1


def ensure_active_project(db, work_order):
    project = db.get(Project, work_order.project_id)
    if project is None or project.deleted_at or project.archived_at or project.termination_status in {"PENDING", "APPROVED", "DELETE_PENDING"}:
        raise HTTPException(409, "项目已结束，不能操作底稿审核")
    if project.duplicate_delete_required:
        raise HTTPException(409, "重复项目待处理，不能操作底稿审核")
    from app.services.project_conflicts import assert_project_can_submit_review
    assert_project_can_submit_review(db, project)
    from app.models.project_handover import ProjectHandover
    if db.query(ProjectHandover.id).filter_by(work_order_id=work_order.id,
            duty="operation_workpaper_reviewer_id", status="PENDING").first():
        raise HTTPException(409, "底稿审核人员待管理员重新分配")


def open_after_second(db, work_order):
    if not uses_parallel(db, work_order):
        return None
    review = db.query(OperationWorkpaperReview).filter_by(work_order_id=work_order.id).first()
    if review is None:
        review = OperationWorkpaperReview(work_order_id=work_order.id, status="DRAFT", revision=0)
        db.add(review)
        db.flush()
    return review


def lock_order(db, order_id):
    # SQLite must acquire its write lock before reading shared branch state.
    db.execute(text("UPDATE work_orders SET id=id WHERE id=:id"), {"id": order_id})


def signoff_destination(db, work_order):
    from app.workflows.states import WorkOrderStatus
    if uses_parallel(db, work_order):
        review = db.query(OperationWorkpaperReview).filter_by(work_order_id=work_order.id).first()
        if not review or review.status != "APPROVED":
            return WorkOrderStatus.WAIT_PARALLEL_WORKPAPER
    return WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD


def assert_signoff_ready(db, work_order):
    if not uses_parallel(db, work_order):
        return
    review = db.query(OperationWorkpaperReview).filter_by(work_order_id=work_order.id).first()
    third = db.query(ReviewRecord).filter_by(work_order_id=work_order.id, review_round="THIRD").filter(
        ReviewRecord.action.in_(["APPROVE", "REJECT_RETURN"])
    ).order_by(ReviewRecord.id.desc()).first()
    if not review or review.status != "APPROVED" or not third or third.action != "APPROVE":
        raise HTTPException(409, "三审和操作类底稿审核均通过后才能进入签发审核")


def transition(db, review, submission, expected, target, actor_id):
    """One CAS for the shared round: entry and withdrawal cannot both succeed."""
    changed = db.execute(update(OperationWorkpaperReview).where(
        OperationWorkpaperReview.id == review.id,
        OperationWorkpaperReview.current_submission_id == submission.id,
        OperationWorkpaperReview.status == expected,
        OperationWorkpaperReview.revision == review.revision,
    ).values(status=target, revision=OperationWorkpaperReview.revision + 1),
        execution_options={"synchronize_session": False})
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "底稿审核状态已变化，请刷新页面")
    now = datetime.now(timezone.utc)
    submission.status = target
    if target == "IN_REVIEW":
        submission.first_entered_at = now
        submission.entered_by = actor_id
    elif target == "WITHDRAWN":
        submission.withdrawn_at = now
    else:
        submission.decided_at = now
    db.flush()
    db.refresh(review)
