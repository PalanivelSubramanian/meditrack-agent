from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.tools.patient_tools import search_patient_tool
from app.tools.scheduling_tools import (
    book_appointment_tool,
    find_available_slots_tool,
)


@dataclass
class SchedulingAgentResult:
    message: str
    ui_type: str
    ui_data: dict[str, Any]


class SchedulingAgent:
    """
    Handles appointment booking workflow.
    Initial version supports exact slot booking.
    """

    def _parse_date_text(self, date_text: str) -> date | None:
        if date_text.lower().strip() == "tomorrow":
            return date.today() + timedelta(days=1)
        return None

    def _parse_start_time(self, time_text: str):
        try:
            return datetime.strptime(time_text, "%H:%M").time()
        except ValueError:
            return None

    def book_from_entities(
        self,
        db: Session,
        entities: dict[str, Any],
        created_by: int | None,
    ) -> SchedulingAgentResult:
        patient_query = entities.get("patient_query")
        specialization = entities.get("specialization")
        date_text = entities.get("date_text")
        time_text = entities.get("time")

        if not patient_query or not specialization or not date_text or not time_text:
            return SchedulingAgentResult(
                message=(
                    "I need patient name, specialization, date, and time to book an appointment. "
                    "Example: Book appointment for Aisha Rahman with cardiology tomorrow at 09:00"
                ),
                ui_type="booking_missing_details",
                ui_data={"entities": entities},
            )

        appointment_date = self._parse_date_text(date_text)
        start_time = self._parse_start_time(time_text)

        if not appointment_date or not start_time:
            return SchedulingAgentResult(
                message="I could not understand the appointment date or time.",
                ui_type="booking_invalid_datetime",
                ui_data={"entities": entities},
            )

        patient_result = search_patient_tool(db, patient_query)

        if patient_result.count == 0:
            return SchedulingAgentResult(
                message="No matching patient was found for this booking request.",
                ui_type="booking_patient_no_match",
                ui_data={"patient_query": patient_query},
            )

        if patient_result.count > 1:
            return SchedulingAgentResult(
                message="I found multiple matching patients. Please confirm which patient before booking.",
                ui_type="booking_patient_matches",
                ui_data={
                    "patient_query": patient_query,
                    "patients": [p.model_dump() for p in patient_result.patients],
                    "booking_entities": entities,
                },
            )

        patient = patient_result.patients[0]

        available_slots = find_available_slots_tool(
            db=db,
            specialization=specialization,
            target_date=appointment_date,
            limit=50,
        )

        matching_slot = None
        for slot in available_slots.slots:
            if slot.start_time == start_time.strftime("%H:%M"):
                matching_slot = slot
                break

        if not matching_slot:
            return SchedulingAgentResult(
                message=(
                    f"No available {specialization} slot was found at "
                    f"{start_time.strftime('%H:%M')} on {appointment_date.isoformat()}."
                ),
                ui_type="booking_slot_unavailable",
                ui_data={
                    "specialization": specialization,
                    "target_date": appointment_date.isoformat(),
                    "requested_time": start_time.strftime("%H:%M"),
                    "available_slots": [s.model_dump() for s in available_slots.slots[:10]],
                },
            )

        end_time = datetime.strptime(matching_slot.end_time, "%H:%M").time()

        booking = book_appointment_tool(
            db=db,
            patient_id=patient.patient_id,
            doctor_id=matching_slot.doctor_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            reason=f"{specialization} appointment",
            created_by=created_by,
        )

        if not booking.success:
            return SchedulingAgentResult(
                message=booking.message,
                ui_type="booking_conflict",
                ui_data={
                    "conflict_reason": booking.conflict_reason,
                    "patient": patient.model_dump(),
                    "slot": matching_slot.model_dump(),
                },
            )

        return SchedulingAgentResult(
            message=(
                f"Appointment booked successfully for {patient.full_name} "
                f"with {matching_slot.doctor_name} on {appointment_date.isoformat()} "
                f"at {matching_slot.start_time}."
            ),
            ui_type="booking_confirmed",
            ui_data={
                "appointment_id": booking.appointment_id,
                "patient": patient.model_dump(),
                "slot": matching_slot.model_dump(),
            },
        )