"""
app/services/notification_service.py - In-app Notification Dispatch and Management.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.user import User


def create_notification(
    db: Session,
    user_id: int,
    ticket_id: int,
    title: str,
    message: str,
    notification_type: str,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        ticket_id=ticket_id,
        title=title,
        message=message,
        notification_type=notification_type,
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def get_user_notifications(db: Session, user_id: int, unread_only: bool = False) -> List[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).limit(50).all()


def mark_notification_as_read(db: Session, notification_id: int, user_id: int) -> Optional[Notification]:
    notif = db.get(Notification, notification_id)
    if notif and notif.user_id == user_id:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif
