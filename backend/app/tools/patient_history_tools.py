from sqlalchemy.orm import Session, joinedload

from app.models.patient import Patient
from app.models.clinical import (
    PatientVisit,
    PatientDiagnosis,
    PatientMedication,
    PatientClinicalNote,
)
from app.schemas.clinical import (
    PatientHistoryIdentity,
    PatientVisitSummary,
    PatientDiagnosisSummary,
    PatientMedicationSummary,
    PatientClinicalNoteSummary,
    PatientHistoryResult,
)


def _phone_ending(phone: str | None) -> str | None:
    if not phone:
        return None

    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) <= 4:
        return digits

    return digits[-4:]


def _full_name(patient: Patient) -> str:
    parts = [patient.first_name, patient.last_name]
    return " ".join(part for part in parts if part)


def _note_preview(note_text: str, max_chars: int = 180) -> str:
    normalized = " ".join(note_text.split())

    if len(normalized) <= max_chars:
        return normalized

    return normalized[: max_chars - 3] + "..."


def get_patient_history_tool(
    db: Session,
    patient_id: int,
    visit_limit: int = 5,
    note_limit: int = 5,
) -> PatientHistoryResult:
    """
    Retrieve a controlled, structured patient history summary.

    Security boundary:
    - This tool assumes the caller has already passed RBAC checks.
    - Do not call this for unauthenticated or unauthorized users.
    - The tool returns summaries/previews, not unlimited raw records.
    """

    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id)
        .first()
    )

    if not patient:
        return PatientHistoryResult(
            status="not_found",
            patient=None,
            message="Patient was not found.",
        )

    recent_visits = (
        db.query(PatientVisit)
        .options(joinedload(PatientVisit.doctor))
        .filter(PatientVisit.patient_id == patient_id)
        .order_by(PatientVisit.visit_date.desc())
        .limit(visit_limit)
        .all()
    )

    active_diagnoses = (
        db.query(PatientDiagnosis)
        .filter(
            PatientDiagnosis.patient_id == patient_id,
            PatientDiagnosis.status.in_(["active", "monitoring"]),
        )
        .order_by(PatientDiagnosis.diagnosed_on.desc().nullslast())
        .all()
    )

    current_medications = (
        db.query(PatientMedication)
        .filter(
            PatientMedication.patient_id == patient_id,
            PatientMedication.status == "active",
        )
        .order_by(PatientMedication.start_date.desc().nullslast())
        .all()
    )

    clinical_notes = (
        db.query(PatientClinicalNote)
        .options(joinedload(PatientClinicalNote.doctor))
        .filter(PatientClinicalNote.patient_id == patient_id)
        .order_by(PatientClinicalNote.created_at.desc())
        .limit(note_limit)
        .all()
    )

    return PatientHistoryResult(
        status="found",
        patient=PatientHistoryIdentity(
            patient_id=patient.id,
            patient_number=patient.patient_number,
            full_name=_full_name(patient),
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            phone_ending=_phone_ending(patient.phone),
        ),
        recent_visits=[
            PatientVisitSummary(
                id=visit.id,
                visit_date=visit.visit_date,
                visit_type=visit.visit_type,
                reason_for_visit=visit.reason_for_visit,
                summary=visit.summary,
                doctor_name=visit.doctor.full_name if visit.doctor else None,
            )
            for visit in recent_visits
        ],
        active_diagnoses=[
            PatientDiagnosisSummary(
                id=diagnosis.id,
                diagnosis_name=diagnosis.diagnosis_name,
                diagnosis_code=diagnosis.diagnosis_code,
                status=diagnosis.status,
                diagnosed_on=diagnosis.diagnosed_on,
            )
            for diagnosis in active_diagnoses
        ],
        current_medications=[
            PatientMedicationSummary(
                id=medication.id,
                medication_name=medication.medication_name,
                dosage=medication.dosage,
                frequency=medication.frequency,
                route=medication.route,
                start_date=medication.start_date,
                end_date=medication.end_date,
                status=medication.status,
            )
            for medication in current_medications
        ],
        clinical_notes=[
            PatientClinicalNoteSummary(
                id=note.id,
                note_type=note.note_type,
                note_preview=_note_preview(note.note_text),
                created_at=note.created_at,
                doctor_name=note.doctor.full_name if note.doctor else None,
            )
            for note in clinical_notes
        ],
        message="Patient history retrieved successfully.",
    )