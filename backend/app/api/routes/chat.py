from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
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
from app.tools.patient_history_tools import get_patient_history_tool
from app.tools.appointment_tools import (
    find_upcoming_patient_appointments_tool,
    cancel_appointment_tool,
)


router = APIRouter(prefix="/chat", tags=["chat"])


bearer_scheme = HTTPBearer(auto_error=False)

class ClearPatientContextRequest(BaseModel):
    session_id: int

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

def build_context_followup_response(raw_history, followup_text: str) -> dict:
    """
    Builds a section-specific UI response from selected patient history.
    """

    normalized = (followup_text or "").lower().strip()

    patient_data = raw_history.patient.model_dump()

    if any(word in normalized for word in ["medication", "medications", "meds"]):
        return {
            "ui_type": "patient_medications",
            "message": f"Retrieved current medications for {raw_history.patient.full_name}.",
            "ui_data": {
                "patient": patient_data,
                "current_medications": [
                    medication.model_dump()
                    for medication in raw_history.current_medications
                ],
            },
        }

    if any(word in normalized for word in ["visit", "visits"]):
        return {
            "ui_type": "patient_visits",
            "message": f"Retrieved recent visits for {raw_history.patient.full_name}.",
            "ui_data": {
                "patient": patient_data,
                "recent_visits": [
                    visit.model_dump()
                    for visit in raw_history.recent_visits
                ],
            },
        }

    if any(word in normalized for word in ["diagnosis", "diagnoses"]):
        return {
            "ui_type": "patient_diagnoses",
            "message": f"Retrieved active diagnoses for {raw_history.patient.full_name}.",
            "ui_data": {
                "patient": patient_data,
                "active_diagnoses": [
                    diagnosis.model_dump()
                    for diagnosis in raw_history.active_diagnoses
                ],
            },
        }

    return {
        "ui_type": "patient_history",
        "message": f"Retrieved history for {raw_history.patient.full_name}.",
        "ui_data": {
            "patient": patient_data,
            "recent_visits": [
                visit.model_dump()
                for visit in raw_history.recent_visits
            ],
            "active_diagnoses": [
                diagnosis.model_dump()
                for diagnosis in raw_history.active_diagnoses
            ],
            "current_medications": [
                medication.model_dump()
                for medication in raw_history.current_medications
            ],
            "clinical_notes": [
                note.model_dump()
                for note in raw_history.clinical_notes
            ],
        },
    }

def build_agent_trace(
    intent: str,
    access_status: str,
    required_permission: str | None = None,
    tool_used: str | None = None,
    selected_patient_id: int | None = None,
    audit_event: str | None = None,
    workflow_result: str | None = None,
) -> dict:
    return {
        "intent": intent,
        "access_status": access_status,
        "required_permission": required_permission,
        "tool_used": tool_used,
        "selected_patient_id": selected_patient_id,
        "audit_event": audit_event,
        "workflow_result": workflow_result,
    }

@router.post("/clear-patient-context")
def clear_patient_context(
    payload: ClearPatientContextRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user, permissions = get_optional_user_context(credentials, db)

    if user is None:
        return {
            "status": "auth_required",
            "message": "Authentication is required to clear patient context.",
        }

    chat_session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id)
        .first()
    )

    if chat_session is None:
        return {
            "status": "not_found",
            "message": "Chat session not found.",
        }

    previous_patient_id = chat_session.selected_patient_id

    chat_session.selected_patient_id = None
    db.add(chat_session)
    db.commit()

    log_audit_event(
        db=db,
        action_type="CLEAR_PATIENT_CONTEXT",
        user_id=user.id,
        entity_type="chat_session",
        entity_id=chat_session.id,
        permission_checked="view_patient_history",
        access_granted=True,
        details=f"Cleared selected_patient_id={previous_patient_id}",
    )

    return {
        "status": "cleared",
        "session_id": chat_session.id,
        "previous_patient_id": previous_patient_id,
    }

def build_appointment_lookup_response(appointment_result: dict) -> dict:
    if appointment_result["status"] == "not_found":
        return {
            "ui_type": "appointment_patient_not_found",
            "message": appointment_result["message"],
            "ui_data": {
                "patient": None,
                "appointments": [],
            },
        }

    if len(appointment_result["appointments"]) == 0:
        return {
            "ui_type": "no_upcoming_appointments",
            "message": appointment_result["message"],
            "ui_data": {
                "patient": appointment_result["patient"],
                "appointments": [],
            },
        }

    return {
        "ui_type": "upcoming_appointments",
        "message": appointment_result["message"],
        "ui_data": {
            "patient": appointment_result["patient"],
            "appointments": appointment_result["appointments"],
        },
    }

