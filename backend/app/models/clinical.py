from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.database import Base


class PatientVisit(Base):
    __tablename__ = "patient_visits"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)

    visit_date = Column(Date, nullable=False)
    visit_type = Column(String(50), nullable=False, default="consultation")
    reason_for_visit = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient = relationship("Patient", back_populates="visits")
    doctor = relationship("Doctor", back_populates="visits")
    diagnoses = relationship("PatientDiagnosis", back_populates="visit")
    medications = relationship("PatientMedication", back_populates="visit")
    clinical_notes = relationship("PatientClinicalNote", back_populates="visit")


class PatientDiagnosis(Base):
    __tablename__ = "patient_diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    visit_id = Column(Integer, ForeignKey("patient_visits.id"), nullable=True)

    diagnosis_name = Column(String(255), nullable=False)
    diagnosis_code = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    diagnosed_on = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient = relationship("Patient", back_populates="diagnoses")
    visit = relationship("PatientVisit", back_populates="diagnoses")


class PatientMedication(Base):
    __tablename__ = "patient_medications"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    visit_id = Column(Integer, ForeignKey("patient_visits.id"), nullable=True)

    medication_name = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    route = Column(String(50), nullable=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient = relationship("Patient", back_populates="medications")
    visit = relationship("PatientVisit", back_populates="medications")


class PatientClinicalNote(Base):
    __tablename__ = "patient_clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    visit_id = Column(Integer, ForeignKey("patient_visits.id"), nullable=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)

    note_type = Column(String(50), nullable=False, default="clinical")
    note_text = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient = relationship("Patient", back_populates="clinical_notes")
    visit = relationship("PatientVisit", back_populates="clinical_notes")
    doctor = relationship("Doctor", back_populates="clinical_notes")