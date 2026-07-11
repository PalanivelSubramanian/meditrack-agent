"""
Appointment-booking conversation as a LangGraph state machine.

One HTTP turn = one graph invocation: chat.py builds a BookingState from the
current message plus whatever was persisted in ChatSession.workflow_state,
invokes the graph, and persists state["workflow_state"] back unchanged
between turns. route_booking() is the single place that decides which node
handles a given turn, replacing the four separate step-tracking blocks that
used to live inline in chat.py.
"""

import re
from datetime import date, datetime
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.access_control_agent import AccessControlAgent
from app.agents.patient_agent import PatientAgent
from app.agents.scheduling_agent import SchedulingAgent
from app.agents.doctor_availability_agent import DoctorAvailabilityAgent
from app.models.auth import User
from app.services.appointment_reason_service import suggest_specialization_for_reason
from app.services.audit_service import log_audit_event
from app.services.intent_service import resolve_target_date
from app.tools.patient_registration_tools import register_patient_tool
from app.tools.scheduling_tools import book_appointment_tool, detect_appointment_conflict_tool


class BookingState(TypedDict, total=False):
    db: Session
    session_id: int
    user: User | None
    user_id: int | None
    permissions: list[str]

    intent: str
    message: str
    entry_entities: dict[str, Any]

    workflow_state: dict[str, Any] | None

    result: dict[str, Any]
    node_trace: list[str]

    _route: str


BOOKING_REASON_EXAMPLES = [
    "chest pain",
    "fever",
    "diabetes follow-up",
    "skin rash",
    "eye pain",
    "routine check-up",
]


def _append_trace(state: BookingState, node_name: str) -> None:
    state.setdefault("node_trace", []).append(node_name)


def _workflow(state: BookingState) -> dict[str, Any]:
    return state.get("workflow_state") or {}


def _set_workflow(state: BookingState, **updates: Any) -> dict[str, Any]:
    updated = {**_workflow(state), "workflow": "appointment_booking", **updates}
    state["workflow_state"] = updated
    return updated


def _clear_workflow(state: BookingState) -> None:
    state["workflow_state"] = None


def _lookup_response(patient_result) -> dict[str, Any]:
    ui_type = {
        "patient_no_match": "booking_patient_not_found",
        "patient_matches": "booking_patient_matches",
    }.get(patient_result.ui_type, "booking_patient_resolved")

    return {
        "ui_type": ui_type,
        "message": patient_result.message,
        "ui_data": {**patient_result.ui_data, "booking_context": True},
    }


def _reason_needed_response(patient_query: str | None, known_entities: dict) -> dict[str, Any]:
    return {
        "ui_type": "booking_reason_needed",
        "message": (
            f"I can help book an appointment for {patient_query}. "
            "What is the reason for the appointment?"
            if patient_query
            else "What is the reason for the appointment?"
        ),
        "ui_data": {
            "patient_query": patient_query,
            "known_entities": known_entities,
            "required_permission": "book_appointment",
            "next_step": "collect_appointment_reason",
            "examples": BOOKING_REASON_EXAMPLES,
        },
    }


# --- Nodes -------------------------------------------------------------


def check_access_node(state: BookingState) -> BookingState:
    """
    Re-checked on every turn (not just the turn that starts booking) so a
    mid-conversation workflow_state can't be advanced by a caller who never
    passed the book_appointment permission check.
    """
    _append_trace(state, "check_access")

    decision = AccessControlAgent().evaluate(
        intent="book_appointment",
        user=state.get("user"),
        permissions=state.get("permissions") or [],
    )

    if decision.status != "access_granted":
        log_audit_event(
            db=state["db"],
            action_type="AUTH_REQUIRED" if decision.status == "auth_required" else "ACCESS_DENIED",
            user_id=state.get("user_id"),
            entity_type="chat",
            entity_id=state.get("session_id"),
            permission_checked=decision.required_permission,
            access_granted=False,
            details=f"Booking workflow continuation blocked: {decision.status}",
        )
        state["result"] = {
            "ui_type": decision.status,
            "message": decision.message,
            "ui_data": {"required_permission": decision.required_permission},
        }

    return state