def build_cancel_appointment_response(cancel_result: dict) -> dict:
    if cancel_result["status"] == "not_found":
        return {
            "ui_type": "appointment_not_found",
            "message": cancel_result["message"],
            "ui_data": {
                "appointment": None,
            },
        }

    if cancel_result["status"] == "not_cancellable":
        return {
            "ui_type": "appointment_not_cancellable",
            "message": cancel_result["message"],
            "ui_data": {
                "appointment": cancel_result["appointment"],
            },
        }

    return {
        "ui_type": "appointment_cancelled",
        "message": cancel_result["message"],
        "ui_data": {
            "appointment": cancel_result["appointment"],
        },
    }

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

                chat_session.selected_patient_id = patient_entity_id
                db.add(chat_session)
                db.commit()
                db.refresh(chat_session)

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

                ui=ChatUIResponse(
                    type=history_result["ui_type"],
                    data={
                        **history_result["ui_data"],
                        "agent_trace": build_agent_trace(
                            intent=intent,
                            access_status=access_decision.status,
                            required_permission=access_decision.required_permission,
                            tool_used="PatientHistoryAgent.get_history_for_query",
                            selected_patient_id=patient_entity_id,
                            audit_event="PATIENT_HISTORY_VIEW",
                            workflow_result=history_result["ui_type"],
                        ),
                    },
                ),
            )

        if intent == "patient_context_followup":
            if not chat_session.selected_patient_id:
                assistant_message = (
                    "Please select a patient first. For example, search a patient "
                    "or open a patient history before asking follow-up questions."
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
                    intent_entities=intent_result.entities,
                    requires_auth=False,
                    ui=ChatUIResponse(
                        type="patient_context_missing",
                        data={
                            "required_permission": access_decision.required_permission,
                            "followup_text": intent_result.entities.get("followup_text"),
                            "agent_trace": build_agent_trace(
                                intent=intent,
                                access_status=access_decision.status,
                                required_permission=access_decision.required_permission,
                                tool_used=None,
                                selected_patient_id=None,
                                audit_event=None,
                                workflow_result="patient_context_missing",
                            ),
                        },
                    ),
                )

            raw_history = get_patient_history_tool(
                db=db,
                patient_id=chat_session.selected_patient_id,
            )

            if raw_history.status == "not_found":
                history_result = {
                    "ui_type": "history_patient_no_match",
                    "message": "The selected patient could not be found.",
                    "ui_data": {
                        "query": str(chat_session.selected_patient_id),
                        "matches": [],
                    },
                }
            else:
                history_result = build_context_followup_response(
                    raw_history=raw_history,
                    followup_text=intent_result.entities.get("followup_text", ""),
                )

            successful_followup_types = {
                "patient_history",
                "patient_medications",
                "patient_visits",
                "patient_diagnoses",
            }

            log_audit_event(
                db=db,
                action_type="PATIENT_CONTEXT_FOLLOWUP",
                user_id=user.id if user else None,
                entity_type="patient",
                entity_id=chat_session.selected_patient_id,
                permission_checked=access_decision.required_permission,
                access_granted=history_result["ui_type"] in successful_followup_types,
                details=(
                    f"Patient context follow-up result={history_result['ui_type']}, "
                    f"selected_patient_id={chat_session.selected_patient_id}, "
                    f"followup_text='{intent_result.entities.get('followup_text')}'"
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
                requires_auth=False,
                ui=ChatUIResponse(
                    type=history_result["ui_type"],
                    data={
                        **history_result["ui_data"],
                        "context_followup": True,
                        "followup_text": intent_result.entities.get("followup_text"),
                        "required_permission": access_decision.required_permission,
                        "agent_trace": build_agent_trace(
                            intent=intent,
                            access_status=access_decision.status,
                            required_permission=access_decision.required_permission,
                            tool_used="get_patient_history_tool",
                            selected_patient_id=chat_session.selected_patient_id,
                            audit_event="PATIENT_CONTEXT_FOLLOWUP",
                            workflow_result=history_result["ui_type"],
                        ),
                    },
                ),
            )

        if intent == "cancel_appointment":
            appointment_id = intent_result.entities.get("appointment_id")

            if not appointment_id:
                assistant_message = "Please provide an appointment ID to cancel."

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
                    intent_entities=intent_result.entities,
                    requires_auth=False,
                    ui=ChatUIResponse(
                        type="missing_appointment_id",
                        data={
                            "required_permission": access_decision.required_permission,
                            "agent_trace": build_agent_trace(
                                intent=intent,
                                access_status=access_decision.status,
                                required_permission=access_decision.required_permission,
                                tool_used=None,
                                selected_patient_id=None,
                                audit_event=None,
                                workflow_result="missing_appointment_id",
                            ),
                        },
                    ),
                )

            cancel_result = cancel_appointment_tool(
                db=db,
                appointment_id=int(appointment_id),
            )

            workflow_result = build_cancel_appointment_response(cancel_result)

            log_audit_event(
                db=db,
                action_type="CANCEL_APPOINTMENT",
                user_id=user.id if user else None,
                entity_type="appointment",
                entity_id=appointment_id,
                permission_checked=access_decision.required_permission,
                access_granted=workflow_result["ui_type"] == "appointment_cancelled",
                details=(
                    f"Cancel appointment result={workflow_result['ui_type']}, "
                    f"appointment_id={appointment_id}"
                ),
            )

            save_chat_message(
                db=db,
                session_id=chat_session.id,
                sender="assistant",
                message=workflow_result["message"],
                intent=intent,
            )

            return ChatMessageResponse(
                session_id=chat_session.id,
                message=workflow_result["message"],
                intent=intent,
                intent_entities=intent_result.entities,
                requires_auth=False,
                ui=ChatUIResponse(
                    type=workflow_result["ui_type"],
                    data={
                        **workflow_result["ui_data"],
                        "required_permission": access_decision.required_permission,
                        "agent_trace": build_agent_trace(
                            intent=intent,
                            access_status=access_decision.status,
                            required_permission=access_decision.required_permission,
                            tool_used="cancel_appointment_tool",
                            selected_patient_id=None,
                            audit_event="CANCEL_APPOINTMENT",
                            workflow_result=workflow_result["ui_type"],
                        ),
                    },
                ),
            )

        if intent == "manage_appointment":
            patient_query = intent_result.entities.get("patient_query", "")

            patient_history_agent = PatientHistoryAgent()
            patient_result = patient_history_agent.get_history_for_query(
                db=db,
                patient_query=patient_query,
            )

            patient_entity_id = None

            if patient_result["ui_type"] == "patient_history":
                patient_entity_id = patient_result["ui_data"]["patient"]["patient_id"]

                appointment_result = find_upcoming_patient_appointments_tool(
                    db=db,
                    patient_id=patient_entity_id,
                )

                workflow_result = build_appointment_lookup_response(
                    appointment_result=appointment_result,
                )
            else:
                workflow_result = {
                    "ui_type": patient_result["ui_type"],
                    "message": patient_result["message"],
                    "ui_data": patient_result["ui_data"],
                }

            log_audit_event(
                db=db,
                action_type="APPOINTMENT_LOOKUP",
                user_id=user.id if user else None,
                entity_type="patient",
                entity_id=patient_entity_id,
                permission_checked=access_decision.required_permission,
                access_granted=workflow_result["ui_type"] == "upcoming_appointments",
                details=(
                    f"Appointment lookup result={workflow_result['ui_type']}, "
                    f"patient_query='{patient_query}'"
                ),
            )

            save_chat_message(
                db=db,
                session_id=chat_session.id,
                sender="assistant",
                message=workflow_result["message"],
                intent=intent,
            )

            return ChatMessageResponse(
                session_id=chat_session.id,
                message=workflow_result["message"],
                intent=intent,
                intent_entities=intent_result.entities,
                requires_auth=False,
                ui=ChatUIResponse(
                    type=workflow_result["ui_type"],
                    data={
                        **workflow_result["ui_data"],
                        "required_permission": access_decision.required_permission,
                        "agent_trace": build_agent_trace(
                            intent=intent,
                            access_status=access_decision.status,
                            required_permission=access_decision.required_permission,
                            tool_used="find_upcoming_patient_appointments_tool",
                            selected_patient_id=patient_entity_id,
                            audit_event="APPOINTMENT_LOOKUP",
                            workflow_result=workflow_result["ui_type"],
                        ),
                    },
                ),
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