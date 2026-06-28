from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.auth import User
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatUIResponse
from app.services.access_control_service import (
    get_required_permission,
    has_permission,
    is_protected_intent,
)
from app.services.auth_service import get_user_permissions
from app.services.chat_service import get_or_create_chat_session, save_chat_message
from app.services.intent_service import detect_intent

router = APIRouter(prefix="/chat", tags=["chat"])

bearer_scheme = HTTPBearer(auto_error=False)


def get_optional_user_context(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
) -> tuple[User | None, list[str]]:
    if credentials is None:
        return None, []

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None, []

    user = db.query(User).filter(User.id == int(payload["sub"])).first()

    if not user or user.status != "active":
        return None, []

    permissions = get_user_permissions(db, user)

    return user, permissions


@router.post("/message", response_model=ChatMessageResponse)
def chat_message(
    payload: ChatMessageRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user, permissions = get_optional_user_context(credentials, db)

    intent = detect_intent(payload.message)

    session_type = "clinic_operations" if user else "public_health_chat"

    chat_session = get_or_create_chat_session(
        db=db,
        session_id=payload.session_id,
        user_id=user.id if user else None,
        session_type=session_type,
    )

    save_chat_message(
        db=db,
        session_id=chat_session.id,
        sender="user",
        message=payload.message,
        intent=intent,
    )

    if is_protected_intent(intent):
        required_permission = get_required_permission(intent)

        if user is None:
            assistant_message = (
                "Patient search requires authorized clinic access. "
                "Please enter your Employee ID to start secure staff verification."
            )

            save_chat_message(
                db=db,
                session_id=chat_session.id,
                sender="assistant",
                message=assistant_message,
                intent=intent,
            )

            return ChatMessageResponse(
                session_id=chat_session.id,
                message=assistant_message,
                intent=intent,
                requires_auth=True,
                ui=ChatUIResponse(
                    type="auth_required",
                    data={
                        "required_permission": required_permission,
                        "auth_method": "employee_id_totp",
                    },
                ),
            )

        if required_permission and not has_permission(permissions, required_permission):
            assistant_message = (
                "Access denied. Your role does not have permission to perform this action."
            )

            save_chat_message(
                db=db,
                session_id=chat_session.id,
                sender="assistant",
                message=assistant_message,
                intent=intent,
            )

            return ChatMessageResponse(
                session_id=chat_session.id,
                message=assistant_message,
                intent=intent,
                requires_auth=False,
                ui=ChatUIResponse(
                    type="access_denied",
                    data={
                        "required_permission": required_permission,
                    },
                ),
            )

        assistant_message = (
            "You are verified. I can help with patient search. "
            "Next step will connect this intent to the Patient Search Tool."
        )

        save_chat_message(
            db=db,
            session_id=chat_session.id,
            sender="assistant",
            message=assistant_message,
            intent=intent,
        )

        return ChatMessageResponse(
            session_id=chat_session.id,
            message=assistant_message,
            intent=intent,
            requires_auth=False,
            ui=ChatUIResponse(
                type="protected_intent_allowed",
                data={
                    "required_permission": required_permission,
                    "user_role": user.role.role_name,
                },
            ),
        )

    if intent == "public_health_question":
        assistant_message = (
            "I can share general health information, but I cannot diagnose or prescribe treatment. "
            "If symptoms are severe, worsening, or urgent, please contact a healthcare professional."
        )
        ui_type = "public_health_answer"
    else:
        assistant_message = (
            "I can help with general health questions or clinic workflows such as patient search, "
            "appointments, doctor availability, and reminders."
        )
        ui_type = "general_assistant"

    save_chat_message(
        db=db,
        session_id=chat_session.id,
        sender="assistant",
        message=assistant_message,
        intent=intent,
    )

    return ChatMessageResponse(
        session_id=chat_session.id,
        message=assistant_message,
        intent=intent,
        requires_auth=False,
        ui=ChatUIResponse(
            type=ui_type,
            data={},
        ),
    )