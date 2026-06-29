from pydantic import BaseModel


class AvailableSlot(BaseModel):
    doctor_id: int
    doctor_name: str
    specialization: str
    department: str
    appointment_date: str
    start_time: str
    end_time: str


class AvailableSlotsResult(BaseModel):
    count: int
    slots: list[AvailableSlot]

class BookAppointmentRequestData(BaseModel):
    patient_query: str
    specialization: str
    appointment_date: str
    start_time: str
    reason: str | None = None


class BookAppointmentResult(BaseModel):
    success: bool
    message: str
    appointment_id: int | None = None
    conflict_reason: str | None = None