def resolve_patient_node(state: BookingState) -> BookingState:
    _append_trace(state, "resolve_patient")

    entities = state.get("entry_entities") or {}
    patient_query = (
        entities.get("patient_query")
        or entities.get("patient_name")
        or entities.get("patient")
    )

    if not patient_query:
        # No patient named yet at all -> same fallback as a fully-specified
        # message: let SchedulingAgent explain what's missing.
        state["_route"] = "book_from_message"
        return state

    patient_result = PatientAgent().search_patient(state["db"], patient_query)

    log_audit_event(
        db=state["db"],
        action_type="BOOK_APPOINTMENT_PATIENT_LOOKUP",
        user_id=state.get("user_id"),
        entity_type="patient",
        entity_id=None,
        permission_checked="book_appointment",
        access_granted=True,
        details=f"Booking patient lookup query='{patient_query}', result_type={patient_result.ui_type}",
    )

    if patient_result.ui_type in ("patient_no_match", "patient_matches"):
        _set_workflow(
            state,
            step="await_registration" if patient_result.ui_type == "patient_no_match" else "select_patient",
            patient_query=patient_query,
            entities=entities,
        )

        log_audit_event(
            db=state["db"],
            action_type=(
                "BOOK_APPOINTMENT_PATIENT_NOT_FOUND"
                if patient_result.ui_type == "patient_no_match"
                else "BOOK_APPOINTMENT_PATIENT_AMBIGUOUS"
            ),
            user_id=state.get("user_id"),
            entity_type="patient",
            entity_id=None,
            permission_checked="book_appointment",
            access_granted=False,
            details=f"Booking patient resolution result={patient_result.ui_type}, patient_query='{patient_query}'",
        )

        state["result"] = _lookup_response(patient_result)
        return state

    resolved_patient = patient_result.ui_data["selected_patient"]
    specialization = entities.get("specialization")
    appointment_reason = (
        entities.get("reason")
        or entities.get("appointment_reason")
        or entities.get("symptom")
        or entities.get("problem")
    )

    if specialization or appointment_reason:
        # Patient resolved but the rest of the booking came in the same
        # message (e.g. specialization given without a full date/time) --
        # same fallthrough SchedulingAgent handles today.
        state["_route"] = "book_from_message"
        return state

    _set_workflow(
        state,
        step="collect_reason",
        patient_id=resolved_patient["patient_id"],
        patient_query=patient_query,
        patient=resolved_patient,
        entities=entities,
    )

    log_audit_event(
        db=state["db"],
        action_type="BOOK_APPOINTMENT_REASON_NEEDED",
        user_id=state.get("user_id"),
        entity_type="appointment",
        entity_id=None,
        permission_checked="book_appointment",
        access_granted=True,
        details=(
            "Appointment booking paused to collect reason after patient resolution. "
            f"patient_query='{patient_query}', patient_id={resolved_patient['patient_id']}"
        ),
    )

    state["result"] = _reason_needed_response(patient_query, entities)
    state["result"]["ui_data"]["patient"] = resolved_patient
    return state


