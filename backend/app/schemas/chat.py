from pydantic import BaseModel, Field
from typing import Any


class ChatMessageRequest(BaseModel):
    message: str
    session_id: int | None = None


class IntentResult(BaseModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    entities: dict[str, Any] = {}


class ChatUIResponse(BaseModel):
    type: str
    data: dict[str, Any] = {}


class ChatMessageResponse(BaseModel):
    session_id: int
    message: str
    intent: str
    requires_auth: bool = False
    ui: ChatUIResponse