from datetime import date
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.patient import Patient


REQUIRED_PATIENT_REGISTRATION_FIELDS = [
    "first_name",
    "last_name",
    "date_of_birth",
    "gender",
    "phone",
]


def _generate_patient_number() -> str:
    return f"P{str(uuid4().int)[0:8]}"


def _normalize_phone(phone: str) -> str:
    return phone.strip().replace(" ", "").replace("-", "")


def validate_patient_registration_payload(payload: dict) -> dict:
    missing_fields = [
        field
        for field in REQUIRED_PATIENT_REGISTRATION_FIELDS
        if not payload.get(field)
    ]

    if missing_fields:
        return {
            "status": "missing_fields",
            "missing_fields": missing_fields,
        }

    try:
        parsed_dob = date.fromisoformat(str(payload["date_of_birth"]))
    except ValueError:
        return {
            "status": "invalid_date",
            "message": "Date of birth must be in YYYY-MM-DD format.",
        }

    normalized_gender = str(payload["gender"]).strip().lower()

    if normalized_gender not in ["male", "female", "other", "unknown"]:
        return {
            "status": "invalid_gender",
            "message": "Gender must be male, female, other, or unknown.",
        }

    normalized_phone = _normalize_phone(str(payload["phone"]))

    if len(normalized_phone) < 7:
        return {
            "status": "invalid_phone",
            "message": "Phone number must have at least 7 digits.",
        }

    return {
        "status": "valid",
        "payload": {
            "first_name": str(payload["first_name"]).strip(),
            "last_name": str(payload["last_name"]).strip(),
            "date_of_birth": parsed_dob,
            "gender": normalized_gender,
            "phone": normalized_phone,
        },
    }


def register_patient_tool(
    db: Session,
    payload: dict,
) -> dict:
    """
    Registers a new patient.
    This tool assumes auth/RBAC has already been checked.
    """

    validation = validate_patient_registration_payload(payload)

    if validation["status"] != "valid":
        return validation

    data = validation["payload"]

    existing_patient = (
        db.query(Patient)
        .filter(
            Patient.first_name.ilike(data["first_name"]),
            Patient.last_name.ilike(data["last_name"]),
            Patient.date_of_birth == data["date_of_birth"],
        )
        .first()
    )

    if existing_patient:
        return {
            "status": "duplicate_possible",
            "message": "A patient with the same name and date of birth already exists.",
            "patient": {
                "patient_id": existing_patient.id,
                "patient_number": existing_patient.patient_number,
                "full_name": f"{existing_patient.first_name} {existing_patient.last_name}",
                "date_of_birth": existing_patient.date_of_birth.isoformat()
                if existing_patient.date_of_birth
                else None,
                "gender": existing_patient.gender,
                "phone_ending": existing_patient.phone[-4:]
                if existing_patient.phone
                else None,
            },
        }

    patient = Patient(
        patient_number=_generate_patient_number(),
        first_name=data["first_name"],
        last_name=data["last_name"],
        date_of_birth=data["date_of_birth"],
        gender=data["gender"],
        phone=data["phone"],
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    return {
        "status": "created",
        "message": f"Registered new patient {patient.first_name} {patient.last_name}.",
        "patient": {
            "patient_id": patient.id,
            "patient_number": patient.patient_number,
            "full_name": f"{patient.first_name} {patient.last_name}",
            "date_of_birth": patient.date_of_birth.isoformat()
            if patient.date_of_birth
            else None,
            "gender": patient.gender,
            "phone_ending": patient.phone[-4:] if patient.phone else None,
        },
    }