from sqlalchemy.orm import Session

from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile

SIGNOFF_SOURCE_CATEGORIES = ("REPORT_ZIP", "FORMAL_REPORT", "FINAL_CONTRACT_SCAN")
ARCHIVE_STAGE = "ARCHIVE"
SIGNOFF_SYNC_SOURCE_TYPE = "SIGNOFF_SYNC"


def is_signoff_source_category(file_category: str) -> bool:
    return file_category in SIGNOFF_SOURCE_CATEGORIES


def get_latest_signoff_source_files(db: Session, work_order_id: int) -> list[WorkOrderFile]:
    rows: list[WorkOrderFile] = []
    for category in SIGNOFF_SOURCE_CATEGORIES:
        row = (
            db.query(WorkOrderFile)
            .filter(
                WorkOrderFile.work_order_id == work_order_id,
                WorkOrderFile.file_category == category,
                WorkOrderFile.is_current.is_(True),
            )
            .order_by(WorkOrderFile.version_no.desc())
            .first()
        )
        if row:
            rows.append(row)
    return rows


def _next_archive_sync_version(db: Session, work_order_id: int, file_category: str) -> int:
    latest = (
        db.query(WorkOrderFile)
        .filter(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.file_category == file_category,
            WorkOrderFile.business_stage == ARCHIVE_STAGE,
            WorkOrderFile.source_type == SIGNOFF_SYNC_SOURCE_TYPE,
        )
        .order_by(WorkOrderFile.version_no.desc())
        .first()
    )
    return 1 if not latest else latest.version_no + 1


def upsert_archive_synced_file(db: Session, work_order: WorkOrder, source_file: WorkOrderFile) -> WorkOrderFile:
    existing = (
        db.query(WorkOrderFile)
        .filter(
            WorkOrderFile.work_order_id == work_order.id,
            WorkOrderFile.file_category == source_file.file_category,
            WorkOrderFile.business_stage == ARCHIVE_STAGE,
            WorkOrderFile.source_type == SIGNOFF_SYNC_SOURCE_TYPE,
        )
        .order_by(WorkOrderFile.version_no.desc())
        .first()
    )
    if existing:
        existing.origin_file_name = source_file.origin_file_name
        existing.storage_key = source_file.storage_key
        existing.file_size = source_file.file_size
        existing.uploaded_by = source_file.uploaded_by
        existing.uploaded_at = source_file.uploaded_at
        existing.is_current = True
        existing.locked = True
        existing.source_file_id = source_file.id
        return existing

    row = WorkOrderFile(
        work_order_id=work_order.id,
        file_category=source_file.file_category,
        business_stage=ARCHIVE_STAGE,
        version_no=_next_archive_sync_version(db, work_order.id, source_file.file_category),
        is_current=True,
        origin_file_name=source_file.origin_file_name,
        storage_key=source_file.storage_key,
        file_size=source_file.file_size,
        uploaded_by=source_file.uploaded_by,
        uploaded_at=source_file.uploaded_at,
        source_type=SIGNOFF_SYNC_SOURCE_TYPE,
        source_file_id=source_file.id,
        locked=True,
    )
    db.add(row)
    db.flush()
    return row


def sync_signoff_files_to_archive(db: Session, work_order: WorkOrder, operator_user_id: int | None = None) -> list[WorkOrderFile]:
    rows: list[WorkOrderFile] = []
    for source_file in get_latest_signoff_source_files(db, work_order.id):
        rows.append(upsert_archive_synced_file(db, work_order, source_file))
    return rows


def refresh_archive_synced_file_by_source(db: Session, source_file: WorkOrderFile) -> WorkOrderFile | None:
    if not is_signoff_source_category(source_file.file_category):
        return None
    work_order = db.query(WorkOrder).filter(WorkOrder.id == source_file.work_order_id).first()
    if not work_order:
        return None
    return upsert_archive_synced_file(db, work_order, source_file)
