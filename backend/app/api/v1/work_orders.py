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
    WorkOrderStatus.CONTRACT_UPLOADED.value: "合同上传",
    WorkOrderStatus.WAIT_PRINTROOM_OFFICIAL_CONTRACT.value: "合同上传",
    WorkOrderStatus.WAIT_FIRST_REVIEW_SUBMIT.value: "一审",
    WorkOrderStatus.FIRST_REVIEWING.value: "一审",
    WorkOrderStatus.FIRST_REVIEW_REJECTED.value: "一审",
    WorkOrderStatus.FIRST_APPROVED_WAIT_LEADER_SUBMIT_SECOND.value: "二审",
    WorkOrderStatus.WAIT_SECOND_REVIEW_SUBMIT.value: "二审",
    WorkOrderStatus.SECOND_REVIEWING.value: "二审",
    WorkOrderStatus.SECOND_REVIEW_REJECTED.value: "二审",
    WorkOrderStatus.SECOND_APPROVED_WAIT_LEADER_SUBMIT_THIRD.value: "三审",
    WorkOrderStatus.WAIT_THIRD_REVIEW_SUBMIT.value: "三审",
    WorkOrderStatus.THIRD_REVIEWING.value: "三审",
    WorkOrderStatus.THIRD_REVIEW_REJECTED.value: "三审",
    WorkOrderStatus.THIRD_APPROVED_WAIT_PRINTROOM.value: "文印室出具",
    WorkOrderStatus.PRINTROOM_PROCESSING.value: "文印室出具",
    WorkOrderStatus.PAPER_REPORT_ISSUED.value: "文印室出具",
    "ARCHIVED": "已归档",
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
    title = project.project_name
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
        title=title,
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
    _: set[str] = Depends(require_roles("ADMIN", "SALES", "PROJECT_LEADER")),
) -> WorkOrderResponse:
    row = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")

    data = payload.model_dump(exclude_unset=True)
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
