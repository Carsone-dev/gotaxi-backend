from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.notification import NotifType


class NotificationRead(BaseModel):
    id: UUID
    type: NotifType
    titre: str
    corps: str
    lue: bool
    data: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    count: int