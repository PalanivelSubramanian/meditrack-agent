from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.auth import User
from app.schemas.auth import (
    AuthStartRequest,
    AuthStartResponse,
    CurrentUserResponse,
    VerifyTotpRequest,
    VerifyTotpResponse,
)
from app.services.auth_service import (
    create_user_session,
    get_user_by_employee_id,
    verify_totp_for_user,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/start", response_model=AuthStartResponse)
def start_auth(payload: AuthStartRequest, db: Session = Depends(get_db)):
    user = get_user_by_employee_id(db, payload.employee_id)

    # Do not reveal whether employee ID exists in production.
    # For MVP, this is okay, but later make response generic.
    if not user:
        log_audit_event(
            db=db,
            action_type="AUTH_START_FAILED",
            user_id=None,
            entity_type="user",
            entity_id=None,
            permission_checked=None,
            access_granted=False,
            details=f"Employee ID not found or inactive: {payload.employee_id}",
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee ID not found or inactive",
        )

    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not enabled for this user",
        )

    log_audit_event(
        db=db,
        action_type="AUTH_START",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        permission_checked=None,
        access_granted=True,
        details=f"Staff verification started for employee_id={user.employee_id}",
    )

    return AuthStartResponse(
        requires_totp=True,
        employee_id=user.employee_id,
        message="Employee ID found. Continue with secure authenticator verification.",
    )


@router.post("/verify-totp", response_model=VerifyTotpResponse)
def verify_totp(payload: VerifyTotpRequest, db: Session = Depends(get_db)):
    user = get_user_by_employee_id(db, payload.employee_id)

    if not user:
        log_audit_event(
            db=db,
            action_type="LOGIN_FAILED",
            user_id=None,
            entity_type="user",
            entity_id=None,
            permission_checked=None,
            access_granted=False,
            details=f"Invalid verification for employee_id={payload.employee_id}",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification",
        )

    is_valid = verify_totp_for_user(user, payload.totp_code)

    if not is_valid:
        log_audit_event(
            db=db,
            action_type="LOGIN_FAILED",
            user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            permission_checked=None,
            access_granted=False,
            details=f"Invalid TOTP verification for employee_id={user.employee_id}",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification",
        )

    access_token, permissions = create_user_session(db, user)

    log_audit_event(
        db=db,
        action_type="LOGIN_SUCCESS",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        permission_checked=None,
        access_granted=True,
        details=f"Login successful for employee_id={user.employee_id}, role={user.role.role_name}",
    )

    return VerifyTotpResponse(
        access_token=access_token,
        user_id=user.id,
        employee_id=user.employee_id,
        full_name=user.full_name,
        role=user.role.role_name,
        permissions=permissions,
    )


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current: tuple[User, list[str]] = Depends(get_current_user),
):
    user, permissions = current

    return CurrentUserResponse(
        user_id=user.id,
        employee_id=user.employee_id,
        full_name=user.full_name,
        role=user.role.role_name,
        permissions=permissions,
    )