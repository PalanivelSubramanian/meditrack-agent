from pydantic import BaseModel
from typing import Any


class ChatMessageRequest(BaseModel):
    message: str
    session_id: int | None = None


class ChatUIResponse(BaseModel):
    type: str
    data: dict[str, Any] = {}


class ChatMessageResponse(BaseModel):
    session_id: int
    message: str
    intent: str
    requires_auth: bool = False
    ui: ChatUIResponse