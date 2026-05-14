from datetime import datetime

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: int
    biz_type: str
    biz_id: int
    title: str
    content: str
    link_type: str | None = None
    link_target_id: int | None = None
    is_read: bool
    popup_flag: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]


class NotificationReadResponse(BaseModel):
    message: str = "ok"
