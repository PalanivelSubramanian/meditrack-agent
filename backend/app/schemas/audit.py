from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action_type: str
    entity_type: str | None
    entity_id: int | None
    permission_checked: str | None
    access_granted: bool
    details: str | None
    created_at: datetime

    class Config:
        from_attributes = True