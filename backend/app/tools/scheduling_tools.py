from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.appointment import AppointmentHistory
from app.models.appointment import Appointment
from app.models.doctor import Doctor, DoctorAvailability
from app.schemas.appointment import AvailableSlot, AvailableSlotsResult, BookAppointmentResult


APPOINTMENT_SLOT_MINUTES = 30


def _combine_date_time(slot_date: date, slot_time: time) -> datetime:
    return datetime.combine(slot_date, slot_time)


def _time_to_string(value: time) -> str:
    return value.strftime("%H:%M")


def _date_to_string(value: date) -> str:
    return value.isoformat()


def _overlaps(
    candidate_start: time,
    candidate_end: time,
    existing_start: time,
    existing_end: time,
) -> bool:
    return candidate_start < existing_end and candidate_end > existing_start


def _generate_30_minute_slots(
    available_date: date,
    start_time: time,
    end_time: time,
) -> list[tuple[time, time]]:
    slots: list[tuple[time, time]] = []

    current = _combine_date_time(available_date, start_time)
    end = _combine_date_time(available_date, end_time)

    while current + timedelta(minutes=APPOINTMENT_SLOT_MINUTES) <= end:
        slot_start = current.time()
        slot_end = (current + timedelta(minutes=APPOINTMENT_SLOT_MINUTES)).time()

        slots.append((slot_start, slot_end))
        current = current + timedelta(minutes=APPOINTMENT_SLOT_MINUTES)

    return slots


def find_available_slots_tool(
    db: Session,
    specialization: str,
    target_date: date,
    limit: int = 10,
) -> AvailableSlotsResult:
    """
    Finds available appointment slots for doctors by specialization.

    This tool only returns slots that:
    - belong to active doctors
    - match the requested specialization
    - are inside available doctor availability windows
    - do not overlap existing scheduled appointments
    """
    normalized_specialization = specialization.lower().strip()

    doctors = (
        db.query(Doctor)
        .filter(
            Doctor.specialization.ilike(f"%{normalized_specialization}%"),
            Doctor.status == "active",
        )
        .order_by(Doctor.full_name)
        .all()
    )

    results: list[AvailableSlot] = []

    for doctor in doctors:
        availability_windows = (
            db.query(DoctorAvailability)
            .filter(
                DoctorAvailability.doctor_id == doctor.id,
                DoctorAvailability.available_date == target_date,
                DoctorAvailability.status == "available",
            )
            .order_by(DoctorAvailability.start_time)
            .all()
        )

        existing_appointments = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor.id,
                Appointment.appointment_date == target_date,
                Appointment.status == "scheduled",
            )
            .all()
        )

        for window in availability_windows:
            candidate_slots = _generate_30_minute_slots(
                available_date=target_date,
                start_time=window.start_time,
                end_time=window.end_time,
            )

            for slot_start, slot_end in candidate_slots:
                has_conflict = any(
                    _overlaps(
                        candidate_start=slot_start,
                        candidate_end=slot_end,
                        existing_start=appointment.start_time,
                        existing_end=appointment.end_time,
                    )
                    for appointment in existing_appointments
                )

                if has_conflict:
                    continue

                results.append(
                    AvailableSlot(
                        doctor_id=doctor.id,
                        doctor_name=doctor.full_name,
                        specialization=doctor.specialization,
                        department=doctor.department,
                        appointment_date=_date_to_string(target_date),
                        start_time=_time_to_string(slot_start),
                        end_time=_time_to_string(slot_end),
                    )
                )

                if len(results) >= limit:
                    return AvailableSlotsResult(
                        count=len(results),
                        slots=results,
                    )

    return AvailableSlotsResult(
        count=len(results),
        slots=results,
    )

def detect_appointment_conflict_tool(
    db: Session,
    patient_id: int,
    doctor_id: int,
    appointment_date: date,
    start_time: time,
    end_time: time,
) -> tuple[bool, str | None]:
    """
    Returns conflict status and reason.
    """

    doctor_conflict = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status == "scheduled",
            Appointment.start_time < end_time,
            Appointment.end_time > start_time,
        )
        .first()
    )

    if doctor_conflict:
        return True, "Doctor already has an appointment at this time."

    patient_conflict = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status == "scheduled",
            Appointment.start_time < end_time,
            Appointment.end_time > start_time,
        )
        .first()
    )

    if patient_conflict:
        return True, "Patient already has an appointment at this time."

    availability = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.available_date == appointment_date,
            DoctorAvailability.status == "available",
            DoctorAvailability.start_time <= start_time,
            DoctorAvailability.end_time >= end_time,
        )
        .first()
    )

    if not availability:
        return True, "Doctor is not available at this time."

    return False, None


def book_appointment_tool(
    db: Session,
    patient_id: int,
    doctor_id: int,
    appointment_date: date,
    start_time: time,
    end_time: time,
    reason: str | None,
    created_by: int | None,
) -> BookAppointmentResult:
    has_conflict, conflict_reason = detect_appointment_conflict_tool(
        db=db,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        start_time=start_time,
        end_time=end_time,
    )

    if has_conflict:
        return BookAppointmentResult(
            success=False,
            message="Appointment could not be booked because of a scheduling conflict.",
            conflict_reason=conflict_reason,
        )

    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
        status="scheduled",
        created_by=created_by,
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    history = AppointmentHistory(
        appointment_id=appointment.id,
        action="created",
        old_value=None,
        new_value=(
            f"Appointment booked for {appointment_date.isoformat()} "
            f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
        ),
        changed_by=created_by,
    )

    db.add(history)
    db.commit()

    return BookAppointmentResult(
        success=True,
        message="Appointment booked successfully.",
        appointment_id=appointment.id,
    )