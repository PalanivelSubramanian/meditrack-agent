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