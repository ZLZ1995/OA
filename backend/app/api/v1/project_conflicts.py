from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.project_conflict import ProjectConflictRecord, ProjectConflictSnapshot
from app.models.user import User
from app.schemas.project_conflict import (
    ProjectConflictDecisionRequest,
    ProjectConflictListResponse,
    ProjectConflictRecordItem,
    ProjectConflictSnapshotItem,
)

router = APIRouter(prefix="/project-conflicts", tags=["项目冲突提醒"])


def _format_date(value) -> str:
    return value.strftime("%Y-%m-%d") if value else ""


def _format_contract_time(value) -> str:
    return value.strftime("%Y年%m月%d日 %H:%M") if value else ""


def _snapshot_item(snapshot: ProjectConflictSnapshot) -> ProjectConflictSnapshotItem:
    return ProjectConflictSnapshotItem(
        project_id=snapshot.project_id,
        project_no=snapshot.project_no,
        project_name=snapshot.project_name,
        client_name=snapshot.client_name,
        project_amount=snapshot.project_amount,
        valuation_base_date=_format_date(snapshot.valuation_base_date),
        project_leader_display_name=snapshot.project_leader_display_name,
        creator_username=snapshot.creator_username,
        contract_uploaded_at=_format_contract_time(snapshot.contract_uploaded_at),
    )


def _record_item(db: Session, record: ProjectConflictRecord) -> ProjectConflictRecordItem:
    snapshot_a = db.query(ProjectConflictSnapshot).filter(ProjectConflictSnapshot.id == record.snapshot_a_id).first()
    snapshot_b = db.query(ProjectConflictSnapshot).filter(ProjectConflictSnapshot.id == record.snapshot_b_id).first()
    if not snapshot_a or not snapshot_b:
        raise HTTPException(status_code=500, detail="项目冲突快照缺失")
    return ProjectConflictRecordItem(
        id=record.id,
        status=record.status,
        decision=record.decision,
        kept_project_id=record.kept_project_id,
        delete_project_id=record.delete_project_id,
        resolve_comment=record.resolve_comment,
        created_at=record.created_at,
        decided_at=record.decided_at,
        resolved_at=record.resolved_at,
        project_a=_snapshot_item(snapshot_a),
        project_b=_snapshot_item(snapshot_b),
    )


def _query_conflicts(db: Session, status: str | None = None) -> list[ProjectConflictRecord]:
    query = db.query(ProjectConflictRecord)
    if status:
        query = query.filter(ProjectConflictRecord.status == status)
    return query.order_by(ProjectConflictRecord.created_at.desc(), ProjectConflictRecord.id.desc()).all()


@router.get("", response_model=ProjectConflictListResponse)
def list_project_conflicts(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> ProjectConflictListResponse:
    rows = _query_conflicts(db, status)
    return ProjectConflictListResponse(items=[_record_item(db, row) for row in rows])


@router.post("/{conflict_id}/not-conflict", response_model=ProjectConflictRecordItem)
def mark_not_conflict(
    conflict_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> ProjectConflictRecordItem:
    record = db.query(ProjectConflictRecord).filter(ProjectConflictRecord.id == conflict_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="冲突记录不存在")
    record.status = "RESOLVED"
    record.decision = "NOT_CONFLICT"
    record.decided_by = current_user.id
    record.decided_at = datetime.now()
    record.resolved_at = datetime.now()
    record.resolve_comment = None
    db.commit()
    db.refresh(record)
    return _record_item(db, record)


@router.post("/{conflict_id}/confirm", response_model=ProjectConflictRecordItem)
def confirm_conflict(
    conflict_id: int,
    payload: ProjectConflictDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> ProjectConflictRecordItem:
    record = db.query(ProjectConflictRecord).filter(ProjectConflictRecord.id == conflict_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="冲突记录不存在")
    if not payload.kept_project_id or payload.kept_project_id not in {record.project_a_id, record.project_b_id}:
        raise HTTPException(status_code=400, detail="请选择本次冲突中要保留的项目")
    if not payload.comment:
        raise HTTPException(status_code=400, detail="确认构成项目冲突时必须填写说明")
    delete_project_id = record.project_b_id if payload.kept_project_id == record.project_a_id else record.project_a_id
    delete_project = db.query(Project).filter(Project.id == delete_project_id, Project.deleted_at.is_(None)).first()
    if not delete_project:
        raise HTTPException(status_code=404, detail="待删除项目不存在")
    delete_project.duplicate_delete_required = True
    delete_project.duplicate_delete_reason = payload.comment
    record.status = "CONFIRMED"
    record.decision = "CONFLICT"
    record.kept_project_id = payload.kept_project_id
    record.delete_project_id = delete_project_id
    record.decided_by = current_user.id
    record.decided_at = datetime.now()
    record.resolve_comment = payload.comment
    db.commit()
    db.refresh(record)
    return _record_item(db, record)


@router.get("/excel")
def export_project_conflicts_excel(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
):
    try:
        from openpyxl import Workbook
    except ModuleNotFoundError as exc:
        raise HTTPException(status_code=500, detail="Excel导出依赖 openpyxl 未安装，请安装后重试") from exc

    rows = [_record_item(db, row) for row in _query_conflicts(db, status)]
    wb = Workbook()
    ws = wb.active
    ws.title = "项目冲突提醒"
    headers = ["状态", "项目A编号", "项目A名称", "项目A客户", "项目A金额", "项目A基准日", "项目A负责人", "项目A合同上传时间", "项目B编号", "项目B名称", "项目B客户", "项目B金额", "项目B基准日", "项目B负责人", "项目B合同上传时间", "处理说明"]
    ws.append(headers)
    for item in rows:
        ws.append([
            item.status,
            item.project_a.project_no,
            item.project_a.project_name,
            item.project_a.client_name,
            item.project_a.project_amount,
            item.project_a.valuation_base_date,
            item.project_a.project_leader_display_name,
            item.project_a.contract_uploaded_at,
            item.project_b.project_no,
            item.project_b.project_name,
            item.project_b.client_name,
            item.project_b.project_amount,
            item.project_b.valuation_base_date,
            item.project_b.project_leader_display_name,
            item.project_b.contract_uploaded_at,
            item.resolve_comment or "",
        ])
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=project-conflicts.xlsx"},
    )
