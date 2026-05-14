from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.issue_feedback import IssueFeedback
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.issue_feedback import (
    IssueFeedbackCreate,
    IssueFeedbackItem,
    IssueFeedbackListResponse,
    IssueFeedbackSuspendRequest,
)
from app.services.notification_service import create_notification

router = APIRouter(prefix="/issue-feedbacks", tags=["问题反馈"])


def _admin_users(db: Session) -> list[User]:
    return (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(User.is_active.is_(True), Role.code == "ADMIN")
        .distinct()
        .all()
    )


def _user_label(db: Session, user_id: int | None) -> str | None:
    if not user_id:
        return None
    row = db.query(User).filter(User.id == user_id).first()
    return row.real_name if row else None


def _serialize(db: Session, row: IssueFeedback) -> IssueFeedbackItem:
    submitter = db.query(User).filter(User.id == row.submitter_user_id).first()
    return IssueFeedbackItem(
        id=row.id,
        project_no=row.project_no,
        process_step=row.process_step,
        detail=row.detail,
        status=row.status,
        submitter_user_id=row.submitter_user_id,
        submitter_user_name=submitter.real_name if submitter else "-",
        submitter_username=submitter.username if submitter else "-",
        created_at=row.created_at,
        handled_by_name=_user_label(db, row.handled_by),
        handled_at=row.handled_at,
        suspended_by_name=_user_label(db, row.suspended_by),
        suspended_at=row.suspended_at,
        suspend_note=row.suspend_note,
    )


@router.post("", response_model=IssueFeedbackItem, status_code=status.HTTP_201_CREATED)
def create_issue_feedback(
    payload: IssueFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IssueFeedbackItem:
    row = IssueFeedback(
        submitter_user_id=current_user.id,
        project_no=payload.project_no.strip(),
        process_step=payload.process_step.strip(),
        detail=payload.detail.strip(),
        status="PENDING",
    )
    if not row.project_no or not row.process_step or not row.detail:
        raise HTTPException(status_code=400, detail="请完整填写项目编号、流程环节和问题详细情况")
    db.add(row)
    db.flush()

    for admin in _admin_users(db):
        create_notification(
            db,
            user_id=admin.id,
            biz_type="ISSUE_FEEDBACK",
            biz_id=row.id,
            title="收到新的问题反馈",
            content=f"{current_user.real_name} 提交了项目 {row.project_no} 的问题反馈，请及时查看。",
            link_type="ISSUE_FEEDBACK",
            link_target_id=row.id,
        )
    db.commit()
    db.refresh(row)
    return _serialize(db, row)


@router.get("", response_model=IssueFeedbackListResponse)
def list_issue_feedbacks(
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> IssueFeedbackListResponse:
    rows = db.query(IssueFeedback).order_by(IssueFeedback.created_at.desc(), IssueFeedback.id.desc()).all()
    return IssueFeedbackListResponse(items=[_serialize(db, row) for row in rows])


@router.get("/tech-support/excel")
def export_tech_support_excel(
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
):
    try:
        from openpyxl import Workbook
    except ModuleNotFoundError as exc:
        raise HTTPException(status_code=500, detail="Excel导出依赖 openpyxl 未安装，请安装后重试") from exc

    rows = (
        db.query(IssueFeedback)
        .filter(IssueFeedback.status == "TECH_SUPPORT")
        .order_by(IssueFeedback.suspended_at.desc(), IssueFeedback.id.desc())
        .all()
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "需技术支持"
    ws.append(["提交人", "提交账号", "提交时间", "项目编号", "流程环节", "问题详情", "处理人", "挂起时间", "挂起说明"])
    for row in rows:
        item = _serialize(db, row)
        ws.append([
            item.submitter_user_name,
            item.submitter_username,
            item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else "",
            item.project_no,
            item.process_step,
            item.detail,
            item.suspended_by_name or "",
            item.suspended_at.strftime("%Y-%m-%d %H:%M") if item.suspended_at else "",
            item.suspend_note or "",
        ])
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=issue-feedback-tech-support.xlsx"},
    )


@router.get("/{feedback_id}", response_model=IssueFeedbackItem)
def get_issue_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> IssueFeedbackItem:
    row = db.query(IssueFeedback).filter(IssueFeedback.id == feedback_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="问题反馈不存在")
    return _serialize(db, row)


@router.post("/{feedback_id}/resolve", response_model=IssueFeedbackItem)
def resolve_issue_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> IssueFeedbackItem:
    row = db.query(IssueFeedback).filter(IssueFeedback.id == feedback_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="问题反馈不存在")
    row.status = "RESOLVED"
    row.handled_by = current_user.id
    row.handled_at = datetime.now()
    create_notification(
        db,
        user_id=row.submitter_user_id,
        biz_type="ISSUE_FEEDBACK",
        biz_id=row.id,
        title="问题反馈已处理",
        content="您反馈的问题已处理，请查看系统最新状态。",
        link_type="ISSUE_FEEDBACK",
        link_target_id=row.id,
    )
    db.commit()
    db.refresh(row)
    return _serialize(db, row)


@router.post("/{feedback_id}/suspend", response_model=IssueFeedbackItem)
def suspend_issue_feedback(
    feedback_id: int,
    payload: IssueFeedbackSuspendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> IssueFeedbackItem:
    row = db.query(IssueFeedback).filter(IssueFeedback.id == feedback_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="问题反馈不存在")
    row.status = "TECH_SUPPORT"
    row.suspended_by = current_user.id
    row.suspended_at = datetime.now()
    row.suspend_note = (payload.suspend_note or "").strip() or None
    db.commit()
    db.refresh(row)
    return _serialize(db, row)
