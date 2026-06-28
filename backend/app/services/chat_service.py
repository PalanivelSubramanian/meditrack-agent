from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession


def get_or_create_chat_session(
    db: Session,
    session_id: int | None,
    user_id: int | None,
    session_type: str,
) -> ChatSession:
    if session_id:
        existing = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if existing:
            return existing

    session = ChatSession(
        user_id=user_id,
        session_type=session_type,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def save_chat_message(
    db: Session,
    session_id: int,
    sender: str,
    message: str,
    intent: str | None = None,
) -> ChatMessage:
    chat_message = ChatMessage(
        session_id=session_id,
        sender=sender,
        message=message,
        intent=intent,
    )
    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)

    return chat_message