def select_patient_node(state: BookingState) -> BookingState:
    """Handles the 'select P123' reply to an ambiguous patient match."""
    _append_trace(state, "select_patient")

    workflow = _workflow(state)
    patient_query = state["entry_entities"].get("patient_query")
    patient_result = PatientAgent().search_patient(state["db"], patient_query)

    if patient_result.ui_type == "patient_single_match":
        resolved_patient = patient_result.ui_data["selected_patient"]

        _set_workflow(
            state,
            step="collect_reason",
            patient_id=resolved_patient["patient_id"],
            patient=resolved_patient,
        )

        log_audit_event(
            db=state["db"],
            action_type="BOOK_APPOINTMENT_REASON_NEEDED",
            user_id=state.get("user_id"),
            entity_type="appointment",
            entity_id=None,
            permission_checked="book_appointment",
            access_granted=True,
            details=(
                "Patient selected for booking from ambiguous match. "
                f"patient_id={resolved_patient['patient_id']}, patient_query='{patient_query}'"
            ),
        )

        assistant_message = f"Selected {resolved_patient['full_name']}. What is the reason for the appointment?"
        state["result"] = {
            "ui_type": "booking_reason_needed",
            "message": assistant_message,
            "ui_data": {
                "patient_query": workflow.get("patient_query"),
                "patient": resolved_patient,
                "known_entities": workflow.get("entities", {}),
                "required_permission": "book_appointment",
                "next_step": "collect_appointment_reason",
                "examples": BOOKING_REASON_EXAMPLES,
            },
        }
        return state

    _set_workflow(
        state,
        step="await_registration" if patient_result.ui_type == "patient_no_match" else "select_patient",
    )

    log_audit_event(
        db=state["db"],
        action_type=(
            "BOOK_APPOINTMENT_PATIENT_NOT_FOUND"
            if patient_result.ui_type == "patient_no_match"
            else "BOOK_APPOINTMENT_PATIENT_AMBIGUOUS"
        ),
        user_id=state.get("user_id"),
        entity_type="patient",
        entity_id=None,
        permission_checked="book_appointment",
        access_granted=False,
        details=f"Booking patient re-selection query='{patient_query}', result_type={patient_result.ui_type}",
    )

    state["result"] = _lookup_response(patient_result)
    return state


def apply_registration_node(state: BookingState) -> BookingState:
    """
    Registers the patient and, on success, resumes the booking workflow at
    the reason-collection step -- this is what closes the gap where
    registering mid-booking used to dead-end.
    """
    _append_trace(state, "apply_registration")

    payload = state.get("entry_entities") or {}
    registration_result = register_patient_tool(db=state["db"], payload=payload)

    log_audit_event(
        db=state["db"],
        action_type="PATIENT_REGISTRATION",
        user_id=state.get("user_id"),
        entity_type="patient",
        entity_id=(registration_result["patient"]["patient_id"] if registration_result["status"] in ("created", "duplicate_possible") else None),
        permission_checked="book_appointment",
        access_granted=registration_result["status"] == "created",
        details=f"Patient registration during booking result={registration_result['status']}",
    )

    if registration_result["status"] not in ("created", "duplicate_possible"):
        state["result"] = {
            "ui_type": "patient_registration_missing_fields"
            if registration_result["status"] == "missing_fields"
            else "patient_registration_invalid",
            "message": registration_result.get(
                "message",
                "Patient registration details are invalid.",
            ),
            "ui_data": {"status": registration_result["status"]},
        }
        return state

    resolved_patient = registration_result["patient"]

    _set_workflow(
        state,
        step="collect_reason",
        patient_id=resolved_patient["patient_id"],
        patient_query=resolved_patient["full_name"],
        patient=resolved_patient,
    )

    assistant_message = (
        f"{registration_result['message']} What is the reason for the appointment?"
    )
    state["result"] = {
        "ui_type": "booking_reason_needed",
        "message": assistant_message,
        "ui_data": {
            "patient_query": resolved_patient["full_name"],
            "patient": resolved_patient,
            "known_entities": {},
            "required_permission": "book_appointment",
            "next_step": "collect_appointment_reason",
            "examples": BOOKING_REASON_EXAMPLES,
        },
    }
    return state


