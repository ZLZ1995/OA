from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderListResponse,
    WorkOrderResponse,
    WorkOrderUpdate,
)
from app.workflows.states import WorkOrderStatus

router = APIRouter(prefix="/work-orders", tags=["工单"])

STATUS_LABEL_MAP = {
    WorkOrderStatus.PROJECT_CREATED.value: "项目创建",
    WorkOrderStatus.WORK_ORDER_CREATED.value: "工单创建",
    WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value: "合同初稿上传",
    WorkOrderStatus.CONTRACT_UPLOADED.value: "合同初稿上传",
    WorkOrderStatus.WAIT_PRINTROOM_OFFICIAL_CONTRACT.value: "合同初稿上传",
    WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT.value: "合同初稿审核",
    WorkOrderStatus.CONTRACT_REVIEWING.value: "合同初稿审核中",
    WorkOrderStatus.CONTRACT_REJECTED.value: "合同初稿审核退回",
    WorkOrderStatus.CONTRACT_APPROVED.value: "合同初稿审核通过",
    WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT.value: "报告送审",
    WorkOrderStatus.FIRST_REVIEWING.value: "一审",
    WorkOrderStatus.FIRST_REVIEW_REJECTED.value: "一审退回",
    WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND.value: "二审",
    WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT.value: "二审",
    WorkOrderStatus.SECOND_REVIEWING.value: "二审",
    WorkOrderStatus.SECOND_REVIEW_REJECTED.value: "二审退回",
    WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD.value: "三审",
    WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT.value: "三审",
    WorkOrderStatus.THIRD_REVIEWING.value: "三审",
    WorkOrderStatus.THIRD_REVIEW_REJECTED.value: "三审退回",
    WorkOrderStatus.THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND.value: "三审通过待发送外部审核确认",
    WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM.value: "待项目负责人确认是否涉及外部审核",
    WorkOrderStatus.WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT.value: "待提交外部一级复核",
    WorkOrderStatus.EXTERNAL_FIRST_REVIEWING.value: "外部一级复核",
    WorkOrderStatus.EXTERNAL_FIRST_REJECTED.value: "外部一级复核退回",
    WorkOrderStatus.WAIT_EXTERNAL_SECOND_REVIEW_SUBMIT.value: "待提交外部二级复核",
    WorkOrderStatus.EXTERNAL_SECOND_REVIEWING.value: "外部二级复核",
    WorkOrderStatus.EXTERNAL_SECOND_REJECTED.value: "外部二级复核退回",
    WorkOrderStatus.WAIT_EXTERNAL_THIRD_REVIEW_SUBMIT.value: "待提交外部三级复核",
    WorkOrderStatus.EXTERNAL_THIRD_REVIEWING.value: "外部三级复核",
    WorkOrderStatus.EXTERNAL_THIRD_REJECTED.value: "外部三级复核退回",
    WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value: "待上传报告附件与合同扫描件",
    WorkOrderStatus.SIGNOFF_REVIEWING.value: "签发审核",
    WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value: "报告出具准备",
    WorkOrderStatus.PRINTROOM_PROCESSING.value: "报告出具",
    WorkOrderStatus.PAPER_REPORT_ISSUED.value: "报告出具完成",
    WorkOrderStatus.REPORT_MAILING.value: "报告邮寄",
    WorkOrderStatus.REPORT_MAILING_COMPLETED.value: "报告邮寄完成",
    WorkOrderStatus.WAIT_INVOICE_INFO.value: "开票信息",
    WorkOrderStatus.INVOICE_INFO_REJECTED.value: "开票信息退回",
    WorkOrderStatus.INVOICE_PROCESSING.value: "财务开票",
    WorkOrderStatus.INVOICE_ISSUED.value: "发票已开具",
    WorkOrderStatus.WAIT_ARCHIVE_SUBMIT.value: "报告归档",
    WorkOrderStatus.ARCHIVE_REVIEWING.value: "底稿审核",
    WorkOrderStatus.ARCHIVE_REJECTED.value: "报告归档退回",
    WorkOrderStatus.ARCHIVED.value: "已归档",
}


