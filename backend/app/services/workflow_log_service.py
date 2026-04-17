from sqlalchemy.orm import Session

from app.models.workflow_log import WorkflowLog


def create_workflow_log(
    db: Session,
    *,
    work_order_id: int,
    from_status: str,
    to_status: str,
    action_type: str,
    operator_user_id: int,
    remark: str | None = None,
) -> WorkflowLog:
    row = WorkflowLog(
        work_order_id=work_order_id,
        from_status=from_status,
        to_status=to_status,
        action_type=action_type,
        operator_user_id=operator_user_id,
        remark=remark,
    )
    db.add(row)
    return row
