"""Prevent approval shortcuts while disabled assignees await reassignment."""
from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.work_order import WorkOrder
from app.models.invoice import Invoice
from app.models.archive import Archive
from app.models.contract_review_record import ContractReviewRecord
from app.services.project_handover import assert_review_assignments_ready


async def require_ready_assignments(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    values = dict(request.query_params)
    if "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
        except ValueError:
            return  # The endpoint's normal validation reports malformed input.
        if isinstance(body, dict):
            values.update(body)
    values.update(request.path_params)
    try:
        order_id = int(values.get("work_order_id") or 0)
        project_id = int(values.get("project_id") or 0)
    except (ValueError, TypeError):
        raise HTTPException(400, "项目或工单编号格式无效")
    # Record-based endpoints must resolve the actual order, never trust a body override.
    for key, model in (("invoice_id", Invoice), ("archive_id", Archive), ("record_id", ContractReviewRecord)):
        if key in request.path_params:
            try:
                record = db.get(model, int(request.path_params[key]))
            except (ValueError, TypeError):
                return
            if not record:
                return
            order_id = record.work_order_id
            break
    if not order_id and project_id:
        order = db.query(WorkOrder).filter_by(project_id=project_id).order_by(WorkOrder.id.desc()).first()
        order_id = order.id if order else 0
    if order_id:
        assert_review_assignments_ready(db, order_id)
