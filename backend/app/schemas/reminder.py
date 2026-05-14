from datetime import datetime

from pydantic import BaseModel, Field


class ReminderEligibilityResponse(BaseModel):
    can_remind: bool
    reason_code: str | None = None
    reason_message: str | None = None
    current_handler_user_id: int | None = None
    current_handler_name: str | None = None
    elapsed_seconds: int = 0
    remaining_seconds_to_48h: int = 0
    today_remind_count: int = 0
    remaining_seconds_to_next_remind: int = 0
    current_status: str | None = None


class ReminderCreateRequest(BaseModel):
    work_order_id: int
    comment: str | None = Field(default=None, max_length=2000)


class ReminderCreateResponse(BaseModel):
    reminder_event_id: int
    today_remind_count: int
    message: str


class ReminderHistoryItem(BaseModel):
    reminder_event_id: int
    project_id: int
    work_order_id: int
    work_order_no: str | None = None
    current_status: str
    initiator_user_id: int
    initiator_user_name: str | None = None
    current_handler_user_id: int
    current_handler_user_name: str | None = None
    overdue_seconds: int
    comment: str | None = None
    day_remind_seq: int
    created_at: datetime
    primary_read_status: str = "UNREAD"
    primary_read_at: datetime | None = None
    delivery_status: str = "SENT"


class ReminderHistoryResponse(BaseModel):
    items: list[ReminderHistoryItem]
