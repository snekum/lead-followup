"""Apply WhatsApp delivery-status callbacks to stored messages."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Message
from app.domain.enums import MessageStatus

_STATUS_MAP = {
    "sent": MessageStatus.SENT,
    "delivered": MessageStatus.DELIVERED,
    "read": MessageStatus.READ,
    "failed": MessageStatus.FAILED,
}


def update_message_status(
    session: Session, *, provider_message_id: str | None, status: str
) -> bool:
    mapped = _STATUS_MAP.get(status.lower())
    if mapped is None or not provider_message_id:
        return False
    message = session.scalar(
        select(Message).where(Message.provider_message_id == provider_message_id)
    )
    if message is None:
        return False
    message.status = mapped
    return True
