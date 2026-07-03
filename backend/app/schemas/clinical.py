from datetime import date, datetime
from pydantic import BaseModel


class PatientHistoryIdentity(BaseModel):
    patient_id: int
    patient_number: str
    full_name: str
    date_of_birth: date | None
    gender: str | None
    phone_ending: str | None


class PatientVisitSummary(BaseModel):
    id: int
    visit_date: date
    visit_type: str
    reason_for_visit: str | None
    summary: str | None
    doctor_name: str | None


class PatientDiagnosisSummary(BaseModel):
    id: int
    diagnosis_name: str
    diagnosis_code: str | None
    status: str
    diagnosed_on: date | None


class PatientMedicationSummary(BaseModel):
    id: int
    medication_name: str
    dosage: str | None
    frequency: str | None
    route: str | None
    start_date: date | None
    end_date: date | None
    status: str


class PatientClinicalNoteSummary(BaseModel):
    id: int
    note_type: str
    note_preview: str
    created_at: datetime
    doctor_name: str | None


class PatientHistoryResult(BaseModel):
    status: str
    patient: PatientHistoryIdentity | None = None
    recent_visits: list[PatientVisitSummary] = []
    active_diagnoses: list[PatientDiagnosisSummary] = []
    current_medications: list[PatientMedicationSummary] = []
    clinical_notes: list[PatientClinicalNoteSummary] = []
    message: str