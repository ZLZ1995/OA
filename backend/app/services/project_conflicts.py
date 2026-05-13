from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.project_conflict import ProjectConflictRecord, ProjectConflictSnapshot
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.services.project_flow import get_project_leader_display_name

COMPANY_SUFFIXES = [
    "有限责任公司",
    "股份有限公司",
    "集团有限公司",
    "实业有限公司",
    "有限公司",
    "股份公司",
    "合伙企业",
    "特殊普通合伙",
    "普通合伙",
    "有限合伙",
]


def normalize_client_name(name: str | None) -> str:
    text = (name or "").strip()
    for suffix in COMPANY_SUFFIXES:
        text = text.replace(suffix, "")
    return "".join(ch for ch in text if not ch.isspace() and ch not in "（）()【】[]-—_·.,，。")


def has_four_shared_chars(left: str, right: str) -> bool:
    left_chars = set(left)
    right_chars = set(right)
    return len(left_chars & right_chars) >= 4


def get_unresolved_conflicts(db: Session, project_id: int) -> list[ProjectConflictRecord]:
    return (
        db.query(ProjectConflictRecord)
        .filter(
            ProjectConflictRecord.status.in_(["PENDING", "CONFIRMED"]),
            or_(ProjectConflictRecord.project_a_id == project_id, ProjectConflictRecord.project_b_id == project_id),
        )
        .order_by(ProjectConflictRecord.id.desc())
        .all()
    )


def assert_project_can_submit_review(db: Session, project: Project) -> None:
    if project.project_amount is None or project.project_amount < 0 or project.valuation_base_date is None:
        raise HTTPException(status_code=400, detail="请先在项目基本信息中填写项目金额和评估基准日")
    if project.duplicate_delete_required:
        raise HTTPException(status_code=400, detail="该项目已被管理员判定为重复项目，请先删除")
    if get_unresolved_conflicts(db, project.id):
        raise HTTPException(status_code=400, detail="该项目存在未处理的重复项目提醒，请等待管理员确认")


def _snapshot_payload(db: Session, project: Project, work_order: WorkOrder, uploaded_at: datetime) -> dict[str, object]:
    leader_name = db.query(User.real_name).filter(User.id == project.project_leader_id).scalar()
    creator = db.query(User).filter(User.id == project.business_user_id).first()
    return {
        "project_id": project.id,
        "work_order_id": work_order.id,
        "project_no": project.project_code,
        "project_name": project.project_name,
        "client_name": project.client_name,
        "normalized_client_name": normalize_client_name(project.client_name),
        "project_amount": float(project.project_amount or 0),
        "valuation_base_date": project.valuation_base_date,
        "project_leader_display_name": get_project_leader_display_name(project, leader_name) or "",
        "creator_user_id": project.business_user_id,
        "creator_username": creator.username if creator else None,
        "contract_uploaded_at": uploaded_at,
    }


def upsert_conflict_snapshot_and_detect(db: Session, project: Project, work_order: WorkOrder, uploaded_at: datetime) -> None:
    if project.project_amount is None or project.project_amount < 0 or project.valuation_base_date is None:
        return
    payload = _snapshot_payload(db, project, work_order, uploaded_at)
    snapshot = db.query(ProjectConflictSnapshot).filter(ProjectConflictSnapshot.project_id == project.id).first()
    if snapshot:
        for key, value in payload.items():
            setattr(snapshot, key, value)
    else:
        snapshot = ProjectConflictSnapshot(**payload)
        db.add(snapshot)
        db.flush()

    existing_snapshots = (
        db.query(ProjectConflictSnapshot)
        .join(Project, Project.id == ProjectConflictSnapshot.project_id)
        .filter(
            ProjectConflictSnapshot.project_id != project.id,
            Project.deleted_at.is_(None),
            Project.duplicate_delete_required.is_(False),
            ProjectConflictSnapshot.project_amount == snapshot.project_amount,
            ProjectConflictSnapshot.valuation_base_date == snapshot.valuation_base_date,
        )
        .all()
    )
    for other in existing_snapshots:
        if other.project_leader_display_name == snapshot.project_leader_display_name:
            continue
        if not has_four_shared_chars(snapshot.normalized_client_name, other.normalized_client_name):
            continue
        left_id, right_id = sorted([snapshot.project_id, other.project_id])
        exists = (
            db.query(ProjectConflictRecord)
            .filter(
                ProjectConflictRecord.project_a_id == left_id,
                ProjectConflictRecord.project_b_id == right_id,
                ProjectConflictRecord.status.in_(["PENDING", "CONFIRMED"]),
            )
            .first()
        )
        if exists:
            continue
        db.add(
            ProjectConflictRecord(
                project_a_id=left_id,
                project_b_id=right_id,
                snapshot_a_id=snapshot.id if snapshot.project_id == left_id else other.id,
                snapshot_b_id=snapshot.id if snapshot.project_id == right_id else other.id,
                status="PENDING",
            )
        )


def mark_project_duplicate_deleted(db: Session, project: Project) -> None:
    project.deleted_at = datetime.now()
    project.status = "DELETED"
    files = (
        db.query(WorkOrderFile)
        .join(WorkOrder, WorkOrder.id == WorkOrderFile.work_order_id)
        .filter(WorkOrder.project_id == project.id)
        .all()
    )
    for file_row in files:
        if file_row.storage_key:
            path = Path(file_row.storage_key)
            if not path.is_absolute():
                path = Path(settings.local_storage_dir) / file_row.storage_key
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
    conflicts = get_unresolved_conflicts(db, project.id)
    for conflict in conflicts:
        if conflict.delete_project_id == project.id or project.duplicate_delete_required:
            conflict.status = "RESOLVED"
            conflict.resolved_at = datetime.now()
