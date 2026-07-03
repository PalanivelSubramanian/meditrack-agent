from sqlalchemy import Column, Date, DateTime, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_number = Column(String(50), unique=True, nullable=False, index=True)

    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(30), nullable=True)

    phone = Column(String(30), nullable=True, index=True)
    email = Column(String(150), nullable=True)
    address = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    visits = relationship("PatientVisit", back_populates="patient")
    diagnoses = relationship("PatientDiagnosis", back_populates="patient")
    medications = relationship("PatientMedication", back_populates="patient")
    clinical_notes = relationship("PatientClinicalNote", back_populates="patient")