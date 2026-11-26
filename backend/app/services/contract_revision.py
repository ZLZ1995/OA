"""Contract review state when the report has advanced independently."""
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.contract_review_record import ContractReviewRecord
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile

APPROVALS = {"APPROVE_CONTRACT", "APPROVE_AND_TRANSFER_PRINT_ROOM"}
REVIEW_STATES = {
    "REOPEN_CONTRACT_REVIEW": "WAIT_CONTRACT_REVIEW_SUBMIT",
    "SUBMIT_CONTRACT": "CONTRACT_REVIEWING",
    "REJECT_CONTRACT": "CONTRACT_REJECTED",
    **dict.fromkeys(APPROVALS, "CONTRACT_APPROVED"),
}
CONTRACT_STAGES = {
    "WORK_ORDER_CREATED", "WAIT_CONTRACT_UPLOAD", "CONTRACT_UPLOADED",
    "WAIT_CONTRACT_REVIEW_SUBMIT", "CONTRACT_REVIEWING", "CONTRACT_REJECTED",
    "CONTRACT_APPROVED", "WAIT_PRINT_ROOM_PROCESS", "WAIT_PROJECT_LEADER_CONTRACT_CONFIRM",
    "CONTRACT_PROCESS_COMPLETED",
}
PENDING_DELETE = "CONTRACT_DELETE_PENDING"
DELETED = "CONTRACT_SUPERSEDED"


def lock_work_order(db: Session, order_id: int):
    query = db.query(WorkOrder).filter(WorkOrder.id == order_id)
    if db.get_bind().dialect.name == "sqlite":
        # SQLite ignores FOR UPDATE. Acquire its write lock before reading the state.
        query.update({WorkOrder.updated_at: WorkOrder.updated_at}, synchronize_session=False)
    return query.populate_existing().with_for_update().first()


def last_review(db: Session, order_id: int):
    return (db.query(ContractReviewRecord)
            .filter(ContractReviewRecord.work_order_id == order_id,
                    ContractReviewRecord.action_type.in_(REVIEW_STATES))
            .order_by(ContractReviewRecord.id.desc()).first())


def contract_status(db: Session, order: WorkOrder):
    if order.current_status in CONTRACT_STAGES:
        return order.current_status
    record = last_review(db, order.id)
    return REVIEW_STATES[record.action_type] if record else None


def set_contract_status(order, status, handler_id):
    if order.current_status in CONTRACT_STAGES:
        order.current_status = status
        order.current_handler_user_id = handler_id


def purge_replaced_contracts(db: Session, file_id=None):
    query = db.query(WorkOrderFile).filter_by(file_category="CONTRACT_DRAFT",
                                             is_current=False, source_type=PENDING_DELETE)
    if file_id is not None:
        query = query.filter_by(id=file_id)
    root = Path(settings.local_storage_dir).resolve()
    for row in query.all():
        path = (root / row.storage_key).resolve()
        if path.parent != root:
            logging.getLogger(__name__).error("Invalid contract storage path for file %s", row.id)
            continue
        try:
            shared = db.query(WorkOrderFile.id).filter(
                WorkOrderFile.id != row.id, WorkOrderFile.storage_key == row.storage_key,
                WorkOrderFile.source_type.notin_([PENDING_DELETE, DELETED])).first()
            if not shared:
                path.unlink(missing_ok=True)
            row.source_type = DELETED
        except OSError:
            logging.getLogger(__name__).exception("Retry contract cleanup for file %s", row.id)
    db.commit()


def retry_contract_cleanup():
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        purge_replaced_contracts(db)
