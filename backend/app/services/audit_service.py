from sqlalchemy.orm import Session

from app.models.chat import AuditLog


def log_audit_event(
    db: Session,
    action_type: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    permission_checked: str | None = None,
    access_granted: bool = False,
    details: str | None = None,
) -> AuditLog:
    """
    Writes a security/audit event.

    Important:
    - Do not store sensitive medical details here.
    - Do not store OTP/TOTP codes here.
    - Do not store full patient history here.
    """
    audit_log = AuditLog(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        permission_checked=permission_checked,
        access_granted=access_granted,
        details=details,
    )

    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    return audit_log