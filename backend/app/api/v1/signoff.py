from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.services.archive_sync_service import sync_signoff_files_to_archive
from app.services.project_role_conflict_service import get_project_party_user_ids, validate_support_role_not_project_party
from app.services.workflow_log_service import create_workflow_log
from app.services.workflow_notification_service import send_workflow_notification
from app.workflows.states import WorkOrderStatus

router = APIRouter(prefix="/signoff", tags=["signoff"])


class SignoffApproveRequest(BaseModel):
    print_room_handler_id: int


class EnterSignoffReviewRequest(BaseModel):
    formal_report_count: int
    signer_one: str
    signer_two: str


def _is_project_party(db: Session, work_order: WorkOrder, current_user: User) -> bool:
    if current_user.id in {work_order.project_leader_id, work_order.initiator_user_id}:
        return True
    return db.query(ProjectMember.id).filter(
        ProjectMember.project_id == work_order.project_id,
        ProjectMember.user_id == current_user.id,
    ).first() is not None


def _get_project(db: Session, work_order: WorkOrder) -> Project | None:
    return db.query(Project).filter(Project.id == work_order.project_id).first()


def _get_chief_appraiser(db: Session) -> User | None:
    return (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            User.is_active.is_(True),
            User.username != settings.initial_admin_username,
            Role.code == "CHIEF_APPRAISER",
        )
        .order_by(User.id.asc())
        .first()
    )


def _resolve_signoff_chief_appraiser(db: Session, work_order: WorkOrder) -> User | None:
    if work_order.chief_appraiser_user_id:
        assigned = (
            db.query(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .filter(
                User.id == work_order.chief_appraiser_user_id,
                User.is_active.is_(True),
                User.username != settings.initial_admin_username,
                Role.code == "CHIEF_APPRAISER",
            )
            .first()
        )
        if assigned:
            return assigned
    return _get_chief_appraiser(db)


def _ensure_print_room_handler(db: Session, work_order: WorkOrder, handler_user_id: int) -> User:
    validate_support_role_not_project_party(
        handler_user_id,
        get_project_party_user_ids(db, work_order.project_id, work_order),
        "文印室人员",
    )
    handler = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            User.id == handler_user_id,
            User.is_active.is_(True),
            User.username != settings.initial_admin_username,
            Role.code == "PRINT_ROOM",
        )
        .first()
    )
    if not handler:
        raise HTTPException(status_code=400, detail="请选择有效的文印室人员")
    return handler


def _ensure_formal_report_count(value: int) -> int:
    if value < 1:
        raise HTTPException(status_code=400, detail="报告出具数量必须大于 0")
    return value


def _ensure_signer_name(value: str, label: str) -> str:
    signer = (value or "").strip()
    if not signer:
        raise HTTPException(status_code=400, detail=f"请填写{label}")
    return signer


@router.post("/work-orders/{work_order_id}/request-owner-confirm")
def request_owner_external_audit_confirm(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("THIRD_REVIEWER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.current_status != WorkOrderStatus.THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND.value:
        raise HTTPException(status_code=400, detail="当前状态不可发送外部审核确认")

    project = _get_project(db, work_order)
    work_order.current_status = WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM.value
    work_order.current_handler_user_id = work_order.project_leader_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=WorkOrderStatus.THIRD_APPROVED_WAIT_OWNER_CONFIRM_SEND.value,
        to_status=WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM.value,
        action_type="REQUEST_OWNER_EXTERNAL_AUDIT_CONFIRM",
        operator_user_id=current_user.id,
        remark="三审通过后发送外部审核确认",
    )
    if project and work_order.project_leader_id:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=work_order.project_leader_id,
            action_name="REQUEST_OWNER_EXTERNAL_AUDIT_CONFIRM",
            comment="请确认是否涉及外部审核",
        )
    db.commit()
    return {"message": "已发送项目负责人确认"}


