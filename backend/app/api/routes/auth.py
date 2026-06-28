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

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/start", response_model=AuthStartResponse)
def start_auth(payload: AuthStartRequest, db: Session = Depends(get_db)):
    user = get_user_by_employee_id(db, payload.employee_id)

    # Do not reveal whether employee ID exists in production.
    # For MVP, this is okay, but later make response generic.
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee ID not found or inactive",
        )

    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not enabled for this user",
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification",
        )

    is_valid = verify_totp_for_user(user, payload.totp_code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification",
        )

    access_token, permissions = create_user_session(db, user)

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