def _to_response(item: WorkOrder) -> WorkOrderResponse:
    data = WorkOrderResponse.model_validate(item, from_attributes=True).model_dump()
    data["current_status"] = STATUS_LABEL_MAP.get(item.current_status, item.current_status)
    return WorkOrderResponse(**data)


@router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkOrderListResponse:
    member_project_subquery = db.query(ProjectMember.project_id).filter(ProjectMember.user_id == current_user.id)
    rows = (
        db.query(WorkOrder)
        .join(Project, Project.id == WorkOrder.project_id)
        .filter(
            Project.deleted_at.is_(None),
            Project.archived_at.is_(None),
            or_(
                WorkOrder.initiator_user_id == current_user.id,
                WorkOrder.project_leader_id == current_user.id,
                WorkOrder.contract_reviewer_id == current_user.id,
                WorkOrder.project_id.in_(member_project_subquery),
            ),
        )
        .order_by(WorkOrder.id.desc())
        .all()
    )
    return WorkOrderListResponse(items=[_to_response(item) for item in rows])


@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER")),
) -> WorkOrderResponse:
    project = (
        db.query(Project)
        .filter(
            Project.id == payload.project_id,
            Project.deleted_at.is_(None),
            Project.archived_at.is_(None),
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="关联项目不存在或不可用")

    work_order_no = project.project_code
    exists = (
        db.query(WorkOrder)
        .filter(WorkOrder.work_order_no == work_order_no, WorkOrder.project_id == payload.project_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="工单号已存在")

    row = WorkOrder(
        **payload.model_dump(exclude={"work_order_no", "title"}),
        work_order_no=work_order_no,
        title=project.project_name,
        current_status=WorkOrderStatus.WORK_ORDER_CREATED.value,
        current_handler_user_id=project.project_leader_id,
        initiator_user_id=current_user.id,
        project_leader_id=project.project_leader_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WorkOrderResponse:
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")
    return _to_response(row)


@router.patch("/{work_order_id}", response_model=WorkOrderResponse)
def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    role_codes: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER", "PROJECT_MEMBER", "THIRD_REVIEWER", "CONTRACT_REVIEWER", "CHIEF_APPRAISER")),
) -> WorkOrderResponse:
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")

    data = payload.model_dump(exclude_unset=True)
    signer_keys = {"signer_one", "signer_two", "formal_report_count"}
    contract_keys = {"contract_reviewer_id"}
    mailing_keys = {"mailing_handler_user_id", "mailing_status"}
    signoff_keys = {"signoff_status", "chief_appraiser_user_id"}

    if signer_keys & set(data) and "ADMIN" not in role_codes:
        if set(data) - signer_keys:
            raise HTTPException(status_code=403, detail="正式报告信息只能由三审老师在报告送审末尾填写")
        if "THIRD_REVIEWER" not in role_codes:
            raise HTTPException(status_code=403, detail="仅三审老师可填写签字评估师")
        if row.current_status != WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value:
            raise HTTPException(status_code=400, detail="三审通过后才可填写正式报告信息")
        if current_user.id != row.third_reviewer_id:
            raise HTTPException(status_code=403, detail="仅该项目三审老师可填写签字评估师")
    elif contract_keys & set(data) and "ADMIN" not in role_codes:
        if set(data) - contract_keys:
            raise HTTPException(status_code=403, detail="合同审核人字段只能单独更新")
        if "PROJECT_LEADER" not in role_codes and "SALES" not in role_codes:
            raise HTTPException(status_code=403, detail="仅项目方可指定合同审核人")
    elif mailing_keys & set(data) and "ADMIN" not in role_codes:
        if set(data) - mailing_keys:
            raise HTTPException(status_code=403, detail="邮寄相关字段只能单独更新")
    elif "ADMIN" not in role_codes and not ({"SALES", "PROJECT_LEADER"} & role_codes):
        if not data or set(data) - signer_keys - contract_keys - mailing_keys:
            raise HTTPException(status_code=403, detail="无权修改该工单")

    for key, value in data.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> None:
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")
    db.delete(row)
    db.commit()
