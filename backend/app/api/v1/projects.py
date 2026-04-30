from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.project_member import ProjectMember
from app.schemas.project_flow import ProjectFlowProject, ProjectFlowResponse
from app.services.project_flow import FLOW_STEPS, assert_project_creator, build_todo_action, get_project_status_display, get_user_role_in_project, is_system_admin, normalize_project_step
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["项目"])
UNIT_CODE_MAP = {"中勤": "ZQ", "中立国际": "ZLGJ", "中众": "ZZ", "其他": "QT"}
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
    assert_project_creator(row, current_user)
    if row.archived_at is None:
        row.archived_at = datetime.now()
    db.commit()
    db.refresh(row)
    return _serialize_project(db, row)


@router.get("/{project_id}/flow", response_model=ProjectFlowResponse)
def get_project_flow(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectFlowResponse:
    if is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="系统管理员不参与业务流程")

    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project_id).order_by(WorkOrder.id.desc()).first()
    is_member = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id).first() is not None

    role = get_user_role_in_project(project, work_order, current_user, is_member)
    if role == "无权限":
        raise HTTPException(status_code=403, detail="无权查看该项目")

    step = normalize_project_step(work_order.current_status if work_order else None, project.archived_at is not None)
    action = build_todo_action(step, role) or "当前暂无待办操作"
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
        user_role_in_project=role,
        available_action=action,
        can_operate=role != "无权限",
        flow_steps=FLOW_STEPS,
    )
