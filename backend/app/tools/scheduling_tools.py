from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.doctor import Doctor, DoctorAvailability
from app.schemas.appointment import AvailableSlot, AvailableSlotsResult


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