from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.sql import func

from app.db.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    selected_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    workflow_state = Column(JSON, nullable=True)
    
    session_type = Column(String(50), nullable=False, default="public_health_chat")

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)

    sender = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)

    agent_name = Column(String(100), nullable=False)
    action_name = Column(String(100), nullable=False)
    tool_called = Column(String(100), nullable=True)

    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    action_type = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)

    permission_checked = Column(String(100), nullable=True)
    access_granted = Column(Boolean, nullable=False, default=False)

    details = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())