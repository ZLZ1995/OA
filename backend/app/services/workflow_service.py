from fastapi import HTTPException, status

from app.workflows.states import WorkOrderStatus
from app.workflows.transitions import can_transit


def ensure_transition_allowed(from_status: WorkOrderStatus, to_status: WorkOrderStatus) -> None:
    """Guard for workflow state transition."""
    if not can_transit(from_status, to_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"非法状态流转: {from_status} -> {to_status}",
        )
