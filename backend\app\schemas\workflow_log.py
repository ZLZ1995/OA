from datetime import datetime

from pydantic import BaseModel


class WorkflowLogResponse(BaseModel):
    id: int
    work_order_id: int
    from_status: str
    to_status: str
    action_type: str
    operator_user_id: int
    remark: str | None
    created_at: datetime


class WorkflowLogListResponse(BaseModel):
    items: list[WorkflowLogResponse]
