from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.report_mailing_record import ReportMailingRecord
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.report_mailing import (
    ReportMailingDecisionRequest,
    ReportMailingExpressRequest,
    ReportMailingRecordListResponse,
    ReportMailingRecordResponse,
    ReportMailingSubmitRequest,
)
from app.services.workflow_log_service import create_workflow_log
from app.workflows.states import WorkOrderStatus

router = APIRouter(prefix="/report-mailing", tags=["报告邮寄"])


def _operator_name(db: Session, user_id: int) -> str | None:
    return db.query(User.real_name).filter(User.id == user_id).scalar()


def _serialize_record(db: Session, row: ReportMailingRecord) -> ReportMailingRecordResponse:
    return ReportMailingRecordResponse(
        id=row.id,
        work_order_id=row.work_order_id,
        project_id=row.project_id,
        action_type=row.action_type,
        operator_user_id=row.operator_user_id,
        operator_user_name=_operator_name(db, row.operator_user_id),
        receiver_name=row.receiver_name,
        receiver_phone=row.receiver_phone,
        receiver_address=row.receiver_address,
        receiver_remark=row.receiver_remark,
        express_no=row.express_no,
        status=row.status,
        invalidated_express_no=row.invalidated_express_no,
        created_at=row.created_at,
    )


def _is_project_party(db: Session, work_order: WorkOrder, user: User) -> bool:
    if user.id in {work_order.project_leader_id, work_order.initiator_user_id}:
        return True
    return db.query(ProjectMember.id).filter(ProjectMember.project_id == work_order.project_id, ProjectMember.user_id == user.id).first() is not None


@router.get("/work-orders/{work_order_id}", response_model=ReportMailingRecordListResponse)
def list_report_mailing_records(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReportMailingRecordListResponse:
    rows = (
        db.query(ReportMailingRecord)
        .filter(ReportMailingRecord.work_order_id == work_order_id)
        .order_by(ReportMailingRecord.created_at.desc(), ReportMailingRecord.id.desc())
        .all()
    )
    return ReportMailingRecordListResponse(items=[_serialize_record(db, row) for row in rows])


@router.post("/work-orders/{work_order_id}/start")
def start_report_mailing(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目负责人、创建人或项目组成员可发起报告邮寄")
    if work_order.current_status not in {
        WorkOrderStatus.PAPER_REPORT_ISSUED.value,
        WorkOrderStatus.WAIT_INVOICE_INFO.value,
        WorkOrderStatus.INVOICE_INFO_REJECTED.value,
        WorkOrderStatus.INVOICE_PROCESSING.value,
        WorkOrderStatus.INVOICE_ISSUED.value,
        WorkOrderStatus.REPORT_MAILING.value,
        WorkOrderStatus.REPORT_MAILING_COMPLETED.value,
    }:
        raise HTTPException(status_code=400, detail="当前状态不可进入报告邮寄")

    if not work_order.print_room_handler_id:
        raise HTTPException(status_code=400, detail="请先完成报告出具后再进入报告邮寄")

    work_order.mailing_status = "PROJECT_EDITING"
    if work_order.current_status == WorkOrderStatus.PAPER_REPORT_ISSUED.value:
        work_order.current_status = WorkOrderStatus.REPORT_MAILING.value
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=work_order.current_status,
        to_status=work_order.current_status,
        action_type="START_REPORT_MAILING",
        operator_user_id=current_user.id,
        remark="进入报告邮寄",
    )
    db.commit()
    return {"message": "已进入报告邮寄"}


@router.post("/work-orders/{work_order_id}/submit", response_model=ReportMailingRecordResponse)
def submit_report_mailing(
    work_order_id: int,
    payload: ReportMailingSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportMailingRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目方可提交邮寄信息")
    if not work_order.print_room_handler_id:
        raise HTTPException(status_code=400, detail="文印室办理人员未确定，无法提交邮寄信息")

    latest_record = (
        db.query(ReportMailingRecord)
        .filter(ReportMailingRecord.work_order_id == work_order_id)
        .order_by(ReportMailingRecord.id.desc())
        .first()
    )
    invalidated_express_no = None
    action_type = "SUBMIT_MAILING"
    if latest_record and latest_record.express_no and latest_record.status == "PRINT_ROOM_DONE":
        invalidated_express_no = latest_record.express_no
        action_type = "RESUBMIT_MAILING"

    row = ReportMailingRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type=action_type,
        operator_user_id=current_user.id,
        receiver_name=payload.receiver_name,
        receiver_phone=payload.receiver_phone,
        receiver_address=payload.receiver_address,
        receiver_remark=payload.receiver_remark,
        status="SUBMITTED",
        invalidated_express_no=invalidated_express_no,
    )
    db.add(row)

    work_order.mailing_handler_user_id = work_order.print_room_handler_id
    work_order.mailing_status = "PRINT_ROOM_PENDING"
    work_order.current_status = WorkOrderStatus.REPORT_MAILING.value
    work_order.current_handler_user_id = work_order.print_room_handler_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=work_order.current_status,
        to_status=WorkOrderStatus.REPORT_MAILING.value,
        action_type=action_type,
        operator_user_id=current_user.id,
        remark=payload.receiver_address,
    )
    db.commit()
    db.refresh(row)
    return _serialize_record(db, row)