@router.post("/work-orders/{work_order_id}/mark-no-external")
def mark_no_external_audit(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not any(item.role.code == "ADMIN" for item in current_user.roles) and not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可操作")
    if work_order.current_status != WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM.value:
        raise HTTPException(status_code=400, detail="当前状态不可确认不涉及外部审核")

    project = _get_project(db, work_order)
    work_order.current_status = WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value
    work_order.current_handler_user_id = work_order.project_leader_id
    work_order.signoff_status = "WAIT_UPLOAD"
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM.value,
        to_status=WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value,
        action_type="MARK_NO_EXTERNAL_AUDIT",
        operator_user_id=current_user.id,
        remark="不涉及外部审核",
    )
    if project:
        for receiver_user_id in {work_order.project_leader_id, work_order.initiator_user_id}:
            if receiver_user_id:
                send_workflow_notification(
                    db,
                    project=project,
                    work_order=work_order,
                    sender_user=current_user,
                    receiver_user_id=receiver_user_id,
                    action_name="WAIT_OWNER_SIGNOFF_UPLOAD",
                    comment="请上传报告附件和合同扫描件",
                )
    db.commit()
    return {"message": "已进入上传报告附件与合同扫描件流程"}


@router.post("/work-orders/{work_order_id}/mark-has-external")
def mark_has_external_audit(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not any(item.role.code == "ADMIN" for item in current_user.roles) and not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可操作")
    if work_order.current_status != WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM.value:
        raise HTTPException(status_code=400, detail="当前状态不可确认涉及外部审核")

    project = _get_project(db, work_order)
    work_order.current_status = WorkOrderStatus.WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT.value
    work_order.current_handler_user_id = work_order.project_leader_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=WorkOrderStatus.WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM.value,
        to_status=WorkOrderStatus.WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT.value,
        action_type="MARK_HAS_EXTERNAL_AUDIT",
        operator_user_id=current_user.id,
        remark="涉及外部审核",
    )
    if project and work_order.project_leader_id:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=work_order.project_leader_id,
            action_name="WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT",
            comment="请上传报告文件和外部审核意见并发起外部审核复核",
        )
    db.commit()
    return {"message": "已进入外部审核复核准备流程"}


@router.post("/work-orders/{work_order_id}/enter-review")
def enter_signoff_review(
    work_order_id: int,
    payload: EnterSignoffReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("PROJECT_LEADER", "PROJECT_MEMBER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if not any(item.role.code == "ADMIN" for item in current_user.roles) and not _is_project_party(db, work_order, current_user):
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可操作")
    if work_order.current_status != WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value:
        raise HTTPException(status_code=400, detail="当前状态不可进入签发审核")

    chief = _resolve_signoff_chief_appraiser(db, work_order)
    if chief is None:
        raise HTTPException(status_code=400, detail="系统未配置首席评估师账号")
    formal_report_count = _ensure_formal_report_count(payload.formal_report_count)
    signer_one = _ensure_signer_name(payload.signer_one, "签字评估师一")
    signer_two = _ensure_signer_name(payload.signer_two, "签字评估师二")

    project = _get_project(db, work_order)
    work_order.current_status = WorkOrderStatus.SIGNOFF_REVIEWING.value
    work_order.current_handler_user_id = chief.id
    work_order.chief_appraiser_user_id = chief.id
    work_order.formal_report_count = formal_report_count
    work_order.signer_one = signer_one
    work_order.signer_two = signer_two
    work_order.signoff_status = "REVIEWING"
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value,
        to_status=WorkOrderStatus.SIGNOFF_REVIEWING.value,
        action_type="ENTER_SIGNOFF_REVIEW",
        operator_user_id=current_user.id,
        remark="进入签发审核",
    )
    if project:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=chief.id,
            action_name="ENTER_SIGNOFF_REVIEW",
            comment="请处理签发审核",
        )
    db.commit()
    return {"message": "已进入签发审核"}


