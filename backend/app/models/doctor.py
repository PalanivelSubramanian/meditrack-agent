from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    full_name = Column(String(150), nullable=False, index=True)
    specialization = Column(String(100), nullable=False, index=True)
    department = Column(String(100), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    availability_slots = relationship("DoctorAvailability", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")
    visits = relationship("PatientVisit", back_populates="doctor")
    clinical_notes = relationship("PatientClinicalNote", back_populates="doctor")


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)

    available_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    status = Column(String(30), nullable=False, default="available")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doctor = relationship("Doctor", back_populates="availability_slots")