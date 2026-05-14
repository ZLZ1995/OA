from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.user_notification import UserNotification
from app.schemas.notification import NotificationItem, NotificationListResponse, NotificationReadResponse
from app.services.notification_service import mark_notification_read

router = APIRouter(prefix="/notifications", tags=["消息中心"])


@router.get("/mine", response_model=NotificationListResponse)
def list_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    rows = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.id)
        .order_by(UserNotification.created_at.desc(), UserNotification.id.desc())
        .all()
    )
    return NotificationListResponse(
        items=[
            NotificationItem(
                id=row.id,
                biz_type=row.biz_type,
                biz_id=row.biz_id,
                title=row.title,
                content=row.content,
                link_type=row.link_type,
                link_target_id=row.link_target_id,
                is_read=row.is_read,
                popup_flag=row.popup_flag,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )


@router.post("/{notification_id}/read", response_model=NotificationReadResponse)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationReadResponse:
    row = db.query(UserNotification).filter(UserNotification.id == notification_id, UserNotification.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="消息不存在")
    mark_notification_read(db, row)
    db.commit()
    return NotificationReadResponse()