def suggest_specialization_node(state: BookingState) -> BookingState:
    _append_trace(state, "suggest_specialization")

    appointment_reason = state["message"].strip()
    reason_result = suggest_specialization_for_reason(appointment_reason)

    workflow = _set_workflow(
        state,
        step="confirm_specialization",
        appointment_reason=appointment_reason,
        suggested_specialization=reason_result["suggested_specialization"],
        reason_result=reason_result,
    )

    log_audit_event(
        db=state["db"],
        action_type="APPOINTMENT_REASON_CAPTURED",
        user_id=state.get("user_id"),
        entity_type="appointment",
        entity_id=None,
        permission_checked="book_appointment",
        access_granted=True,
        details=(
            f"Appointment reason captured. patient_query='{workflow.get('patient_query')}', "
            f"reason='{appointment_reason}', suggested_specialization='{reason_result['suggested_specialization']}', "
            f"urgency='{reason_result['urgency']}'"
        ),
    )

    specialization_label = reason_result["suggested_specialization"].replace("_", " ")
    state["result"] = {
        "ui_type": "booking_specialization_suggested",
        "message": (
            f"Based on the appointment reason, {specialization_label} may be appropriate. "
            "Do you want to check availability?"
        ),
        "ui_data": {
            "patient_query": workflow.get("patient_query"),
            "appointment_reason": reason_result["reason"],
            "suggested_specialization": reason_result["suggested_specialization"],
            "suggested_specialization_label": specialization_label.title(),
            "confidence": reason_result["confidence"],
            "urgency": reason_result["urgency"],
            "red_flags": reason_result["red_flags"],
            "patient_message": reason_result["patient_message"],
            "next_step": "confirm_specialization",
        },
    }
    return state


def check_availability_node(state: BookingState) -> BookingState:
    _append_trace(state, "check_availability")

    workflow = _workflow(state)
    entities = state.get("entry_entities") or {}
    specialization = entities.get("specialization") or workflow.get("suggested_specialization")
    date_text = entities.get("date_text") or "tomorrow"

    target_date = resolve_target_date(date_text)

    if target_date is None:
        state["result"] = {
            "ui_type": "availability_unsupported_date",
            "message": (
                "I couldn't understand that date. Try 'today', 'tomorrow', "
                "or a date like 2026-07-20."
            ),
            "ui_data": {"date_text": date_text},
        }
        return state

    availability_result = DoctorAvailabilityAgent().find_slots(
        db=state["db"],
        specialization=specialization,
        target_date=target_date,
    )

    has_slots = availability_result.ui_type == "availability_slots"

    _set_workflow(
        state,
        # Stay on confirm_specialization when nothing came back so the next
        # message (e.g. a retry with another specialization or date) is
        # treated as a fresh availability check instead of being
        # misinterpreted as a slot selection by select_slot_node.
        step="select_slot" if has_slots else "confirm_specialization",
        available_slots=availability_result.ui_data.get("slots", []),
        availability_specialization=specialization,
        availability_date_text=date_text,
        availability_result_type=availability_result.ui_type,
    )

    log_audit_event(
        db=state["db"],
        action_type="CHECK_DOCTOR_AVAILABILITY",
        user_id=state.get("user_id"),
        entity_type="doctor_availability",
        entity_id=None,
        permission_checked="book_appointment",
        access_granted=True,
        details=(
            f"Availability lookup specialization={specialization}, "
            f"target_date={target_date.isoformat()}, result_type={availability_result.ui_type}"
        ),
    )

    state["result"] = {
        "ui_type": availability_result.ui_type,
        "message": availability_result.message,
        "ui_data": {
            **availability_result.ui_data,
            "booking_workflow_state": state["workflow_state"],
        },
    }
    return state


