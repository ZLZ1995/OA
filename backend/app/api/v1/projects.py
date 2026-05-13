import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.v1.contract_reviews import get_contract_review_status_display
from app.db.session import get_db
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
from app.models.user import User
from app.models.work_order import WorkOrder
from app.schemas.contract_review import ContractReviewRecordResponse
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.schemas.project_flow import ProjectFlowProject, ProjectFlowResponse, ProjectUpdateLogItem
from app.services.project_flow import (
    build_todo_action,
    get_flow_steps,
    get_project_leader_display_name,
    get_project_source_display,
    get_project_status_display,
    get_user_role_in_project,
    normalize_project_step,
)
from app.services.workflow_log_service import create_workflow_log
from app.services.project_delete_service import can_project_owner_delete_direct, delete_project_related_data
from app.workflows.states import WorkOrderStatus

router = APIRouter(prefix="/projects", tags=["项目"])

UNIT_CODE_MAP = {
    "中勤": "ZQ",
    "中立国际": "ZLGJ",
    "中众": "ZZ",
    "其他": "QT",
}


class ProjectTerminationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


def _build_status_display(project: Project, latest_work_order_status: str | None) -> str:
    return get_project_status_display(latest_work_order_status, project.archived_at is not None, project.project_source)


def _get_latest_work_order(db: Session, project_id: int) -> WorkOrder | None:
    return db.query(WorkOrder).filter(WorkOrder.project_id == project_id).order_by(WorkOrder.id.desc()).first()


def _serialize_contract_review_records(db: Session, work_order_id: int | None) -> list[ContractReviewRecordResponse]:
    if not work_order_id:
        return []
    rows = (
        db.query(ContractReviewRecord)
        .filter(ContractReviewRecord.work_order_id == work_order_id)
        .order_by(ContractReviewRecord.created_at.desc(), ContractReviewRecord.id.desc())
        .all()
    )
    from app.api.v1.contract_reviews import _serialize_record

    return [_serialize_record(db, row) for row in rows]


def _resolve_contract_review_status_from_history(records: list[ContractReviewRecordResponse]) -> tuple[str | None, str | None]:
    for item in records:
        if item.action_type == "APPROVE_CONTRACT":
            return "CONTRACT_APPROVED", "合同初稿审核通过"
        if item.action_type == "REJECT_CONTRACT":
            return "CONTRACT_REJECTED", "合同初稿审核退回"
        if item.action_type == "SUBMIT_CONTRACT":
            return "CONTRACT_REVIEWING", "合同初稿审核中"
    return None, None


