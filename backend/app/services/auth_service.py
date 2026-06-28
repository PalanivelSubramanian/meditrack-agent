from datetime import datetime, timedelta, timezone

import pyotp
from sqlalchemy.orm import Session

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.security import create_access_token, hash_token
from app.models.auth import AuthSession, Permission, RolePermission, User


def get_user_by_employee_id(db: Session, employee_id: str) -> User | None:
    return (
        db.query(User)
        .filter(User.employee_id == employee_id, User.status == "active")
        .first()
    )


def get_user_permissions(db: Session, user: User) -> list[str]:
    rows = (
        db.query(Permission.permission_name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == user.role_id)
        .all()
    )

    return [row[0] for row in rows]


def verify_totp_for_user(user: User, totp_code: str) -> bool:
    if not user.totp_enabled or not user.totp_secret_encrypted:
        return False

    totp = pyotp.TOTP(user.totp_secret_encrypted)

    # valid_window=1 allows one time-step before/after for clock drift.
    return totp.verify(totp_code, valid_window=1)


def create_user_session(db: Session, user: User) -> tuple[str, list[str]]:
    permissions = get_user_permissions(db, user)

    token = create_access_token(
        {
            "sub": str(user.id),
            "employee_id": user.employee_id,
            "role": user.role.role_name,
            "permissions": permissions,
        }
    )

    session = AuthSession(
        user_id=user.id,
        session_token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    db.add(session)
    db.commit()

    return token, permissions