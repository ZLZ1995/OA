from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
import zipfile
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.operation_workpaper import OperationWorkpaperReview as Review, OperationWorkpaperSubmission as Submission, OperationWorkpaperSubmissionFile as Attachment
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.services.operation_workpaper import uses_parallel, ensure_active_project, transition
from app.services.workflow_log_service import create_workflow_log
from app.services.workflow_notification_service import send_workflow_notification

router = APIRouter(prefix="/operation-workpapers", tags=["操作类底稿审核"])
CATEGORY = "OPERATION_WORKPAPER"


class Submit(BaseModel):
    reviewer_id: int
    request_id: str = Field(min_length=8, max_length=64)
    revision: int = Field(ge=0)
    material_type: Literal["ZIP", "CLOUD_LINK"]
    file_ids: list[int] = Field(default_factory=list)
    cloud_url: str | None = Field(default=None, max_length=2048)
    cloud_code: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def exclusive_materials(self):
        self.cloud_url = (self.cloud_url or "").strip() or None
        self.cloud_code = (self.cloud_code or "").strip() or None
        if self.material_type == "ZIP":
            if not self.file_ids or self.cloud_url or self.cloud_code or len(set(self.file_ids)) != len(self.file_ids):
                raise ValueError("请选择一个或多个ZIP文件，不可同时填写网盘信息")
        else:
            if self.file_ids or not self.cloud_url or not self.cloud_code:
                raise ValueError("网盘链接和提取码均为必填项，不可同时上传ZIP文件")
            url = urlparse(self.cloud_url)
            if url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password:
                raise ValueError("请填写有效的HTTP或HTTPS网盘链接")
        return self


class Decision(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    reason: str = Field(default="", max_length=4000)


@router.get("/tasks")
def tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Review, WorkOrder, Project).join(WorkOrder, WorkOrder.id == Review.work_order_id).join(
        Project, Project.id == WorkOrder.project_id).filter(Project.deleted_at.is_(None), Project.archived_at.is_(None)).all()
    result = []
    for review, order, project in rows:
        if project.termination_status in {"PENDING", "APPROVED", "DELETE_PENDING"}:
            continue
        row = db.get(Submission, review.current_submission_id) if review.current_submission_id else None
        mode = None
        if review.status in {"DRAFT", "WITHDRAWN", "REJECTED"} and order.project_leader_id == user.id:
            mode = "operationWorkpaper"
        elif review.status in {"SUBMITTED", "IN_REVIEW"} and row and row.reviewer_id == user.id:
            mode = "operationWorkpaperReview"
        if mode:
            result.append(dict(project_id=project.id, project_code=project.project_code, project_name=project.project_name,
                status=review.status, panel=mode))
    return result


def is_admin(user):
    return any(r.role.code == "ADMIN" for r in user.roles)


def order_for(db, order_id):
    order = db.get(WorkOrder, order_id)
    if not order:
        raise HTTPException(404, "工单不存在")
    return order


def review_for(db, order):
    if not uses_parallel(db, order):
        raise HTTPException(409, "旧项目沿用原流程，无操作类底稿并行审核")
    review = db.query(Review).filter_by(work_order_id=order.id).first()
    if not review:
        raise HTTPException(409, "二审通过后才能提交操作类底稿")
    return review


def ensure_leader(order, user):
    if order.project_leader_id != user.id:
        raise HTTPException(403, "仅项目负责人可提交或撤回操作类底稿")


def ensure_reviewer(db, user_id):
    if not db.query(User.id).join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).filter(
        User.id == user_id, User.is_active.is_(True), Role.code == "ARCHIVE_MANAGER"
    ).first():
        raise HTTPException(403, "请选择具有档案管理员角色的有效账号")


def ensure_access(db, order, user):
    project = db.get(Project, order.project_id)
    assigned = db.query(Submission.id).join(Review, Review.id == Submission.review_id).filter(
        Review.work_order_id == order.id, Submission.reviewer_id == user.id
    ).first()
    if not (is_admin(user) or user.id in {order.project_leader_id, project.business_user_id} or assigned or
            db.query(ProjectMember.id).filter_by(project_id=project.id, user_id=user.id).first()):
        raise HTTPException(403, "无权查看本项目底稿审核")


def log_action(db, order, user, action, receiver, remark):
    create_workflow_log(db, work_order_id=order.id, from_status=order.current_status,
        to_status=order.current_status, action_type=action, operator_user_id=user.id, remark=remark)
    send_workflow_notification(db, project=db.get(Project, order.project_id), work_order=order,
        sender_user=user, receiver_user_id=receiver, action_name=action, comment=remark)


