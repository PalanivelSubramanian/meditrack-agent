from app.models.auth import Role, Permission, RolePermission, User, AuthSession
from app.models.patient import Patient
from app.models.chat import ChatSession, ChatMessage, AgentAction, AuditLog
from app.models.doctor import Doctor, DoctorAvailability
from app.models.appointment import Appointment, AppointmentHistory
from app.models.clinical import (
    PatientVisit,
    PatientDiagnosis,
    PatientMedication,
    PatientClinicalNote,
)