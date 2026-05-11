from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.archive import Archive
from app.models.project import Project
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.project_member import ProjectMember
from app.workflows.states import WorkOrderStatus
from app.schemas.project_flow import ProjectFlowProject, ProjectFlowResponse
from app.services.workflow_log_service import create_workflow_log
from app.services.project_flow import FLOW_STEPS, assert_project_creator, build_todo_action, get_project_status_display, get_user_role_in_project, normalize_project_step
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["项目"])
UNIT_CODE_MAP = {"中勤": "ZQ", "中立国际": "ZLGJ", "中众": "ZZ", "其他": "QT"}
class ProjectTerminationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


STATUS_DISPLAY_MAP = {
    "PROJECT_CREATED": "项目创建",
    "WORK_ORDER_CREATED": "工单创建",
    "CONTRACT_UPLOADED": "合同上传",
    "FIRST_REVIEWING": "一审",
    "SECOND_REVIEWING": "二审",
    "THIRD_REVIEWING": "三审",
    "PAPER_REPORT_ISSUED": "文印室出具",
    "ARCHIVED": "已归档",
}


def _build_status_display(project: Project, latest_work_order_status: str | None) -> str:
    return get_project_status_display(latest_work_order_status, project.archived_at is not None)


def _serialize_project(db: Session, project: Project) -> ProjectResponse:
    latest_status = (
        db.query(WorkOrder.current_status)
        .filter(WorkOrder.project_id == project.id)
        .order_by(WorkOrder.id.desc())
        .limit(1)
        .scalar()
    )
    data = ProjectResponse.model_validate(project, from_attributes=True).model_dump()
    data.pop("status", None)
    data.pop("status_display", None)
    data.pop("current_status", None)
    status_cn = _build_status_display(project, latest_status)
    return ProjectResponse(
        **data,
        status=status_cn,
        status_display=status_cn,
    )


def _generate_project_code(db: Session, undertaking_unit: str) -> str:
    unit_code = UNIT_CODE_MAP.get(undertaking_unit)
    if not unit_code:
        raise HTTPException(status_code=400, detail="不支持的项目承接单位")
    now = datetime.now()
    yyyymm = now.strftime("%Y%m")
    prefix = f"{unit_code}-{yyyymm}-"
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


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProjectListResponse:
    rows = (
        db.query(Project)
        .filter(Project.deleted_at.is_(None))
        .order_by(Project.id.desc())
        .all()
    )
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
    current_user: User = Depends(get_current_user),
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

    work_order = WorkOrder(
        work_order_no=row.project_code,
        project_id=row.id,
        title=row.project_name,
        current_status=WorkOrderStatus.WORK_ORDER_CREATED.value,
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
    assert_project_creator(row, current_user)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
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
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="项目已归档，不可删除")
    if row.termination_status == "PENDING":
        raise HTTPException(status_code=400, detail="项目终止/废止审核中，不可删除")
    assert_project_creator(row, current_user)
    row.deleted_at = datetime.now()
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
    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project_id).order_by(WorkOrder.id.desc()).first()
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None
    if row.business_user_id != current_user.id and row.project_leader_id != current_user.id and not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可归档")
    termination_approved = row.termination_status == "APPROVED"
    if not work_order or (work_order.archive_submission_type != "APPROVED" and not termination_approved):
        raise HTTPException(status_code=400, detail="底稿审核通过或终止/废止审核通过后才可归档")
    if row.archived_at is None:
        row.archived_at = datetime.now()
    archived = db.query(Archive).filter(Archive.work_order_id == work_order.id).first()
    if not archived:
        db.add(Archive(
            work_order_id=work_order.id,
            archived_by=current_user.id,
            archive_no=work_order.work_order_no,
            archive_location=None,
            archive_at=datetime.now(),
            remark="项目人员确认归档",
        ))
    if work_order:
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
    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project_id).order_by(WorkOrder.id.desc()).first()
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None
    if row.business_user_id != current_user.id and row.project_leader_id != current_user.id and not is_member:
        raise HTTPException(status_code=403, detail="仅项目负责人或项目组成员可申请终止/废止")
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

    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project_id).order_by(WorkOrder.id.desc()).first()
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

    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project_id).order_by(WorkOrder.id.desc()).first()
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None

    role = get_user_role_in_project(project, work_order, current_user, is_member)
    if role == "无权限":
        raise HTTPException(status_code=403, detail="无权查看该项目")

    step = normalize_project_step(work_order.current_status if work_order else None, project.archived_at is not None)
    is_termination_locked = project.termination_status in {"PENDING", "APPROVED"}
    action = "项目终止/废止流程处理中，当前业务已锁定" if is_termination_locked else build_todo_action(step, role) or "当前暂无待办操作"
    return ProjectFlowResponse(
        project=ProjectFlowProject(
            id=project.id,
            project_no=project.project_code,
            project_name=project.project_name,
            client_name=project.client_name,
            undertaking_unit=project.undertaking_unit,
            current_step=step,
            status_display=step,
        ),
        current_work_order_id=work_order.id if work_order else None,
        current_work_order_status=work_order.current_status if work_order else None,
        current_handler_user_id=work_order.current_handler_user_id if work_order else None,
        first_reviewer_id=work_order.first_reviewer_id if work_order else None,
        second_reviewer_id=work_order.second_reviewer_id if work_order else None,
        third_reviewer_id=work_order.third_reviewer_id if work_order else None,
        signer_one=work_order.signer_one if work_order else None,
        signer_two=work_order.signer_two if work_order else None,
        formal_report_count=work_order.formal_report_count if work_order else None,
        print_room_handler_id=work_order.print_room_handler_id if work_order else None,
        archive_reviewer_id=work_order.archive_reviewer_id if work_order else None,
        archive_submitter_id=work_order.archive_submitter_id if work_order else None,
        archive_submission_type=work_order.archive_submission_type if work_order else None,
        user_role_in_project=role,
        available_action=action,
        can_operate=role != "无权限" and not is_termination_locked,
        flow_steps=FLOW_STEPS,
    )