@router.get("/work-orders/{work_order_id}")
def get_state(work_order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = order_for(db, work_order_id)
    ensure_access(db, order, user)
    enabled = uses_parallel(db, order)
    review = db.query(Review).filter_by(work_order_id=order.id).first() if enabled else None
    rows = db.query(Submission).filter_by(review_id=review.id).order_by(Submission.round_no.desc()).all() if review else []
    history = []
    def timestamp(value):
        return value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None
    for row in rows:
        can_read = user.id == order.project_leader_id or is_admin(user) or (user.id == row.reviewer_id and row.first_entered_at is not None)
        files = db.query(WorkOrderFile).join(Attachment, Attachment.file_id == WorkOrderFile.id).filter(Attachment.submission_id == row.id).all() if can_read else []
        history.append(dict(id=row.id, round_no=row.round_no, status=row.status, reviewer_id=row.reviewer_id,
            reviewer_name=db.get(User, row.reviewer_id).real_name,
            submitted_at=timestamp(row.submitted_at), first_entered_at=timestamp(row.first_entered_at), withdrawn_at=timestamp(row.withdrawn_at),
            decided_at=timestamp(row.decided_at), reason=row.decision_reason, material_type=row.material_type,
            cloud_url=row.cloud_url if can_read else None, cloud_code=row.cloud_code if can_read else None,
            files=[dict(id=f.id, name=f.origin_file_name) for f in files]))
    return dict(enabled=enabled, status=review.status if review else "NOT_OPEN", revision=review.revision if review else 0,
        current_submission_id=review.current_submission_id if review else None, leader_id=order.project_leader_id, history=history)


@router.get("/work-orders/{work_order_id}/candidates")
def candidates(work_order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = order_for(db, work_order_id)
    ensure_leader(order, user)
    review_for(db, order)
    rows = db.query(User).join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).filter(
        User.is_active.is_(True), Role.code == "ARCHIVE_MANAGER").all()
    return [dict(id=r.id, name=r.real_name or r.username) for r in rows]


@router.post("/work-orders/{work_order_id}/files")
def upload_zip(work_order_id: int, upload: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = order_for(db, work_order_id)
    ensure_leader(order, user)
    ensure_active_project(db, order)
    review = review_for(db, order)
    if review.status not in {"DRAFT", "WITHDRAWN", "REJECTED"}:
        raise HTTPException(409, "提交后请先撤回，审核开始后不能修改")
    if not (upload.filename or "").lower().endswith(".zip") or not zipfile.is_zipfile(upload.file):
        raise HTTPException(422, "仅支持有效的ZIP文件")
    upload.file.seek(0)
    key = f"{uuid4().hex}.zip"
    path = Path(settings.local_storage_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("wb") as output:
            shutil.copyfileobj(upload.file, output, length=1024 * 1024)
        size = path.stat().st_size
    except Exception:
        path.unlink(missing_ok=True)
        raise
    row = WorkOrderFile(work_order_id=order.id, file_category=CATEGORY, business_stage=CATEGORY,
        version_no=1, is_current=True, origin_file_name=upload.filename, storage_key=key, file_size=size,
        uploaded_by=user.id, uploaded_at=datetime.now(timezone.utc), locked=True)
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        (Path(settings.local_storage_dir) / key).unlink(missing_ok=True)
        raise
    return dict(id=row.id, name=row.origin_file_name)


@router.delete("/files/{file_id}")
def discard_temporary_file(file_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(WorkOrderFile, file_id)
    if not row or row.file_category != CATEGORY:
        raise HTTPException(404, "临时底稿文件不存在")
    from app.services.operation_workpaper import lock_order
    lock_order(db, row.work_order_id)
    ensure_leader(order_for(db, row.work_order_id), user)
    if db.query(Attachment).filter_by(file_id=row.id).first():
        raise HTTPException(409, "文件已纳入历史提交记录，不可删除")
    path = Path(settings.local_storage_dir) / row.storage_key
    from app.services.committed_file_cleanup import after_commit_delete
    after_commit_delete(db, [path])
    db.delete(row)
    db.commit()
    return {"message": "临时文件已清理"}


@router.post("/work-orders/{work_order_id}/submit")
def submit(work_order_id: int, payload: Submit, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.operation_workpaper import lock_order
    lock_order(db, work_order_id)
    order = order_for(db, work_order_id)
    ensure_leader(order, user)
    ensure_active_project(db, order)
    review = review_for(db, order)
    previous = db.query(Submission).filter_by(review_id=review.id, request_id=payload.request_id).first()
    if previous:
        if previous.status in {"WITHDRAWN", "REJECTED"} or review.current_submission_id != previous.id:
            raise HTTPException(409, "原提交轮次已结束，请使用新的提交标识重新提交")
        previous_files = {r.file_id for r in db.query(Attachment).filter_by(submission_id=previous.id).all()}
        if (previous.reviewer_id != payload.reviewer_id or previous.material_type != payload.material_type or
                previous.cloud_url != payload.cloud_url or previous.cloud_code != payload.cloud_code or previous_files != set(payload.file_ids)):
            raise HTTPException(409, "重复提交标识与资料不一致，请刷新后重新提交")
        return dict(submission_id=previous.id)
    ensure_reviewer(db, payload.reviewer_id)
    files = db.query(WorkOrderFile).filter(WorkOrderFile.id.in_(payload.file_ids)).all()
    if len(files) != len(payload.file_ids) or any(f.work_order_id != order.id or f.file_category != CATEGORY or
            not f.origin_file_name.lower().endswith(".zip") for f in files):
        raise HTTPException(422, "底稿文件不属于当前工单或格式错误")
    if any(not (Path(settings.local_storage_dir) / f.storage_key).is_file() for f in files):
        raise HTTPException(422, "底稿文件已不存在，请重新上传")
    changed = db.execute(update(Review).where(Review.id == review.id, Review.revision == payload.revision,
        Review.status.in_(["DRAFT", "WITHDRAWN", "REJECTED"])).values(status="SUBMITTED", revision=Review.revision + 1),
        execution_options={"synchronize_session": False})
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "底稿已提交或状态已变化，请刷新")
    round_no = (db.query(func.max(Submission.round_no)).filter_by(review_id=review.id).scalar() or 0) + 1
    row = Submission(review_id=review.id, round_no=round_no, request_id=payload.request_id, submitter_id=user.id,
        reviewer_id=payload.reviewer_id, material_type=payload.material_type, cloud_url=payload.cloud_url,
        cloud_code=payload.cloud_code, status="SUBMITTED", submitted_at=datetime.now(timezone.utc))
    db.add(row)
    db.flush()
    order.operation_workpaper_reviewer_id = payload.reviewer_id
    db.execute(update(Review).where(Review.id == review.id).values(current_submission_id=row.id), execution_options={"synchronize_session": False})
    for f in files:
        db.add(Attachment(submission_id=row.id, file_id=f.id))
    log_action(db, order, user, "OPERATION_WORKPAPER_SUBMIT", row.reviewer_id, "操作类底稿已提交，请进入底稿审核页面处理")
    db.commit()
    return dict(submission_id=row.id)


def submission_context(db, submission_id):
    row = db.get(Submission, submission_id)
    if not row:
        raise HTTPException(404, "提交记录不存在")
    review = db.get(Review, row.review_id)
    order = order_for(db, review.work_order_id)
    ensure_active_project(db, order)
    if review.current_submission_id != row.id:
        raise HTTPException(409, "此记录不是当前审核轮次")
    return order, review, row


@router.post("/submissions/{submission_id}/enter")
def enter(submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order, review, row = submission_context(db, submission_id)
    if row.reviewer_id != user.id:
        raise HTTPException(403, "仅本轮指定的底稿审核人员可进入审核")
    ensure_reviewer(db, user.id)
    if review.status == "IN_REVIEW" and row.first_entered_at:
        return {"message": "已进入本轮审核"}
    transition(db, review, row, "SUBMITTED", "IN_REVIEW", user.id)
    log_action(db, order, user, "OPERATION_WORKPAPER_ENTER", order.project_leader_id, "底稿审核人员已进入审核页面，不能撤回")
    db.commit()
    return {"message": "已进入底稿审核"}


@router.post("/submissions/{submission_id}/withdraw")
def withdraw(submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order, review, row = submission_context(db, submission_id)
    ensure_leader(order, user)
    transition(db, review, row, "SUBMITTED", "WITHDRAWN", user.id)
    log_action(db, order, user, "OPERATION_WORKPAPER_WITHDRAW", row.reviewer_id, "项目负责人已撤回本轮底稿审核")
    db.commit()
    return {"message": "已撤回，可修改资料后重新提交"}


@router.post("/submissions/{submission_id}/decision")
def decide(submission_id: int, payload: Decision, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.operation_workpaper import lock_order
    target_review = db.query(Review).join(Submission, Submission.review_id == Review.id).filter(Submission.id == submission_id).first()
    if not target_review:
        raise HTTPException(404, "提交记录不存在")
    lock_order(db, target_review.work_order_id)
    db.expire_all()
    order, review, row = submission_context(db, submission_id)
    if row.reviewer_id != user.id:
        raise HTTPException(403, "仅本轮指定的底稿审核人员可审核")
    ensure_reviewer(db, user.id)
    reason = payload.reason.strip()
    if payload.action == "REJECT" and not reason:
        raise HTTPException(422, "退回时必须填写退回理由")
    target = "APPROVED" if payload.action == "APPROVE" else "REJECTED"
    transition(db, review, row, "IN_REVIEW", target, user.id)
    row.decision_reason = reason
    if target == "APPROVED" and order.current_status == "WAIT_PARALLEL_WORKPAPER":
        order.current_status = "WAIT_OWNER_SIGNOFF_UPLOAD"
        order.current_handler_user_id = order.project_leader_id
        order.signoff_status = "WAIT_UPLOAD"
    log_action(db, order, user, "OPERATION_WORKPAPER_" + target, order.project_leader_id, reason or "操作类底稿审核通过")
    db.commit()
    return {"message": "底稿审核通过" if target == "APPROVED" else "已退回项目负责人补充"}
