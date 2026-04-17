from app.workflows.states import WorkOrderStatus


ALLOWED_TRANSITIONS: dict[WorkOrderStatus, set[WorkOrderStatus]] = {
    WorkOrderStatus.PROJECT_CREATED: {WorkOrderStatus.WORK_ORDER_CREATED},
    WorkOrderStatus.WORK_ORDER_CREATED: {WorkOrderStatus.CONTRACT_UPLOADED},
    WorkOrderStatus.CONTRACT_UPLOADED: {WorkOrderStatus.WAIT_PRINTROOM_OFFICIAL_CONTRACT},
    WorkOrderStatus.WAIT_PRINTROOM_OFFICIAL_CONTRACT: {WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT},
    WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT: {WorkOrderStatus.FIRST_REVIEWING},
    WorkOrderStatus.FIRST_REVIEWING: {
        WorkOrderStatus.FIRST_REVIEW_REJECTED,
        WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND,
    },
    WorkOrderStatus.FIRST_REVIEW_REJECTED: {WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT},
    WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND: {WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT},
    WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT: {WorkOrderStatus.SECOND_REVIEWING},
    WorkOrderStatus.SECOND_REVIEWING: {
        WorkOrderStatus.SECOND_REVIEW_REJECTED,
        WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD,
    },
    WorkOrderStatus.SECOND_REVIEW_REJECTED: {WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT},
    WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD: {WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT},
    WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT: {WorkOrderStatus.THIRD_REVIEWING},
    WorkOrderStatus.THIRD_REVIEWING: {
        WorkOrderStatus.THIRD_REVIEW_REJECTED,
        WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM,
    },
    WorkOrderStatus.THIRD_REVIEW_REJECTED: {WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT},
    WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM: {WorkOrderStatus.PRINTROOM_PROCESSING},
    WorkOrderStatus.PRINTROOM_PROCESSING: {WorkOrderStatus.PAPER_REPORT_ISSUED},
    WorkOrderStatus.PAPER_REPORT_ISSUED: set(),
}


def can_transit(from_status: WorkOrderStatus, to_status: WorkOrderStatus) -> bool:
    """Check whether state transition is allowed by static transition table."""
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())
