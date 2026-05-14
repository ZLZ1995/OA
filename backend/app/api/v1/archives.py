from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.archive import Archive
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.work_order import WorkOrder
from app.schemas.archive import ArchiveCreate, ArchiveDecisionRequest, ArchiveListResponse, ArchiveResponse, ArchiveSubmitRequest, ArchiveUpdate
from app.services.workflow_notification_service import send_workflow_notification
from app.services.workflow_log_service import create_workflow_log
from app.workflows.states import WorkOrderStatus

router = APIRouter(prefix="/archives", tags=["归档"])


@router.get("", response_model=ArchiveListResponse)
def list_archives(
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ARCHIVE_MANAGER", "ADMIN", "PROJECT_LEADER", "PROJECT_MEMBER")),
) -> ArchiveListResponse:
    rows = db.query(Archive).order_by(Archive.id.desc()).all()
    return ArchiveListResponse(items=[ArchiveResponse.model_validate(item, from_attributes=True) for item in rows])


@router.post("", response_model=ArchiveResponse, status_code=status.HTTP_201_CREATED)
def create_archive(
    payload: ArchiveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ARCHIVE_MANAGER", "ADMIN")),
) -> ArchiveResponse:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")

    exists = db.query(Archive).filter(Archive.work_order_id == payload.work_order_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="该工单已归档")

    row = Archive(**payload.model_dump(), archived_by=current_user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ArchiveResponse.model_validate(row, from_attributes=True)


def _ensure_project_operator(db: Session, work_order: WorkOrder, user: User) -> None:
    if any(item.role.code == "ADMIN" for item in user.roles):
        return
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == work_order.project_id, ProjectMember.user_id == user.id).first()
    if work_order.project_leader_id != user.id and not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可提交底稿")


def _ensure_archive_reviewer(db: Session, user_id: int) -> None:
    exists = (
        db.query(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(User, User.id == UserRole.user_id)
        .filter(User.id == user_id, User.is_active.is_(True), Role.code == "ARCHIVE_MANAGER")
        .first()
    )
    if not exists:
        raise HTTPException(status_code=400, detail="请选择有效的档案管理员")


@router.post("/submit")
def submit_archive(
    payload: ArchiveSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _ensure_project_operator(db, work_order, current_user)
    _ensure_archive_reviewer(db, payload.reviewer_user_id)
    if payload.submission_type not in {"ONLINE", "OFFLINE"}:
        raise HTTPException(status_code=400, detail="底稿提交方式不正确")
    from_status = WorkOrderStatus(work_order.current_status)
    work_order.archive_reviewer_id = payload.reviewer_user_id
    work_order.archive_submitter_id = current_user.id
    work_order.archive_submission_type = payload.submission_type
    work_order.current_status = WorkOrderStatus.ARCHIVE_REVIEWING.value
    work_order.current_handler_user_id = payload.reviewer_user_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=WorkOrderStatus.ARCHIVE_REVIEWING.value,
        action_type=f"ARCHIVE_SUBMIT_{payload.submission_type}",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    if project:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=payload.reviewer_user_id,
            action_name=f"ARCHIVE_SUBMIT_{payload.submission_type}",
            comment=payload.remark,
        )
    db.commit()
    return {"message": "已提交底稿，待审查"}


@router.post("/approve")
def approve_archive(
    payload: ArchiveDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ARCHIVE_MANAGER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.archive_reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅选定档案管理员可审核")
    if not work_order.archive_submission_type or work_order.archive_submission_type == "APPROVED":
        raise HTTPException(status_code=400, detail="当前无待审核底稿")
    from_status = WorkOrderStatus(work_order.current_status)
    work_order.archive_submission_type = "APPROVED"
    work_order.current_status = WorkOrderStatus.WAIT_ARCHIVE_SUBMIT.value
    work_order.current_handler_user_id = work_order.archive_submitter_id or work_order.project_leader_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=WorkOrderStatus.WAIT_ARCHIVE_SUBMIT.value,
        action_type="ARCHIVE_APPROVE",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    receiver_user_id = work_order.archive_submitter_id or work_order.project_leader_id
    if project and receiver_user_id:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=receiver_user_id,
            action_name="ARCHIVE_APPROVE",
            comment=payload.remark,
        )
    db.commit()
    return {"message": "底稿审核通过，待项目人员确认归档"}


@router.post("/finalize")
def finalize_archive(
    payload: ArchiveDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    _ensure_project_operator(db, work_order, current_user)
    if work_order.archive_submission_type != "APPROVED":
        raise HTTPException(status_code=400, detail="底稿审核通过后才可归档")
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    exists = db.query(Archive).filter(Archive.work_order_id == work_order.id).first()
    if not exists:
        db.add(Archive(
            work_order_id=work_order.id,
            archived_by=current_user.id,
            archive_no=work_order.work_order_no,
            archive_location=None,
            archive_at=datetime.now(),
            remark=payload.remark,
        ))
    if project:
        project.archived_at = datetime.now()
    from_status = WorkOrderStatus(work_order.current_status)
    work_order.current_status = WorkOrderStatus.ARCHIVED.value
    work_order.current_handler_user_id = None
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=WorkOrderStatus.ARCHIVED.value,
        action_type="ARCHIVE_FINALIZE",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    if project:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=project.project_leader_id,
            action_name="ARCHIVE_FINALIZE",
            comment=payload.remark,
        )
    db.commit()
    return {"message": "项目已归档"}


@router.post("/reject")
def reject_archive(
    payload: ArchiveDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: set[str] = Depends(require_roles("ARCHIVE_MANAGER", "ADMIN")),
) -> dict[str, str]:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == payload.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if work_order.archive_reviewer_id != current_user.id and not any(item.role.code == "ADMIN" for item in current_user.roles):
        raise HTTPException(status_code=403, detail="仅选定档案管理员可审核")
    if not work_order.archive_submission_type or work_order.archive_submission_type == "APPROVED":
        raise HTTPException(status_code=400, detail="当前无待审核底稿")
    from_status = WorkOrderStatus(work_order.current_status)
    work_order.archive_submission_type = "REJECTED"
    work_order.current_status = WorkOrderStatus.ARCHIVE_REJECTED.value
    work_order.current_handler_user_id = work_order.archive_submitter_id or work_order.project_leader_id
    create_workflow_log(
        db,
        work_order_id=work_order.id,
        from_status=from_status.value,
        to_status=WorkOrderStatus.ARCHIVE_REJECTED.value,
        action_type="ARCHIVE_REJECT",
        operator_user_id=current_user.id,
        remark=payload.remark,
    )
    project = db.query(Project).filter(Project.id == work_order.project_id).first()
    receiver_user_id = work_order.archive_submitter_id or work_order.project_leader_id
    if project and receiver_user_id:
        send_workflow_notification(
            db,
            project=project,
            work_order=work_order,
            sender_user=current_user,
            receiver_user_id=receiver_user_id,
            action_name="ARCHIVE_REJECT",
            comment=payload.remark,
        )
    db.commit()
    return {"message": "审核未通过，已返回修改"}


@router.patch("/{archive_id}", response_model=ArchiveResponse)
def update_archive(
    archive_id: int,
    payload: ArchiveUpdate,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ARCHIVE_MANAGER", "ADMIN")),
) -> ArchiveResponse:
    row = db.query(Archive).filter(Archive.id == archive_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="归档记录不存在")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ArchiveResponse.model_validate(row, from_attributes=True)
