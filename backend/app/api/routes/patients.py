from pydantic import BaseModel
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.auth import User
from app.services.auth_service import get_user_permissions
from app.services.audit_service import log_audit_event
from app.tools.patient_registration_tools import register_patient_tool


router = APIRouter(prefix="/patients", tags=["patients"])
bearer_scheme = HTTPBearer(auto_error=False)


class PatientRegistrationRequest(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: str


def get_current_user_and_permissions(
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


@router.post("/register")
def register_patient(
    payload: PatientRegistrationRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user, permissions = get_current_user_and_permissions(credentials, db)

    if user is None:
        return {
            "status": "auth_required",
            "message": "Authentication is required to register a patient.",
        }

    required_permission = "search_patient"

    if required_permission not in permissions:
        log_audit_event(
            db=db,
            action_type="PATIENT_REGISTRATION_DENIED",
            user_id=user.id,
            entity_type="patient",
            entity_id=None,
            permission_checked=required_permission,
            access_granted=False,
            details="User attempted patient registration without permission.",
        )

        return {
            "status": "access_denied",
            "message": "You do not have permission to register patients.",
        }

    registration_result = register_patient_tool(
        db=db,
        payload=payload.model_dump(),
    )

    patient_entity_id = None

    if registration_result["status"] in ["created", "duplicate_possible"]:
        patient_entity_id = registration_result["patient"]["patient_id"]

    log_audit_event(
        db=db,
        action_type="PATIENT_REGISTRATION",
        user_id=user.id,
        entity_type="patient",
        entity_id=patient_entity_id,
        permission_checked=required_permission,
        access_granted=registration_result["status"] == "created",
        details=(
            f"Structured patient registration result={registration_result['status']}, "
            f"first_name='{payload.first_name}', last_name='{payload.last_name}'"
        ),
    )

    return registration_result