@router.post("/work-orders/{work_order_id}/print-room", response_model=ReportMailingRecordResponse)
def submit_report_mailing_express(
    work_order_id: int,
    payload: ReportMailingExpressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportMailingRecordResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if current_user.id != work_order.print_room_handler_id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅文印室办理人员可填写快递单号")

    latest = (
        db.query(ReportMailingRecord)
        .filter(ReportMailingRecord.work_order_id == work_order_id)
        .order_by(ReportMailingRecord.id.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=400, detail="请先由项目方提交邮寄信息")

    row = ReportMailingRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="PRINT_ROOM_SUBMIT_EXPRESS",
        operator_user_id=current_user.id,
        receiver_name=latest.receiver_name,
        receiver_phone=latest.receiver_phone,
        receiver_address=latest.receiver_address,
        receiver_remark=latest.receiver_remark,
        express_no=payload.express_no,
        status="PRINT_ROOM_DONE",
    )
    db.add(row)

    work_order.mailing_status = "PROJECT_CONFIRMING"
    work_order.current_status = WorkOrderStatus.REPORT_MAILING.value
    work_order.current_handler_user_id = work_order.project_leader_id or work_order.initiator_user_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=work_order.current_status,
        to_status=WorkOrderStatus.REPORT_MAILING.value,
        action_type="PRINT_ROOM_SUBMIT_EXPRESS",
        operator_user_id=current_user.id,
        remark=payload.express_no,
    )
    db.commit()
    db.refresh(row)
    return _serialize_record(db, row)


@router.post("/work-orders/{work_order_id}/confirm")
def confirm_report_mailing(
    work_order_id: int,
    payload: ReportMailingDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目方可确认已寄出")

    latest = (
        db.query(ReportMailingRecord)
        .filter(ReportMailingRecord.work_order_id == work_order_id)
        .order_by(ReportMailingRecord.id.desc())
        .first()
    )
    if not latest or latest.status != "PRINT_ROOM_DONE":
        raise HTTPException(status_code=400, detail="请等待文印室填写快递单号后再确认")

    row = ReportMailingRecord(
        work_order_id=work_order.id,
        project_id=work_order.project_id,
        action_type="PROJECT_CONFIRM_MAILING",
        operator_user_id=current_user.id,
        receiver_name=latest.receiver_name,
        receiver_phone=latest.receiver_phone,
        receiver_address=latest.receiver_address,
        receiver_remark=latest.receiver_remark,
        express_no=latest.express_no,
        status="CONFIRMED",
    )
    db.add(row)

    work_order.mailing_status = "COMPLETED"
    work_order.current_status = WorkOrderStatus.REPORT_MAILING_COMPLETED.value
    work_order.current_handler_user_id = work_order.project_leader_id or work_order.initiator_user_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=WorkOrderStatus.REPORT_MAILING.value,
        to_status=WorkOrderStatus.REPORT_MAILING_COMPLETED.value,
        action_type="PROJECT_CONFIRM_MAILING",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    db.commit()
    return {"message": "报告邮寄已确认完成"}
