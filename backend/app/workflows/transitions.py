from app.workflows.states import WorkOrderStatus


ALLOWED_TRANSITIONS: dict[WorkOrderStatus, set[WorkOrderStatus]] = {
    WorkOrderStatus.PROJECT_CREATED: {WorkOrderStatus.WORK_ORDER_CREATED},
    WorkOrderStatus.WORK_ORDER_CREATED: {
        WorkOrderStatus.WAIT_CONTRACT_UPLOAD,
        WorkOrderStatus.CONTRACT_UPLOADED,
        WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT,
    },
    WorkOrderStatus.WAIT_CONTRACT_UPLOAD: {
        WorkOrderStatus.CONTRACT_UPLOADED,
        WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT,
    },
    WorkOrderStatus.CONTRACT_UPLOADED: {
        WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT,
        WorkOrderStatus.WAIT_PRINTROOM_OFFICIAL_CONTRACT,
        WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT,
    },
    WorkOrderStatus.WAIT_PRINTROOM_OFFICIAL_CONTRACT: {WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT},
    WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT: {WorkOrderStatus.CONTRACT_REVIEWING},
    WorkOrderStatus.CONTRACT_REVIEWING: {
        WorkOrderStatus.CONTRACT_REJECTED,
        WorkOrderStatus.CONTRACT_APPROVED,
    },
    WorkOrderStatus.CONTRACT_REJECTED: {
        WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT,
        WorkOrderStatus.CONTRACT_REVIEWING,
    },
    WorkOrderStatus.CONTRACT_APPROVED: {
        WorkOrderStatus.FIRST_REVIEWING,
        WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT,
    },
    WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT: {WorkOrderStatus.FIRST_REVIEWING},
    WorkOrderStatus.FIRST_REVIEWING: {
        WorkOrderStatus.FIRST_REVIEW_REJECTED,
        WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND,
        WorkOrderStatus.FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND,
        WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
    },
    WorkOrderStatus.FIRST_REVIEW_REJECTED: {
        WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT,
        WorkOrderStatus.FIRST_REVIEWING,
    },
    WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND: {
        WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
        WorkOrderStatus.SECOND_REVIEWING,
    },
    WorkOrderStatus.FIRST_APPROVED_WAIT_FIRST_SELECT_SECOND: {
        WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
        WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND,
    },
    WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT: {WorkOrderStatus.SECOND_REVIEWING},
    WorkOrderStatus.SECOND_REVIEWING: {
        WorkOrderStatus.SECOND_REVIEW_REJECTED,
        WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD,
        WorkOrderStatus.SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD,
        WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
    },
    WorkOrderStatus.SECOND_REVIEW_REJECTED: {
        WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT,
        WorkOrderStatus.SECOND_REVIEWING,
    },
    WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD: {
        WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
        WorkOrderStatus.THIRD_REVIEWING,
    },
    WorkOrderStatus.SECOND_APPROVED_WAIT_SECOND_SELECT_THIRD: {
        WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
        WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD,
    },
    WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT: {WorkOrderStatus.THIRD_REVIEWING},
    WorkOrderStatus.THIRD_REVIEWING: {
        WorkOrderStatus.THIRD_REVIEW_REJECTED,
        WorkOrderStatus.THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND,
        WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD,
        WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM,
    },
    WorkOrderStatus.THIRD_REVIEW_REJECTED: {
        WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT,
        WorkOrderStatus.THIRD_REVIEWING,
    },
    WorkOrderStatus.THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND: {WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM},
    WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM: {
        WorkOrderStatus.WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT,
        WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD,
    },
    WorkOrderStatus.WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT: {WorkOrderStatus.EXTERNAL_FIRST_REVIEWING},
    WorkOrderStatus.EXTERNAL_FIRST_REVIEWING: {
        WorkOrderStatus.EXTERNAL_FIRST_REJECTED,
        WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT,
    },
    WorkOrderStatus.EXTERNAL_FIRST_REJECTED: {
        WorkOrderStatus.WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT,
        WorkOrderStatus.EXTERNAL_FIRST_REVIEWING,
    },
    WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT: {WorkOrderStatus.EXTERNAL_SECOND_REVIEWING},
    WorkOrderStatus.EXTERNAL_SECOND_REVIEWING: {
        WorkOrderStatus.EXTERNAL_SECOND_REJECTED,
        WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT,
    },
    WorkOrderStatus.EXTERNAL_SECOND_REJECTED: {
        WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT,
        WorkOrderStatus.EXTERNAL_SECOND_REVIEWING,
    },
    WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT: {WorkOrderStatus.EXTERNAL_THIRD_REVIEWING},
    WorkOrderStatus.EXTERNAL_THIRD_REVIEWING: {
        WorkOrderStatus.EXTERNAL_THIRD_REJECTED,
        WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD,
    },
    WorkOrderStatus.EXTERNAL_THIRD_REJECTED: {
        WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT,
        WorkOrderStatus.EXTERNAL_THIRD_REVIEWING,
    },
    WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD: {WorkOrderStatus.SIGNOFF_REVIEWING},
    WorkOrderStatus.SIGNOFF_REVIEWING: {
        WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD,
        WorkOrderStatus.THIRD_REVIEWING,
        WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM,
    },
    WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM: {
        WorkOrderStatus.THIRD_REVIEWING,
        WorkOrderStatus.WAIT_CONTRACT_UPLOAD,
        WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT,
        WorkOrderStatus.PRINTROOM_PROCESSING,
    },
    WorkOrderStatus.PRINTROOM_PROCESSING: {
        WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM,
        WorkOrderStatus.WAIT_CONTRACT_UPLOAD,
        WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT,
        WorkOrderStatus.PAPER_REPORT_ISSUED,
    },
    WorkOrderStatus.PAPER_REPORT_ISSUED: {
        WorkOrderStatus.REPORT_MAILING,
        WorkOrderStatus.WAIT_INVOICE_INFO,
        WorkOrderStatus.PRINTROOM_PROCESSING,
    },
    WorkOrderStatus.REPORT_MAILING: {
        WorkOrderStatus.REPORT_MAILING_COMPLETED,
        WorkOrderStatus.PAPER_REPORT_ISSUED,
    },
    WorkOrderStatus.REPORT_MAILING_COMPLETED: {
        WorkOrderStatus.REPORT_MAILING,
        WorkOrderStatus.WAIT_INVOICE_INFO,
    },
    WorkOrderStatus.WAIT_INVOICE_INFO: {WorkOrderStatus.INVOICE_PROCESSING},
    WorkOrderStatus.INVOICE_INFO_REJECTED: {
        WorkOrderStatus.INVOICE_PROCESSING,
        WorkOrderStatus.PRINTROOM_PROCESSING,
    },
    WorkOrderStatus.INVOICE_PROCESSING: {
        WorkOrderStatus.INVOICE_INFO_REJECTED,
        WorkOrderStatus.INVOICE_ISSUED,
        WorkOrderStatus.WAIT_ARCHIVE_SUBMIT,
        WorkOrderStatus.ARCHIVE_REVIEWING,
    },
    WorkOrderStatus.INVOICE_ISSUED: {WorkOrderStatus.WAIT_ARCHIVE_SUBMIT},
    WorkOrderStatus.WAIT_ARCHIVE_SUBMIT: {WorkOrderStatus.ARCHIVE_REVIEWING},
    WorkOrderStatus.ARCHIVE_REJECTED: {WorkOrderStatus.ARCHIVE_REVIEWING},
    WorkOrderStatus.ARCHIVE_REVIEWING: {
        WorkOrderStatus.ARCHIVE_REJECTED,
        WorkOrderStatus.ARCHIVED,
    },
    WorkOrderStatus.ARCHIVED: set(),
}


def can_transit(from_status: WorkOrderStatus, to_status: WorkOrderStatus) -> bool:
    """Check whether state transition is allowed by static transition table."""
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())