def select_slot_node(state: BookingState) -> BookingState:
    """
    Reads a slot choice out of free text and, once resolved, hands off to
    book_node -- this closes the previous dead end where reaching
    step='select_slot' had no code path that ever booked.

    The reply isn't always a bare "09:00" or "1" -- the frontend's "Book
    this slot" button sends a full composed sentence (e.g. "Book
    appointment for John Smith with cardiology tomorrow at 09:00"), so this
    searches for a time or index anywhere in the message rather than
    requiring an exact match.
    """
    _append_trace(state, "select_slot")

    workflow = _workflow(state)
    available_slots = workflow.get("available_slots") or []
    reply = state["message"].strip().lower()

    time_match = re.search(r"\d{1,2}:\d{2}", reply)
    requested_time = time_match.group(0) if time_match else None

    selected_slot = None
    for index, slot in enumerate(available_slots, start=1):
        if slot["start_time"] == requested_time or reply in (str(index), f"slot {index}"):
            selected_slot = slot
            break

    if selected_slot is None:
        state["result"] = {
            "ui_type": "booking_slot_selection_needed",
            "message": "Please choose one of the available slots by time (e.g. '09:00') or number (e.g. '1').",
            "ui_data": {
                "available_slots": available_slots,
                "booking_workflow_state": state["workflow_state"],
            },
        }
        return state

    _set_workflow(state, selected_slot=selected_slot)
    return book_node(state)


def book_from_message_node(state: BookingState) -> BookingState:
    """Fully-specified single-message booking, e.g. 'Book appointment for
    Aisha Rahman with cardiology tomorrow at 09:00' -- unchanged from the
    original SchedulingAgent-based flow."""
    _append_trace(state, "book_from_message")

    workflow_before_clear = state.get("workflow_state")
    scheduling_result = SchedulingAgent().book_from_entities(
        db=state["db"],
        entities=state.get("entry_entities") or {},
        created_by=state.get("user_id"),
    )

    if scheduling_result.ui_type == "booking_confirmed":
        _clear_workflow(state)

    log_audit_event(
        db=state["db"],
        action_type="BOOK_APPOINTMENT",
        user_id=state.get("user_id"),
        entity_type="appointment",
        entity_id=scheduling_result.ui_data.get("appointment_id"),
        permission_checked="book_appointment",
        access_granted=scheduling_result.ui_type == "booking_confirmed",
        details=(
            f"Booking workflow result={scheduling_result.ui_type}, "
            f"workflow_state_before_clear={workflow_before_clear}"
        ),
    )

    state["result"] = {
        "ui_type": scheduling_result.ui_type,
        "message": scheduling_result.message,
        "ui_data": {
            **scheduling_result.ui_data,
            "booking_workflow_state_before_clear": workflow_before_clear,
            "booking_workflow_cleared": scheduling_result.ui_type == "booking_confirmed",
        },
    }
    return state


def book_node(state: BookingState) -> BookingState:
    """Books using patient/slot/reason accumulated across turns -- this is
    the path that actually consumes the multi-turn workflow_state, unlike
    the old book_appointment branch which only ever read the latest
    message's entities."""
    _append_trace(state, "book")

    workflow = _workflow(state)
    slot = workflow["selected_slot"]

    has_conflict, conflict_reason = detect_appointment_conflict_tool(
        db=state["db"],
        patient_id=workflow["patient_id"],
        doctor_id=slot["doctor_id"],
        appointment_date=date.fromisoformat(slot["appointment_date"]),
        start_time=_parse_hhmm(slot["start_time"]),
        end_time=_parse_hhmm(slot["end_time"]),
    )

    if has_conflict:
        state["result"] = {
            "ui_type": "booking_conflict",
            "message": "Appointment could not be booked because of a scheduling conflict.",
            "ui_data": {"conflict_reason": conflict_reason, "patient": workflow.get("patient"), "slot": slot},
        }
        log_audit_event(
            db=state["db"],
            action_type="BOOK_APPOINTMENT",
            user_id=state.get("user_id"),
            entity_type="appointment",
            entity_id=None,
            permission_checked="book_appointment",
            access_granted=False,
            details=f"Booking conflict: {conflict_reason}",
        )
        return state

    booking = book_appointment_tool(
        db=state["db"],
        patient_id=workflow["patient_id"],
        doctor_id=slot["doctor_id"],
        appointment_date=date.fromisoformat(slot["appointment_date"]),
        start_time=_parse_hhmm(slot["start_time"]),
        end_time=_parse_hhmm(slot["end_time"]),
        reason=workflow.get("appointment_reason"),
        created_by=state.get("user_id"),
    )

    workflow_before_clear = state.get("workflow_state")
    _clear_workflow(state)

    log_audit_event(
        db=state["db"],
        action_type="BOOK_APPOINTMENT",
        user_id=state.get("user_id"),
        entity_type="appointment",
        entity_id=booking.appointment_id,
        permission_checked="book_appointment",
        access_granted=True,
        details=f"Booking workflow result=booking_confirmed, workflow_state_before_clear={workflow_before_clear}",
    )

    state["result"] = {
        "ui_type": "booking_confirmed",
        "message": (
            f"Appointment booked successfully for {workflow['patient']['full_name']} "
            f"with {slot['doctor_name']} on {slot['appointment_date']} at {slot['start_time']}."
        ),
        "ui_data": {
            "appointment_id": booking.appointment_id,
            "patient": workflow.get("patient"),
            "slot": slot,
            "booking_workflow_state_before_clear": workflow_before_clear,
            "booking_workflow_cleared": True,
        },
    }
    return state


