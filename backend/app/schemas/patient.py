from pydantic import BaseModel


class PatientSafeSummary(BaseModel):
    patient_id: int
    patient_number: str
    full_name: str
    date_of_birth: str
    gender: str | None
    phone_ending: str | None


class PatientSearchResult(BaseModel):
    count: int
    patients: list[PatientSafeSummary]