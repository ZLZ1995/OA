from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.archive import Archive
from app.models.contract import Contract
from app.models.contract_review_record import ContractReviewRecord
from app.models.invoice import Invoice
from app.models.print_room_record import PrintRoomRecord
from app.models.project import Project
from app.models.project_delete_request import ProjectDeleteRequest
from app.models.project_member import ProjectMember
from app.models.project_update_log import ProjectUpdateLog
from app.models.report_mailing_record import ReportMailingRecord
from app.models.report_version import ReportVersion
from app.models.review_record import ReviewRecord
from app.models.work_order import WorkOrder
from app.models.work_order_file import WorkOrderFile
from app.models.workflow_log import WorkflowLog
from app.services.project_flow import normalize_project_step


def now_local() -> datetime:
    return datetime.now()


def can_project_owner_delete_direct(work_order: WorkOrder | None) -> bool:
    if not work_order:
        return True
    current_step = normalize_project_step(work_order.current_status, False)
    return current_step not in {"报告出具", "报告邮寄", "发票开具", "报告归档", "已归档"}


def ensure_admin_approver_not_self(current_user_id: int, approver_user_id: int) -> None:
    if current_user_id == approver_user_id:
        raise HTTPException(status_code=400, detail="共同认证管理员不能选择自己")


def delete_project_related_data(db: Session, project: Project) -> None:
    work_orders = db.query(WorkOrder).filter(WorkOrder.project_id == project.id).all()
    work_order_ids = [item.id for item in work_orders]
    # Keep notification text as history, but detach deleted entities and stale links.
    from sqlalchemy import or_
    from app.models.user_notification import UserNotification
    db.query(UserNotification).filter(or_(UserNotification.project_id == project.id,
        UserNotification.work_order_id.in_(work_order_ids))).update({
        UserNotification.project_id: None, UserNotification.work_order_id: None,
        UserNotification.link_type: None, UserNotification.link_target_id: None,
        UserNotification.group_key: None, UserNotification.popup_flag: False,
    }, synchronize_session=False)

    storage_keys = []
    if work_order_ids:
        from app.models.operation_workpaper import OperationWorkpaperReview, OperationWorkpaperSubmission, OperationWorkpaperSubmissionFile
        review_ids = [r.id for r in db.query(OperationWorkpaperReview).filter(OperationWorkpaperReview.work_order_id.in_(work_order_ids))]
        if review_ids:
            submission_ids = [s.id for s in db.query(OperationWorkpaperSubmission).filter(OperationWorkpaperSubmission.review_id.in_(review_ids))]
            db.query(OperationWorkpaperSubmissionFile).filter(OperationWorkpaperSubmissionFile.submission_id.in_(submission_ids)).delete(synchronize_session=False)
            db.query(OperationWorkpaperSubmission).filter(OperationWorkpaperSubmission.review_id.in_(review_ids)).delete(synchronize_session=False)
            db.query(OperationWorkpaperReview).filter(OperationWorkpaperReview.id.in_(review_ids)).delete(synchronize_session=False)
        storage_keys = [
            item.storage_key
            for item in db.query(WorkOrderFile).filter(WorkOrderFile.work_order_id.in_(work_order_ids)).all()
            if item.storage_key
        ]
        db.query(Archive).filter(Archive.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(Contract).filter(Contract.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(ContractReviewRecord).filter(ContractReviewRecord.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(Invoice).filter(Invoice.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(PrintRoomRecord).filter(PrintRoomRecord.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(ReportMailingRecord).filter(ReportMailingRecord.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(ReportVersion).filter(ReportVersion.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(ReviewRecord).filter(ReviewRecord.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(WorkOrderFile).filter(WorkOrderFile.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(WorkflowLog).filter(WorkflowLog.work_order_id.in_(work_order_ids)).delete(synchronize_session=False)
        db.query(WorkOrder).filter(WorkOrder.id.in_(work_order_ids)).delete(synchronize_session=False)

    delete_request = db.query(ProjectDeleteRequest).filter(ProjectDeleteRequest.project_id == project.id).first()
    if delete_request:
        delete_request.status = "APPROVED"
        delete_request.reviewed_at = now_local()
        delete_request.project_no = project.project_code
        delete_request.project_name = project.project_name
        delete_request.client_name = project.client_name
        delete_request.current_step = "已删除"
        delete_request.project_id = None

    db.query(ProjectMember).filter(ProjectMember.project_id == project.id).delete(synchronize_session=False)
    db.query(ProjectUpdateLog).filter(ProjectUpdateLog.project_id == project.id).delete(synchronize_session=False)
    db.delete(project)
    db.flush()

    from app.core.config import settings
    from app.services.committed_file_cleanup import after_commit_delete
    after_commit_delete(db, [Path(key) if Path(key).is_absolute() else Path(settings.local_storage_dir) / key for key in storage_keys])