def _parse_hhmm(value: str):
    return datetime.strptime(value, "%H:%M").time()


# --- Routing -------------------------------------------------------------


def route_booking(state: BookingState) -> str:
    if state.get("result") is not None:
        return "end"

    if state.get("_route") == "book_from_message":
        return "book_from_message"

    intent = state.get("intent")

    if intent == "book_appointment":
        entities = state.get("entry_entities") or {}
        if all(entities.get(key) for key in ("patient_query", "specialization", "date_text", "time")):
            return "book_from_message"
        return "resolve_patient"

    return {
        "collect_reason_reply": "suggest_specialization",
        "select_patient_reply": "select_patient",
        "register_patient_resume": "apply_registration",
        "check_availability_reply": "check_availability",
        "select_slot_reply": "select_slot",
    }.get(intent, "unsupported")


def unsupported_node(state: BookingState) -> BookingState:
    state["result"] = {
        "ui_type": "workflow_not_implemented",
        "message": "Access granted, but no workflow is implemented for this step yet.",
        "ui_data": {},
    }
    return state


def build_appointment_booking_graph():
    graph = StateGraph(BookingState)

    graph.add_node("check_access", check_access_node)
    graph.add_node("resolve_patient", resolve_patient_node)
    graph.add_node("select_patient", select_patient_node)
    graph.add_node("apply_registration", apply_registration_node)
    graph.add_node("suggest_specialization", suggest_specialization_node)
    graph.add_node("check_availability", check_availability_node)
    graph.add_node("select_slot", select_slot_node)
    graph.add_node("book_from_message", book_from_message_node)
    graph.add_node("unsupported", unsupported_node)

    graph.set_entry_point("check_access")

    graph.add_conditional_edges(
        "check_access",
        route_booking,
        {
            "end": END,
            "resolve_patient": "resolve_patient",
            "select_patient": "select_patient",
            "apply_registration": "apply_registration",
            "suggest_specialization": "suggest_specialization",
            "check_availability": "check_availability",
            "select_slot": "select_slot",
            "book_from_message": "book_from_message",
            "unsupported": "unsupported",
        },
    )

    graph.add_conditional_edges(
        "resolve_patient",
        route_booking,
        {"end": END, "book_from_message": "book_from_message"},
    )

    for node_name in (
        "select_patient",
        "apply_registration",
        "suggest_specialization",
        "check_availability",
        "select_slot",
        "book_from_message",
        "unsupported",
    ):
        graph.add_edge(node_name, END)

    return graph.compile()


def run_appointment_booking_graph(db: Session, state: dict) -> dict:
    state = {**state, "db": db, "node_trace": []}
    graph = build_appointment_booking_graph()
    return graph.invoke(state)