def _serialize_project_update_logs(db: Session, project_id: int) -> list[ProjectUpdateLogItem]:
    rows = (
        db.query(ProjectUpdateLog)
        .filter(ProjectUpdateLog.project_id == project_id)
        .order_by(ProjectUpdateLog.created_at.desc(), ProjectUpdateLog.id.desc())
        .all()
    )
    items: list[ProjectUpdateLogItem] = []
    for row in rows:
        operator_name = db.query(User.real_name).filter(User.id == row.operator_user_id).scalar()
        items.append(
            ProjectUpdateLogItem(
                id=row.id,
                operator_user_id=row.operator_user_id,
                operator_user_name=operator_name,
                changed_fields=row.changed_fields,
                created_at=row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
    return items


def _get_readonly_flow_fields(db: Session, project: Project, work_order: WorkOrder | None) -> dict[str, str | float | None]:
    if not work_order:
        return {}

    print_room_record = db.query(PrintRoomRecord).filter(PrintRoomRecord.work_order_id == work_order.id).first()
    invoice = db.query(Invoice).filter(Invoice.work_order_id == work_order.id).order_by(Invoice.id.desc()).first()
    contract = db.query(Contract).filter(Contract.work_order_id == work_order.id).first()
    mailing_record = db.query(ReportMailingRecord).filter(ReportMailingRecord.work_order_id == work_order.id).order_by(ReportMailingRecord.id.desc()).first()

    def user_name(user_id: int | None) -> str | None:
        if not user_id:
            return None
        return db.query(User.real_name).filter(User.id == user_id).scalar()

    return {
        "contract_no": contract.contract_no if contract else None,
        "report_no": print_room_record.paper_report_no if print_room_record else None,
        "first_reviewer_name": user_name(work_order.first_reviewer_id),
        "second_reviewer_name": user_name(work_order.second_reviewer_id),
        "third_reviewer_name": user_name(work_order.third_reviewer_id),
        "print_room_handler_name": user_name(work_order.print_room_handler_id),
        "mailing_handler_name": user_name(work_order.mailing_handler_user_id),
        "invoice_handler_name": user_name((invoice.handled_by or invoice.finance_handler_id) if invoice else None),
        "archive_reviewer_name": user_name(work_order.archive_reviewer_id),
        "mailing_receiver_name": mailing_record.receiver_name if mailing_record else None,
        "mailing_receiver_phone": mailing_record.receiver_phone if mailing_record else None,
        "mailing_receiver_address": mailing_record.receiver_address if mailing_record else None,
        "mailing_receiver_remark": mailing_record.receiver_remark if mailing_record else None,
        "mailing_express_no": mailing_record.express_no if mailing_record else None,
    }


def _serialize_project(db: Session, project: Project) -> ProjectResponse:
    work_order = _get_latest_work_order(db, project.id)
    leader_name = db.query(User.real_name).filter(User.id == project.project_leader_id).scalar()
    latest_status = work_order.current_status if work_order else None
    status_cn = _build_status_display(project, latest_status)
    readonly_fields = _get_readonly_flow_fields(db, project, work_order)
    contract_review_records = _serialize_contract_review_records(db, work_order.id if work_order else None)
    history_contract_status, history_contract_status_display = _resolve_contract_review_status_from_history(contract_review_records)

    data = ProjectResponse.model_validate(project, from_attributes=True).model_dump()
    for key in ["status", "status_display", "project_source_display", "project_leader_display_name", "contract_review_status", "contract_review_status_display", "contract_no", "report_no"]:
        data.pop(key, None)

    return ProjectResponse(
        **data,
        status=status_cn,
        status_display=status_cn,
        project_source_display=get_project_source_display(project.project_source),
        project_leader_display_name=get_project_leader_display_name(project, leader_name),
        report_no=readonly_fields.get("report_no"),
        contract_no=readonly_fields.get("contract_no"),
        contract_review_status=(
            latest_status if latest_status in {
                WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value,
                WorkOrderStatus.CONTRACT_UPLOADED.value,
                WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT.value,
                WorkOrderStatus.CONTRACT_REVIEWING.value,
                WorkOrderStatus.CONTRACT_REJECTED.value,
                WorkOrderStatus.CONTRACT_APPROVED.value,
            } else history_contract_status
        ),
        contract_review_status_display=(
            get_contract_review_status_display(latest_status)
            if latest_status in {
                WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value,
                WorkOrderStatus.CONTRACT_UPLOADED.value,
                WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT.value,
                WorkOrderStatus.CONTRACT_REVIEWING.value,
                WorkOrderStatus.CONTRACT_REJECTED.value,
                WorkOrderStatus.CONTRACT_APPROVED.value,
            }
            else history_contract_status_display
        ),
    )


def _generate_project_code(db: Session, undertaking_unit: str) -> str:
    unit_code = UNIT_CODE_MAP.get(undertaking_unit)
    if not unit_code:
        raise HTTPException(status_code=400, detail="不支持的项目承接单位")
    now = datetime.now()
    prefix = f"{unit_code}-{now.strftime('%Y%m')}-"
    latest = (
        db.query(Project.project_code)
        .filter(Project.project_code.like(f"{prefix}%"))
        .order_by(Project.project_code.desc())
        .first()
    )
    next_seq = 1
    if latest and latest[0]:
        try:
            next_seq = int(latest[0].split("-")[-1]) + 1
        except ValueError:
            next_seq = 1
    return f"{prefix}{next_seq:03d}"


def _can_edit_project_basic_info(db: Session, project_id: int, project: Project, current_user: User) -> bool:
    if project.archived_at is not None:
        return False
    if current_user.id == project.project_leader_id:
        return True
    return db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None


def _record_project_update_log(db: Session, project: Project, current_user: User, before: dict[str, object], after: dict[str, object]) -> None:
    changed: dict[str, dict[str, object]] = {}
    for key, before_value in before.items():
        after_value = after.get(key)
        if before_value != after_value:
            changed[key] = {"before": before_value, "after": after_value}
    if not changed:
        return
    db.add(
        ProjectUpdateLog(
            project_id=project.id,
            operator_user_id=current_user.id,
            changed_fields=json.dumps(changed, ensure_ascii=False),
            remark="项目基本信息修改",
        )
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectListResponse:
    rows = db.query(Project).filter(Project.deleted_at.is_(None)).order_by(Project.id.desc()).all()
    return ProjectListResponse(items=[_serialize_project(db, row) for row in rows])


@router.get("/options", response_model=ProjectListResponse)
def list_project_options(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectListResponse:
    rows = (
        db.query(Project)
        .filter(Project.deleted_at.is_(None), Project.archived_at.is_(None))
        .order_by(Project.id.desc())
        .all()
    )
    return ProjectListResponse(items=[_serialize_project(db, row) for row in rows])


@router.get("/generate-code")
def generate_project_code(
    undertaking_unit: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, str]:
    return {"project_code": _generate_project_code(db, undertaking_unit)}


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    project_code = payload.project_code or _generate_project_code(db, payload.undertaking_unit)
    exists = db.query(Project).filter(Project.project_code == project_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="项目编号已存在")

    row = Project(**payload.model_dump(exclude={"project_code"}), project_code=project_code)
    db.add(row)
    db.flush()

    initial_status = WorkOrderStatus.WORK_ORDER_CREATED.value if row.project_source == "INTERNAL" else WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value
    work_order = WorkOrder(
        work_order_no=row.project_code,
        project_id=row.id,
        title=row.project_name,
        current_status=initial_status,
        current_handler_user_id=row.project_leader_id,
        initiator_user_id=current_user.id,
        project_leader_id=row.project_leader_id,
    )
    db.add(work_order)
    db.commit()
    db.refresh(row)
    return _serialize_project(db, row)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectResponse:
    row = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _serialize_project(db, row)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    row = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    if row.termination_status == "PENDING":
        raise HTTPException(status_code=400, detail="项目终止/废止审核中，已锁定编辑")
    if not _can_edit_project_basic_info(db, project_id, row, current_user):
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可编辑项目基本信息")

    data = payload.model_dump(exclude_unset=True)
    project_source = data.get("project_source", row.project_source)
    external_leader = data.get("external_project_leader_name", row.external_project_leader_name)
    if project_source == "EXTERNAL" and not external_leader:
        raise HTTPException(status_code=400, detail="外部项目必须填写外部项目负责人姓名")
    if project_source != "EXTERNAL":
        data["external_project_leader_name"] = None

    before = {
        "undertaking_unit": row.undertaking_unit,
        "project_name": row.project_name,
        "client_name": row.client_name,
        "report_type": row.report_type,
        "valuation_base_date": row.valuation_base_date.isoformat() if row.valuation_base_date else None,
        "business_salesman": row.business_salesman,
        "project_amount": row.project_amount,
        "project_source": row.project_source,
        "external_project_leader_name": row.external_project_leader_name,
    }

    for key, value in data.items():
        setattr(row, key, value)

    after = {
        "undertaking_unit": row.undertaking_unit,
        "project_name": row.project_name,
        "client_name": row.client_name,
        "report_type": row.report_type,
        "valuation_base_date": row.valuation_base_date.isoformat() if row.valuation_base_date else None,
        "business_salesman": row.business_salesman,
        "project_amount": row.project_amount,
        "project_source": row.project_source,
        "external_project_leader_name": row.external_project_leader_name,
    }
    _record_project_update_log(db, row, current_user, before, after)

    db.commit()
    db.refresh(row)
    return _serialize_project(db, row)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    row = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    work_order = _get_latest_work_order(db, project_id)
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None
    if row.termination_status in {"PENDING", "DELETE_PENDING"}:
        raise HTTPException(status_code=400, detail="当前项目状态不允许删除")
    if row.archived_at is not None or (work_order and work_order.current_status == WorkOrderStatus.ARCHIVED.value):
        raise HTTPException(status_code=400, detail="已归档项目不可删除")
    if row.project_leader_id != current_user.id and row.business_user_id != current_user.id and not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人可删除该项目")
    if not can_project_owner_delete_direct(work_order):
        raise HTTPException(status_code=400, detail="报告出具后需管理员确认删除")
    delete_project_related_data(db, row)
    db.commit()


@router.patch("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    row = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    work_order = _get_latest_work_order(db, project_id)
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None
    if row.business_user_id != current_user.id and row.project_leader_id != current_user.id and not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人、创建人或项目组成员可归档")
    termination_approved = row.termination_status == "APPROVED"
    if not work_order or (work_order.archive_submission_type != "APPROVED" and not termination_approved):
        raise HTTPException(status_code=400, detail="底稿审核通过或终止/废止审核通过后才可归档")
    if row.archived_at is None:
        row.archived_at = datetime.now()
    archived = db.query(Archive).filter(Archive.work_order_id == work_order.id).first()
    if not archived:
        db.add(
            Archive(
                work_order_id=work_order.id,
                archived_by=current_user.id,
                archive_no=work_order.work_order_no,
                archive_location=None,
                archive_at=datetime.now(),
                remark="项目人员确认归档",
            )
        )
    work_order.current_status = WorkOrderStatus.ARCHIVED.value
    work_order.current_handler_user_id = None
    db.commit()
    db.refresh(row)
    return _serialize_project(db, row)


@router.post("/{project_id}/termination-request", response_model=ProjectResponse)
def request_project_termination(
    project_id: int,
    payload: ProjectTerminationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    row = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="项目已归档，不可终止/废止")
    work_order = _get_latest_work_order(db, project_id)
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None
    if row.business_user_id != current_user.id and row.project_leader_id != current_user.id and not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人、创建人或项目组成员可申请终止/废止")
    if row.termination_status == "PENDING":
        raise HTTPException(status_code=400, detail="终止/废止申请已在审核中")

    row.termination_status = "PENDING"
    row.termination_reason = payload.reason
    row.termination_requested_by = current_user.id
    row.termination_requested_at = datetime.now()
    row.status = "TERMINATION_PENDING"
    if work_order:
        create_workflow_log(
            db,
            work_order_id=work_order.id,
            from_status=work_order.current_status,
            to_status=work_order.current_status,
            action_type="PROJECT_TERMINATION_REQUEST",
            operator_user_id=current_user.id,
            remark=payload.reason,
        )
    db.commit()
    db.refresh(row)
    return _serialize_project(db, row)


@router.post("/{project_id}/termination-approve", response_model=ProjectResponse)
def approve_project_termination(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> ProjectResponse:
    row = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    if row.termination_status != "PENDING":
        raise HTTPException(status_code=400, detail="当前无待审核的终止/废止申请")

    work_order = _get_latest_work_order(db, project_id)
    row.termination_status = "APPROVED"
    row.termination_approved_by = current_user.id
    row.termination_approved_at = datetime.now()
    row.status = "TERMINATION_APPROVED"
    if work_order:
        create_workflow_log(
            db,
            work_order_id=work_order.id,
            from_status=work_order.current_status,
            to_status=work_order.current_status,
            action_type="PROJECT_TERMINATION_APPROVE",
            operator_user_id=current_user.id,
            remark=row.termination_reason,
        )
    db.commit()
    db.refresh(row)
    return _serialize_project(db, row)


@router.get("/{project_id}/flow", response_model=ProjectFlowResponse)
def get_project_flow(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectFlowResponse:
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    work_order = _get_latest_work_order(db, project_id)
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None

    role = get_user_role_in_project(project, work_order, current_user, is_member)
    if role == "无权限":
        raise HTTPException(status_code=403, detail="无权查看该项目")

    step = normalize_project_step(work_order.current_status if work_order else None, project.archived_at is not None, project.project_source)
    is_termination_locked = project.termination_status in {"PENDING", "APPROVED", "DELETE_PENDING"}
    if project.termination_status == "DELETE_PENDING":
        step = "待确认删除"
        action = "待确认删除，当前业务已锁定"
    else:
        action = "项目终止/废止流程处理中，当前业务已锁定" if is_termination_locked else build_todo_action(step, role) or "当前暂无待办操作"
    leader_name = db.query(User.real_name).filter(User.id == project.project_leader_id).scalar()
    contract_reviewer_name = db.query(User.real_name).filter(User.id == work_order.contract_reviewer_id).scalar() if work_order and work_order.contract_reviewer_id else None
    readonly_fields = _get_readonly_flow_fields(db, project, work_order)
    contract_review_records = _serialize_contract_review_records(db, work_order.id if work_order else None)
    history_contract_status, history_contract_status_display = _resolve_contract_review_status_from_history(contract_review_records)

    return ProjectFlowResponse(
        project=ProjectFlowProject(
            id=project.id,
            project_no=project.project_code,
            project_name=project.project_name,
            client_name=project.client_name,
            undertaking_unit=project.undertaking_unit,
            report_type=project.report_type,
            valuation_base_date=project.valuation_base_date.strftime("%Y-%m-%d") if project.valuation_base_date else None,
            business_salesman=project.business_salesman,
            project_amount=project.project_amount,
            project_source=project.project_source,
            project_source_display=get_project_source_display(project.project_source),
            external_project_leader_name=project.external_project_leader_name,
            project_leader_display_name=get_project_leader_display_name(project, leader_name),
            contract_no=readonly_fields.get("contract_no"),
            report_no=readonly_fields.get("report_no"),
            first_reviewer_name=readonly_fields.get("first_reviewer_name"),
            second_reviewer_name=readonly_fields.get("second_reviewer_name"),
            third_reviewer_name=readonly_fields.get("third_reviewer_name"),
            print_room_handler_name=readonly_fields.get("print_room_handler_name"),
            mailing_handler_name=readonly_fields.get("mailing_handler_name"),
            invoice_handler_name=readonly_fields.get("invoice_handler_name"),
            archive_reviewer_name=readonly_fields.get("archive_reviewer_name"),
            current_step=step,
            status_display=step,
        ),
        current_work_order_id=work_order.id if work_order else None,
        current_work_order_status=work_order.current_status if work_order else None,
        current_handler_user_id=work_order.current_handler_user_id if work_order else None,
        contract_reviewer_id=work_order.contract_reviewer_id if work_order else None,
        contract_reviewer_name=contract_reviewer_name,
        contract_review_status=(
            work_order.current_status
            if work_order and work_order.current_status in {
                WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value,
                WorkOrderStatus.CONTRACT_UPLOADED.value,
                WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT.value,
                WorkOrderStatus.CONTRACT_REVIEWING.value,
                WorkOrderStatus.CONTRACT_REJECTED.value,
                WorkOrderStatus.CONTRACT_APPROVED.value,
            }
            else history_contract_status
        ),
        contract_review_status_display=(
            get_contract_review_status_display(work_order.current_status if work_order else None)
            if work_order and work_order.current_status in {
                WorkOrderStatus.WAIT_CONTRACT_UPLOAD.value,
                WorkOrderStatus.CONTRACT_UPLOADED.value,
                WorkOrderStatus.WAIT_CONTRACT_REVIEW_SUBMIT.value,
                WorkOrderStatus.CONTRACT_REVIEWING.value,
                WorkOrderStatus.CONTRACT_REJECTED.value,
                WorkOrderStatus.CONTRACT_APPROVED.value,
            }
            else history_contract_status_display
        ),
        first_reviewer_id=work_order.first_reviewer_id if work_order else None,
        second_reviewer_id=work_order.second_reviewer_id if work_order else None,
        third_reviewer_id=work_order.third_reviewer_id if work_order else None,
        signer_one=work_order.signer_one if work_order else None,
        signer_two=work_order.signer_two if work_order else None,
        formal_report_count=work_order.formal_report_count if work_order else None,
        print_room_handler_id=work_order.print_room_handler_id if work_order else None,
        mailing_handler_user_id=work_order.mailing_handler_user_id if work_order else None,
        archive_reviewer_id=work_order.archive_reviewer_id if work_order else None,
        archive_submitter_id=work_order.archive_submitter_id if work_order else None,
        archive_submission_type=work_order.archive_submission_type if work_order else None,
        mailing_status=work_order.mailing_status if work_order else None,
        user_role_in_project=role,
        available_action=action,
        can_operate=role != "无权限" and not is_termination_locked,
        flow_steps=get_flow_steps(project),
        contract_review_records=contract_review_records,
        project_update_logs=_serialize_project_update_logs(db, project.id),
    )
