from sqlalchemy import or_, cast, String
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.schemas.patient import PatientSafeSummary, PatientSearchResult


def _phone_ending(phone: str | None) -> str | None:
    if not phone:
        return None
    return phone[-4:]


def _to_safe_summary(patient: Patient) -> PatientSafeSummary:
    return PatientSafeSummary(
        patient_id=patient.id,
        patient_number=patient.patient_number,
        full_name=f"{patient.first_name} {patient.last_name}",
        date_of_birth=patient.date_of_birth.isoformat(),
        gender=patient.gender,
        phone_ending=_phone_ending(patient.phone),
    )


def search_patient_tool(db: Session, query: str) -> PatientSearchResult:
    """
    Search patients using safe lookup fields.

    This tool returns only identification-safe data.
    It does not return medical history.
    """
    cleaned_query = " ".join(query.strip().split())

    if not cleaned_query:
        return PatientSearchResult(count=0, patients=[])

    like_query = f"%{cleaned_query.lower()}%"
    tokens = cleaned_query.lower().split()

    base_query = db.query(Patient)

    filters = [
        Patient.patient_number.ilike(like_query),
        Patient.first_name.ilike(like_query),
        Patient.last_name.ilike(like_query),
        Patient.phone.ilike(like_query),
        cast(Patient.date_of_birth, String).ilike(like_query),
    ]

    # Full name support: "john smith"
    if len(tokens) >= 2:
        first_token = tokens[0]
        last_token = tokens[-1]
        filters.append(
            Patient.first_name.ilike(f"%{first_token}%")
            & Patient.last_name.ilike(f"%{last_token}%")
        )

    patients = (
        base_query
        .filter(or_(*filters))
        .order_by(Patient.last_name, Patient.first_name, Patient.date_of_birth)
        .limit(10)
        .all()
    )

    safe_patients = [_to_safe_summary(patient) for patient in patients]

    return PatientSearchResult(
        count=len(safe_patients),
        patients=safe_patients,
    )