@router.post("/work-orders/{work_order_id}/approve")
def approve_signoff(
    work_order_id: int,
    payload: SignoffApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("CHIEF_APPRAISER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    is_repair_assign = (
        work_order.current_status == WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value
        and work_order.signoff_status == "APPROVED"
        and not work_order.print_room_handler_id
    )
    if work_order.current_status != WorkOrderStatus.SIGNOFF_REVIEWING.value and not is_repair_assign:
        raise HTTPException(status_code=400, detail="当前状态不可执行签发通过")
    handler = _ensure_print_room_handler(db, work_order, payload.print_room_handler_id)
    formal_report_count = _ensure_formal_report_count(work_order.formal_report_count or 0)

    project = _get_project(db, work_order)
    from_status = work_order.current_status
    work_order.current_status = WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value
    work_order.print_room_handler_id = handler.id
    work_order.current_handler_user_id = handler.id
    work_order.formal_report_count = formal_report_count
    work_order.signoff_status = "APPROVED"
    if not is_repair_assign:
        sync_signoff_files_to_archive(db, work_order, current_user.id)
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status,
        to_status=WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value,
        action_type="ASSIGN_PRINT_ROOM_AFTER_SIGNOFF" if is_repair_assign else "APPROVE_SIGNOFF",
        operator_user_id=current_user.id,
        remark="补充指定文印室人员和报告出具数量" if is_repair_assign else "同意签发",
    )
    if project:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=handler.id,
            action_name="ASSIGN_PRINT_ROOM_AFTER_SIGNOFF" if is_repair_assign else "APPROVE_SIGNOFF",
            comment="签发已通过，请进入报告出具",
        )
    db.commit()
    return {"message": "签发通过，已进入报告出具"}


@router.post("/work-orders/{work_order_id}/return-third")
def return_signoff_to_third_review(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("CHIEF_APPRAISER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.current_status != WorkOrderStatus.SIGNOFF_REVIEWING.value:
        raise HTTPException(status_code=400, detail="当前状态不可退回三审")

    project = _get_project(db, work_order)
    work_order.current_status = WorkOrderStatus.THIRD_REVIEWING.value
    work_order.current_handler_user_id = work_order.third_reviewer_id
    work_order.signoff_status = "RETURNED_TO_THIRD"
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=WorkOrderStatus.SIGNOFF_REVIEWING.value,
        to_status=WorkOrderStatus.THIRD_REVIEWING.value,
        action_type="RETURN_SIGNOFF_TO_THIRD",
        operator_user_id=current_user.id,
        remark="签发退回三审",
    )
    if project:
        for receiver_user_id in {work_order.project_leader_id, work_order.third_reviewer_id}:
            if receiver_user_id:
                send_workflow_notification(
                    db,
                    project=project,
                    work_order=work_order,
                    sender_user=current_user,
                    receiver_user_id=receiver_user_id,
                    action_name="RETURN_SIGNOFF_TO_THIRD",
                    comment="签发认为报告需修改，已退回三审",
                )
    db.commit()
    return {"message": "已退回三审"}


@router.post("/work-orders/{work_order_id}/return-owner-upload")
def return_signoff_to_owner_upload(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("CHIEF_APPRAISER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.current_status != WorkOrderStatus.SIGNOFF_REVIEWING.value:
        raise HTTPException(status_code=400, detail="当前状态不可退回项目负责人")

    project = _get_project(db, work_order)
    work_order.current_status = WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value
    work_order.current_handler_user_id = work_order.project_leader_id
    work_order.signoff_status = "RETURNED_TO_OWNER"
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=WorkOrderStatus.SIGNOFF_REVIEWING.value,
        to_status=WorkOrderStatus.WAIT_OWNER_SIGNOFF_UPLOAD.value,
        action_type="RETURN_SIGNOFF_TO_OWNER_UPLOAD",
        operator_user_id=current_user.id,
        remark="签发认为附件或合同有误",
    )
    if project:
        for receiver_user_id in {work_order.project_leader_id, work_order.initiator_user_id}:
            if receiver_user_id:
                send_workflow_notification(
                    db,
                    project=project,
                    work_order=work_order,
                    sender_user=current_user,
                    receiver_user_id=receiver_user_id,
                    action_name="RETURN_SIGNOFF_TO_OWNER_UPLOAD",
                    comment="签发认为附件或合同有误，请重新上传",
                )
    db.commit()
    return {"message": "已退回项目负责人上传附件"}
