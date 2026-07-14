from sqlalchemy.orm import Session

from app.models.contract_review_record import ContractReviewRecord
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.models.workflow_log import WorkflowLog
from app.workflows.states import WorkOrderStatus

STAMPED_CONTRACT_SCAN_FILE_CATEGORY = "STAMPED_CONTRACT_SCAN"
STAMPED_CONTRACT_SCAN_STAGE = "PRINT_ROOM_CONTRACT_SCAN"

PRINT_ROOM_TRANSFER_ACTIONS = {
    "APPROVE_AND_TRANSFER_PRINT_ROOM",
    "TRANSFER_APPROVED_PRINT_ROOM",
}


def get_contract_print_room_status(db: Session, work_order: WorkOrder | None) -> str | None:
    if not work_order:
        return None
    if work_order.current_status in {
        WorkOrderStatus.WAIT_PRINT_ROOM_PROCESS.value,
        WorkOrderStatus.WAIT_PROJECT_LEADER_CONTRACT_CONFIRM.value,
        WorkOrderStatus.CONTRACT_PROCESS_COMPLETED.value,
    }:
        return work_order.current_status
    transfer_record = (
        db.query(ContractReviewRecord)
        .filter(
            ContractReviewRecord.work_order_id == work_order.id,
            ContractReviewRecord.action_type.in_(PRINT_ROOM_TRANSFER_ACTIONS),
        )
        .order_by(ContractReviewRecord.created_at.desc(), ContractReviewRecord.id.desc())
        .first()
    )
    if not transfer_record:
        return None

    latest_log = (
        db.query(WorkflowLog)
        .filter(
            WorkflowLog.work_order_id == work_order.id,
            WorkflowLog.action_type.in_(
                [
                    "RETURN_TO_PRINT_ROOM",
                    "SEND_TO_PROJECT_LEADER_CONFIRM",
                    "CONFIRM_CONTRACT_COMPLETE",
                    "REOPEN_CONTRACT_REVIEW",
                ]
            ),
        )
        .order_by(WorkflowLog.created_at.desc(), WorkflowLog.id.desc())
        .first()
    )
    if latest_log:
        if latest_log.action_type == "RETURN_TO_PRINT_ROOM":
            return WorkOrderStatus.WAIT_PRINT_ROOM_PROCESS.value
        if latest_log.action_type == "SEND_TO_PROJECT_LEADER_CONFIRM":
            return WorkOrderStatus.WAIT_PROJECT_LEADER_CONTRACT_CONFIRM.value
        if latest_log.action_type == "CONFIRM_CONTRACT_COMPLETE":
            return WorkOrderStatus.CONTRACT_PROCESS_COMPLETED.value
        if latest_log.action_type == "REOPEN_CONTRACT_REVIEW":
            return None
    return WorkOrderStatus.WAIT_PRINT_ROOM_PROCESS.value


def has_current_stamped_contract_scan(db: Session, work_order_id: int) -> bool:
    return (
        db.query(WorkOrderFile.id)
        .filter(
            WorkOrderFile.work_order_id == work_order_id,
            WorkOrderFile.file_category == STAMPED_CONTRACT_SCAN_FILE_CATEGORY,
            WorkOrderFile.business_stage == STAMPED_CONTRACT_SCAN_STAGE,
            WorkOrderFile.is_current.is_(True),
        )
        .first()
        is not None
    )
