"""Bounded garbage collection for abandoned ZIP uploads, never review history."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import exists
from app.core.config import settings
from app.models.work_order_file import WorkOrderFile
from app.models.operation_workpaper import OperationWorkpaperSubmissionFile as Attachment
from app.services.operation_workpaper import lock_order
from app.services.committed_file_cleanup import after_commit_delete


def collect_expired_workpaper_files(db, *, now=None, limit=500):
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=24)
    def candidates():
        return db.query(WorkOrderFile).filter(
            WorkOrderFile.file_category == "OPERATION_WORKPAPER",
            WorkOrderFile.uploaded_at < cutoff,
            ~exists().where(Attachment.file_id == WorkOrderFile.id),
        )
    ids = [r.id for r in candidates().order_by(WorkOrderFile.id).limit(limit)]
    count = 0
    for file_id in ids:
        row = db.get(WorkOrderFile, file_id)
        if row is None:
            continue
        lock_order(db, row.work_order_id)
        # A submit may have acquired the lock first: recheck references after locking.
        row = candidates().filter(WorkOrderFile.id == file_id).populate_existing().first()
        if row is None:
            continue
        root = Path(settings.local_storage_dir).resolve()
        path = (root / row.storage_key).resolve()
        if not path.is_relative_to(root):
            continue
        after_commit_delete(db, [path])
        db.delete(row)
        db.flush()
        count += 1
    return count


def cleanup_expired_workpaper_files():
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        count = collect_expired_workpaper_files(db)
        db.commit()
        return count
