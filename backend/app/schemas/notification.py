from datetime import datetime

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: int
    biz_type: str
    biz_id: int
    title: str
    content: str
    message_type: str
    priority: str
    sender_user_id: int | None = None
    sender_user_name: str | None = None
    project_id: int | None = None
    project_code: str | None = None
    project_name: str | None = None
    client_name: str | None = None
    work_order_id: int | None = None
    work_order_no: str | None = None
    work_order_title: str | None = None
    current_status: str | None = None
    current_handler_user_id: int | None = None
    current_handler_user_name: str | None = None
    process_status: str
    cc_flag: bool = False
    receiver_user_name: str | None = None
    group_key: str | None = None
    link_type: str | None = None
    link_target_id: int | None = None
    is_read: bool
    popup_flag: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    total: int = 0
    page: int = 1
    page_size: int = 20


class NotificationStatsResponse(BaseModel):
    today_new_count: int
    unread_count: int
    today_reminder_count: int
    read_rate: float
    avg_process_duration_seconds: int
    latest_notification_id: int | None = None
    server_time: datetime


class NotificationBatchReadRequest(BaseModel):
    notification_ids: list[int]


class NotificationDetailResponse(NotificationItem):
    pass


class NotificationTimelineItem(BaseModel):
    event_type: str
    title: str
    operator_user_name: str | None = None
    status: str | None = None
    created_at: datetime
    remark: str | None = None


class NotificationTimelineResponse(BaseModel):
    items: list[NotificationTimelineItem]


class NotificationReadResponse(BaseModel):
    message: str = "ok"
