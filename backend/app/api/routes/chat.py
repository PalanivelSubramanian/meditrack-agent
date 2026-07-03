from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.agents.patient_agent import PatientAgent
from app.agents.scheduling_agent import SchedulingAgent
from app.agents.doctor_availability_agent import DoctorAvailabilityAgent
from app.agents.patient_history_agent import PatientHistoryAgent
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.auth import User
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatUIResponse
from app.agents.access_control_agent import AccessControlAgent
from app.services.auth_service import get_user_permissions
from app.services.chat_service import get_or_create_chat_session, save_chat_message
from app.services.intent_service import detect_intent
from app.services.audit_service import log_audit_event
from app.models.chat import ChatSession

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

    intent_result = detect_intent(payload.message)
    intent = intent_result.intent

    access_agent = AccessControlAgent()
    access_decision = access_agent.evaluate(
        intent=intent,
        user=user,
        permissions=permissions,
    )

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

    if access_decision.status == "auth_required":
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

        log_audit_event(
            db=db,
            action_type="AUTH_REQUIRED",
            user_id=None,
            entity_type="chat",
            entity_id=chat_session.id,
            permission_checked=access_decision.required_permission,
            access_granted=False,
            details=f"Unauthenticated request blocked for intent={intent}",
        )

        return ChatMessageResponse(
            session_id=chat_session.id,
            message=assistant_message,
            intent=intent,
            requires_auth=True,
            ui=ChatUIResponse(
                type="auth_required",
                data={
                    "required_permission": access_decision.required_permission,
                    "auth_method": "employee_id_totp",
                    "intent_entities": intent_result.entities,
                },
            ),
        )

    if access_decision.status == "access_denied":
        assistant_message = access_decision.message

        save_chat_message(
            db=db,
            session_id=chat_session.id,
            sender="assistant",
            message=assistant_message,
            intent=intent,
        )

        log_audit_event(
            db=db,
            action_type="ACCESS_DENIED",
            user_id=user.id if user else None,
            entity_type="chat",
            entity_id=chat_session.id,
            permission_checked=access_decision.required_permission,
            access_granted=False,
            details=f"Access denied for intent={intent}",
        )
        
        return ChatMessageResponse(
            session_id=chat_session.id,
            message=assistant_message,
            intent=intent,
            requires_auth=False,
            ui=ChatUIResponse(
                type="access_denied",
                data={
                    "required_permission": access_decision.required_permission,
                },
            ),
        )

    if access_decision.status == "access_granted":
        if intent == "search_patient":
            patient_query = intent_result.entities.get("patient_query")

            if not patient_query:
                assistant_message = (
                    "Please provide a patient name, phone number, date of birth, "
                    "or patient number to search."
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
                        type="missing_patient_query",
                        data={
                            "required_permission": access_decision.required_permission,
                        },
                    ),
                )

            patient_agent = PatientAgent()
            patient_result = patient_agent.search_patient(db, patient_query)

            log_audit_event(
                db=db,
                action_type="PATIENT_SEARCH",
                user_id=user.id if user else None,
                entity_type="patient",
                entity_id=None,
                permission_checked=access_decision.required_permission,
                access_granted=True,
                details=(
                    f"Patient search query='{patient_query}', "
                    f"result_type={patient_result.ui_type}"
                ),
            )

            save_chat_message(
                db=db,
                session_id=chat_session.id,
                sender="assistant",
                message=patient_result.message,
                intent=intent,
            )

            return ChatMessageResponse(
                session_id=chat_session.id,
                message=patient_result.message,
                intent=intent,
                requires_auth=False,
                ui=ChatUIResponse(
                    type=patient_result.ui_type,
                    data={
                        **patient_result.ui_data,
                        "required_permission": access_decision.required_permission,
                        "user_role": user.role.role_name if user else None,
                    },
                ),
            )

        if intent == "view_patient_history":
            patient_query = intent_result.entities.get("patient_query", "")

            patient_history_agent = PatientHistoryAgent()
            history_result = patient_history_agent.get_history_for_query(
                db=db,
                patient_query=patient_query,
            )

            patient_entity_id = None

            if history_result["ui_type"] == "patient_history":
                patient_entity_id = history_result["ui_data"]["patient"]["patient_id"]

            log_audit_event(
                db=db,
                action_type="PATIENT_HISTORY_VIEW",
                user_id=user.id if user else None,
                entity_type="patient",
                entity_id=patient_entity_id,
                permission_checked=access_decision.required_permission,
                access_granted=history_result["ui_type"] == "patient_history",
                details=(
                    f"Patient history workflow result={history_result['ui_type']}, "
                    f"patient_query='{patient_query}'"
                ),
            )

            save_chat_message(
                db=db,
                session_id=chat_session.id,
                sender="assistant",
                message=history_result["message"],
                intent=intent,
            )

            return ChatMessageResponse(
                session_id=chat_session.id,
                message=history_result["message"],
                intent=intent,
                intent_entities=intent_result.entities,
                ui={
                    "type": history_result["ui_type"],
                    "data": history_result["ui_data"],
                },
            )

        if intent == "book_appointment":
            scheduling_agent = SchedulingAgent()
            scheduling_result = scheduling_agent.book_from_entities(
                db=db,
                entities=intent_result.entities,
                created_by=user.id if user else None,
            )

            log_audit_event(
                db=db,
                action_type="BOOK_APPOINTMENT",
                user_id=user.id if user else None,
                entity_type="appointment",
                entity_id=scheduling_result.ui_data.get("appointment_id"),
                permission_checked=access_decision.required_permission,
                access_granted=scheduling_result.ui_type == "booking_confirmed",
                details=(
                    f"Booking workflow result={scheduling_result.ui_type}, "
                    f"entities={intent_result.entities}"
                ),
            )

            save_chat_message(
                db=db,
                session_id=chat_session.id,
                sender="assistant",
                message=scheduling_result.message,
                intent=intent,
            )

            return ChatMessageResponse(
                session_id=chat_session.id,
                message=scheduling_result.message,
                intent=intent,
                requires_auth=False,
                ui=ChatUIResponse(
                    type=scheduling_result.ui_type,
                    data={
                        **scheduling_result.ui_data,
                        "required_permission": access_decision.required_permission,
                        "user_role": user.role.role_name if user else None,
                    },
                ),
            )
        
        if intent == "check_doctor_availability":
            specialization = intent_result.entities.get("specialization")
            date_text = intent_result.entities.get("date_text")

            if not specialization or not date_text:
                assistant_message = (
                    "Please provide a specialization and date. "
                    "Example: Check cardiology availability tomorrow."
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
                        type="availability_missing_details",
                        data={
                            "intent_entities": intent_result.entities,
                            "required_permission": access_decision.required_permission,
                            "user_role": user.role.role_name if user else None,
                        },
                    ),
                )

            if date_text == "tomorrow":
                target_date = date.today() + timedelta(days=1)
            else:
                assistant_message = "For now, I can check availability for tomorrow only."

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
                        type="availability_unsupported_date",
                        data={
                            "date_text": date_text,
                            "required_permission": access_decision.required_permission,
                            "user_role": user.role.role_name if user else None,
                        },
                    ),
                )

            availability_agent = DoctorAvailabilityAgent()
            availability_result = availability_agent.find_slots(
                db=db,
                specialization=specialization,
                target_date=target_date,
            )

            log_audit_event(
                db=db,
                action_type="CHECK_DOCTOR_AVAILABILITY",
                user_id=user.id if user else None,
                entity_type="doctor_availability",
                entity_id=None,
                permission_checked=access_decision.required_permission,
                access_granted=True,
                details=(
                    f"Availability lookup specialization={specialization}, "
                    f"target_date={target_date.isoformat()}, "
                    f"result_type={availability_result.ui_type}"
                ),
            )

            save_chat_message(
                db=db,
                session_id=chat_session.id,
                sender="assistant",
                message=availability_result.message,
                intent=intent,
            )

            return ChatMessageResponse(
                session_id=chat_session.id,
                message=availability_result.message,
                intent=intent,
                requires_auth=False,
                ui=ChatUIResponse(
                    type=availability_result.ui_type,
                    data={
                        **availability_result.ui_data,
                        "required_permission": access_decision.required_permission,
                        "user_role": user.role.role_name if user else None,
                    },
                ),
            )

        assistant_message = "Access granted, but no workflow is implemented for this intent yet."

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
                type="workflow_not_implemented",
                data={
                    "required_permission": access_decision.required_permission,
                    "user_role": user.role.role_name if user else None,
                    "intent_entities": intent_result.entities,
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