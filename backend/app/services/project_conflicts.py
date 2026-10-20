from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.project import Project
from app.models.project_conflict import ProjectConflictRecord, ProjectConflictSnapshot
from app.models.project_handover import ProjectConflictEvaluation
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
    ignored = set("（）()【】[]-—·.,，。、 ")
    return "".join(ch for ch in text if not ch.isspace() and ch not in ignored)


def has_four_shared_chars(left: str, right: str) -> bool:
    if left and left == right:
        return True
    left_chars = set(left)
    right_chars = set(right)
    return len(left_chars & right_chars) >= 4


def get_unresolved_conflicts(db: Session, project_id: int) -> list[ProjectConflictRecord]:
    rows = (
        db.query(ProjectConflictRecord)
        .filter(
            ProjectConflictRecord.status.in_(["PENDING", "CONFIRMED"]),
            or_(ProjectConflictRecord.project_a_id == project_id, ProjectConflictRecord.project_b_id == project_id),
        )
        .order_by(ProjectConflictRecord.id.desc())
        .all()
    )
    result = []
    for row in rows:
        a, b = db.get(Project, row.project_a_id), db.get(Project, row.project_b_id)
        if not a or not b or a.deleted_at or b.deleted_at:
            continue
        if row.status == "CONFIRMED" and row.kept_project_id == project_id:
            continue
        evaluation = db.query(ProjectConflictEvaluation).filter_by(conflict_id=row.id).first()
        if row.status == "PENDING" and evaluation:
            sa, sb = db.get(ProjectConflictSnapshot, row.snapshot_a_id), db.get(ProjectConflictSnapshot, row.snapshot_b_id)
            if sa and sb and _evidence(sa, sb)[0] != evaluation.fingerprint:
                continue
        result.append(row)
    return result


def _evidence(a, b):
    data = [{"project_id": s.project_id, "client": s.normalized_client_name,
             "amount": str(s.project_amount), "base_date": str(s.valuation_base_date)}
            for s in sorted((a, b), key=lambda s: s.project_id)]
    evidence = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(evidence.encode()).hexdigest(), evidence


def is_current_conflict(db: Session, record: ProjectConflictRecord) -> bool:
    evaluation = db.query(ProjectConflictEvaluation).filter_by(conflict_id=record.id).first()
    if not evaluation:
        return True
    a = db.get(ProjectConflictSnapshot, record.snapshot_a_id)
    b = db.get(ProjectConflictSnapshot, record.snapshot_b_id)
    return bool(a and b and _evidence(a, b)[0] == evaluation.fingerprint)


def bootstrap_legacy_conflicts(db: Session) -> None:
    """Capture legacy decisions before mutable snapshots change; retain old records."""
    pairs = db.query(ProjectConflictRecord.project_a_id, ProjectConflictRecord.project_b_id).distinct().all()
    for left, right in pairs:
        if db.query(ProjectConflictEvaluation.id).filter_by(project_a_id=left, project_b_id=right).first():
            continue
        rows = db.query(ProjectConflictRecord).filter_by(project_a_id=left, project_b_id=right).order_by(ProjectConflictRecord.id.desc()).all()
        decisions = [r for r in rows if r.decided_at]
        record = max(decisions, key=lambda r: (r.decided_at, r.id)) if decisions else rows[0]
        a, b = db.get(ProjectConflictSnapshot, record.snapshot_a_id), db.get(ProjectConflictSnapshot, record.snapshot_b_id)
        if not a or not b:
            continue
        fingerprint, evidence = _evidence(a, b)
        try:
            with db.begin_nested():
                db.add(ProjectConflictEvaluation(project_a_id=left, project_b_id=right,
                        fingerprint=fingerprint, evidence=evidence, conflict_id=record.id))
                db.flush()
        except IntegrityError:
            if db.query(ProjectConflictEvaluation.id).filter_by(project_a_id=left,
                    project_b_id=right, fingerprint=fingerprint).first():
                continue
            raise
        for duplicate in rows:
            if duplicate.id != record.id and duplicate.status == "PENDING":
                duplicate.status = "RESOLVED"
                duplicate.resolved_at = datetime.now()
                duplicate.resolve_comment = f"旧重复提醒归并，适用判定记录 #{record.id}"
                duplicate.decision = "SUPERSEDED"
    db.flush()


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
    bootstrap_legacy_conflicts(db)
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
        if not has_four_shared_chars(snapshot.normalized_client_name, other.normalized_client_name):
            continue
        left_id, right_id = sorted([snapshot.project_id, other.project_id])
        fingerprint, evidence = _evidence(snapshot, other)
        exists = db.query(ProjectConflictEvaluation.id).filter_by(
            project_a_id=left_id, project_b_id=right_id, fingerprint=fingerprint).first()
        if exists:
            continue
        try:
            with db.begin_nested():
                record = ProjectConflictRecord(
                    project_a_id=left_id,
                    project_b_id=right_id,
                    snapshot_a_id=snapshot.id if snapshot.project_id == left_id else other.id,
                    snapshot_b_id=snapshot.id if snapshot.project_id == right_id else other.id,
                    status="PENDING",
                )
                db.add(record)
                db.flush()
                db.add(ProjectConflictEvaluation(project_a_id=left_id, project_b_id=right_id,
                    fingerprint=fingerprint, evidence=evidence, conflict_id=record.id))
                db.flush()
        except IntegrityError:
            # A concurrent upload already registered this exact pair and evidence.
            if not db.query(ProjectConflictEvaluation.id).filter_by(project_a_id=left_id,
                    project_b_id=right_id, fingerprint=fingerprint).first():
                raise


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
