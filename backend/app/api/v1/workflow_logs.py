from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workflow_log import WorkflowLog
from app.schemas.workflow_log import WorkflowLogListResponse, WorkflowLogResponse

router = APIRouter(prefix="/workflow-logs", tags=["流转日志"])


@router.get("/work-orders/{work_order_id}", response_model=WorkflowLogListResponse)
def list_workflow_logs(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WorkflowLogListResponse:
    rows = (
        db.query(WorkflowLog)
        .filter(WorkflowLog.work_order_id == work_order_id)
        .order_by(WorkflowLog.created_at.desc())
        .all()
    )
    return WorkflowLogListResponse(
        items=[
            WorkflowLogResponse(
                id=row.id,
                work_order_id=row.work_order_id,
                from_status=row.from_status,
                to_status=row.to_status,
                action_type=row.action_type,
                operator_user_id=row.operator_user_id,
                remark=row.remark,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )
