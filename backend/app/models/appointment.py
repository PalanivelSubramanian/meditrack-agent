from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)

    appointment_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    reason = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="scheduled")

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doctor = relationship("Doctor", back_populates="appointments")


class AppointmentHistory(Base):
    __tablename__ = "appointment_history"

    id = Column(Integer, primary_key=True, index=True)

    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    action = Column(String(100), nullable=False)

    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())