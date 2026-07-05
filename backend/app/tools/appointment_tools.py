from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.doctor import Doctor


def _patient_full_name(patient: Patient) -> str:
    return f"{patient.first_name} {patient.last_name}".strip()


def _appointment_doctor_name(doctor: Doctor | None) -> str | None:
    if doctor is None:
        return None

    return f"Dr. {doctor.first_name} {doctor.last_name}".strip()


def find_upcoming_patient_appointments_tool(
    db: Session,
    patient_id: int,
) -> dict:
    """
    Finds upcoming scheduled appointments for one patient.
    This tool assumes auth/RBAC has already been checked by the agent route.
    """

    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if patient is None:
        return {
            "status": "not_found",
            "message": "Patient not found.",
            "patient": None,
            "appointments": [],
        }

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.status == "scheduled",
            Appointment.appointment_date >= date.today(),
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc())
        .all()
    )

    appointment_items = []

    for appointment in appointments:
        doctor = (
            db.query(Doctor)
            .filter(Doctor.id == appointment.doctor_id)
            .first()
        )

        appointment_items.append(
            {
                "appointment_id": appointment.id,
                "appointment_date": appointment.appointment_date.isoformat(),
                "start_time": appointment.start_time.strftime("%H:%M"),
                "end_time": appointment.end_time.strftime("%H:%M"),
                "status": appointment.status,
                "reason": appointment.reason,
                "doctor_name": _appointment_doctor_name(doctor),
                "specialization": doctor.specialization if doctor else None,
            }
        )

    return {
        "status": "success",
        "message": f"Found {len(appointment_items)} upcoming appointment(s) for {_patient_full_name(patient)}.",
        "patient": {
            "patient_id": patient.id,
            "patient_number": patient.patient_number,
            "full_name": _patient_full_name(patient),
            "date_of_birth": patient.date_of_birth.isoformat()
            if patient.date_of_birth
            else None,
            "phone_ending": patient.phone[-4:] if patient.phone else None,
        },
        "appointments": appointment_items,
    }


def cancel_appointment_tool(
    db: Session,
    appointment_id: int,
) -> dict:
    """
    Cancels a scheduled appointment.
    This tool assumes auth/RBAC has already been checked by the agent route.
    """

    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )

    if appointment is None:
        return {
            "status": "not_found",
            "message": "Appointment not found.",
            "appointment": None,
        }

    if appointment.status != "scheduled":
        return {
            "status": "not_cancellable",
            "message": f"Appointment is already {appointment.status}.",
            "appointment": {
                "appointment_id": appointment.id,
                "status": appointment.status,
            },
        }

    appointment.status = "cancelled"
    appointment.updated_at = datetime.utcnow()

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "status": "cancelled",
        "message": "Appointment cancelled successfully.",
        "appointment": {
            "appointment_id": appointment.id,
            "appointment_date": appointment.appointment_date.isoformat(),
            "start_time": appointment.start_time.strftime("%H:%M"),
            "end_time": appointment.end_time.strftime("%H:%M"),
            "status": appointment.status,
        },
    }