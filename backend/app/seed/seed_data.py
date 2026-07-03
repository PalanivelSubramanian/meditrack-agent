from datetime import date, time, timedelta

import pyotp
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.auth import Permission, Role, RolePermission, User
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentHistory
from app.models.doctor import Doctor, DoctorAvailability
from app.models.clinical import (
    PatientVisit,
    PatientDiagnosis,
    PatientMedication,
    PatientClinicalNote,
)

ROLES = ["receptionist", "doctor", "admin"]

PERMISSIONS = [
    "search_patient",
    "view_patient_history",
    "book_appointment",
    "cancel_appointment",
    "reschedule_appointment",
    "check_doctor_availability",
    "create_reminder",
    "view_audit_logs",
]

ROLE_PERMISSION_MAP = {
    "receptionist": [
        "search_patient",
        "book_appointment",
        "cancel_appointment",
        "reschedule_appointment",
        "check_doctor_availability",
        "create_reminder",
    ],
    "doctor": [
        "search_patient",
        "view_patient_history",
        "check_doctor_availability",
    ],
    "admin": PERMISSIONS,
}


DEMO_USERS = [
    {
        "employee_id": "EMP1001",
        "full_name": "Riya Receptionist",
        "email": "reception@meditrack.local",
        "role": "receptionist",
    },
    {
        "employee_id": "DOC2001",
        "full_name": "Dr. Arjun Mehta",
        "email": "doctor@meditrack.local",
        "role": "doctor",
    },
    {
        "employee_id": "ADM9001",
        "full_name": "Anika Admin",
        "email": "admin@meditrack.local",
        "role": "admin",
    },
]


DEMO_PATIENTS = [
    {
        "patient_number": "P10001",
        "first_name": "John",
        "last_name": "Smith",
        "date_of_birth": date(1980, 5, 12),
        "gender": "male",
        "phone": "5551114432",
        "email": "john.smith.1980@example.com",
        "address": "12 Lake Road",
    },
    {
        "patient_number": "P10002",
        "first_name": "John",
        "last_name": "Smith",
        "date_of_birth": date(1992, 2, 3),
        "gender": "male",
        "phone": "5552229011",
        "email": "john.smith.1992@example.com",
        "address": "88 Green Street",
    },
    {
        "patient_number": "P10003",
        "first_name": "Aisha",
        "last_name": "Rahman",
        "date_of_birth": date(1991, 5, 14),
        "gender": "female",
        "phone": "5553332044",
        "email": "aisha.rahman@example.com",
        "address": "21 Park Avenue",
    },
]

DEMO_DOCTORS = [
    {
        "full_name": "Dr. Arjun Mehta",
        "specialization": "cardiology",
        "department": "cardiology",
        "status": "active",
    },
    {
        "full_name": "Dr. Priya Nair",
        "specialization": "cardiology",
        "department": "cardiology",
        "status": "active",
    },
    {
        "full_name": "Dr. Kavita Rao",
        "specialization": "dermatology",
        "department": "dermatology",
        "status": "active",
    },
]


def get_or_create_role(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.role_name == role_name).first()
    if role:
        return role

    role = Role(role_name=role_name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def get_or_create_permission(db: Session, permission_name: str) -> Permission:
    permission = (
        db.query(Permission)
        .filter(Permission.permission_name == permission_name)
        .first()
    )
    if permission:
        return permission

    permission = Permission(permission_name=permission_name)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


def assign_permission_to_role(db: Session, role: Role, permission: Permission) -> None:
    existing = (
        db.query(RolePermission)
        .filter(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
        .first()
    )

    if existing:
        return

    role_permission = RolePermission(
        role_id=role.id,
        permission_id=permission.id,
    )
    db.add(role_permission)
    db.commit()


def seed_roles_permissions(db: Session) -> dict[str, Role]:
    roles = {}
    permissions = {}

    for role_name in ROLES:
        roles[role_name] = get_or_create_role(db, role_name)

    for permission_name in PERMISSIONS:
        permissions[permission_name] = get_or_create_permission(db, permission_name)

    for role_name, permission_names in ROLE_PERMISSION_MAP.items():
        role = roles[role_name]
        for permission_name in permission_names:
            assign_permission_to_role(db, role, permissions[permission_name])

    return roles


def seed_users(db: Session, roles: dict[str, Role]) -> None:
    print("\nDemo user TOTP secrets")
    print("----------------------")

    for user_data in DEMO_USERS:
        existing_user = (
            db.query(User)
            .filter(User.employee_id == user_data["employee_id"])
            .first()
        )

        if existing_user:
            print(
                f"{existing_user.employee_id} already exists. "
                f"TOTP secret: {existing_user.totp_secret_encrypted}"
            )
            continue

        totp_secret = pyotp.random_base32()

        user = User(
            employee_id=user_data["employee_id"],
            full_name=user_data["full_name"],
            email=user_data["email"],
            role_id=roles[user_data["role"]].id,
            status="active",
            totp_enabled=True,
            # For MVP/dev only. Later this should be encrypted.
            totp_secret_encrypted=totp_secret,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"{user.employee_id} / {user.full_name}")
        print(f"TOTP secret: {totp_secret}")
        print(f"Authenticator URI: {pyotp.totp.TOTP(totp_secret).provisioning_uri(name=user.email, issuer_name='MediTrack Agent')}")
        print()


def seed_patients(db: Session) -> None:
    for patient_data in DEMO_PATIENTS:
        existing_patient = (
            db.query(Patient)
            .filter(Patient.patient_number == patient_data["patient_number"])
            .first()
        )

        if existing_patient:
            continue

        patient = Patient(**patient_data)
        db.add(patient)

    db.commit()

def seed_doctors(db: Session) -> list[Doctor]:
    doctors: list[Doctor] = []

    for doctor_data in DEMO_DOCTORS:
        existing_doctor = (
            db.query(Doctor)
            .filter(Doctor.full_name == doctor_data["full_name"])
            .first()
        )

        if existing_doctor:
            doctors.append(existing_doctor)
            continue

        doctor = Doctor(**doctor_data)
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        doctors.append(doctor)

    return doctors


def seed_doctor_availability(db: Session, doctors: list[Doctor]) -> None:
    today = date.today()

    for doctor in doctors:
        for day_offset in range(1, 8):
            available_date = today + timedelta(days=day_offset)

            existing_slot = (
                db.query(DoctorAvailability)
                .filter(
                    DoctorAvailability.doctor_id == doctor.id,
                    DoctorAvailability.available_date == available_date,
                    DoctorAvailability.start_time == time(9, 0),
                    DoctorAvailability.end_time == time(17, 0),
                )
                .first()
            )

            if existing_slot:
                continue

            slot = DoctorAvailability(
                doctor_id=doctor.id,
                available_date=available_date,
                start_time=time(9, 0),
                end_time=time(17, 0),
                status="available",
            )

            db.add(slot)

    db.commit()

def seed_sample_appointments(db: Session) -> None:
    today = date.today()
    appointment_date = today + timedelta(days=1)

    patient = (
        db.query(Patient)
        .filter(Patient.patient_number == "P10001")
        .first()
    )

    doctor = (
        db.query(Doctor)
        .filter(Doctor.full_name == "Dr. Arjun Mehta")
        .first()
    )

    if not patient or not doctor:
        return

    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == appointment_date,
            Appointment.start_time == time(10, 0),
        )
        .first()
    )

    if existing_appointment:
        return

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=appointment_date,
        start_time=time(10, 0),
        end_time=time(10, 30),
        reason="Existing cardiology follow-up",
        status="scheduled",
        created_by=None,
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    history = AppointmentHistory(
        appointment_id=appointment.id,
        action="created",
        old_value=None,
        new_value="Seeded sample appointment at 10:00",
        changed_by=None,
    )

    db.add(history)
    db.commit()

def seed_clinical_history(db: Session):
    patients = {
        patient.patient_number: patient
        for patient in db.query(Patient).all()
    }

    doctors = {
        doctor.full_name: doctor
        for doctor in db.query(Doctor).all()
    }

    required_patients = ["P10001", "P10002", "P10003"]
    missing_patients = [p for p in required_patients if p not in patients]

    if missing_patients:
        print(f"Skipping clinical history seed. Missing patients: {missing_patients}")
        return

    if not doctors:
        print("Skipping clinical history seed. No doctors found.")
        return

    dr_arjun = doctors.get("Dr. Arjun Mehta")
    dr_priya = doctors.get("Dr. Priya Nair")
    dr_kavita = doctors.get("Dr. Kavita Rao")

    # Make this seed idempotent for demo purposes.
    existing_visit = (
        db.query(PatientVisit)
        .filter(PatientVisit.patient_id == patients["P10003"].id)
        .first()
    )

    if existing_visit:
        print("Clinical history already seeded. Skipping.")
        return

    john_older = patients["P10001"]
    john_younger = patients["P10002"]
    aisha = patients["P10003"]

    today = date.today()

    # -------------------------
    # P10001 — John Smith, older
    # -------------------------
    john_visit_1 = PatientVisit(
        patient_id=john_older.id,
        doctor_id=dr_arjun.id if dr_arjun else None,
        visit_date=today - timedelta(days=120),
        visit_type="consultation",
        reason_for_visit="Intermittent chest discomfort and elevated blood pressure",
        summary="Patient reported occasional chest tightness during exertion. Blood pressure was elevated. Lifestyle changes and follow-up were advised.",
    )

    john_visit_2 = PatientVisit(
        patient_id=john_older.id,
        doctor_id=dr_priya.id if dr_priya else None,
        visit_date=today - timedelta(days=35),
        visit_type="follow_up",
        reason_for_visit="Blood pressure follow-up",
        summary="Blood pressure improved but still above target. Medication adherence reviewed. No acute chest pain reported.",
    )

    db.add_all([john_visit_1, john_visit_2])
    db.flush()

    db.add_all(
        [
            PatientDiagnosis(
                patient_id=john_older.id,
                visit_id=john_visit_1.id,
                diagnosis_name="Hypertension",
                diagnosis_code="I10",
                status="active",
                diagnosed_on=today - timedelta(days=120),
            ),
            PatientDiagnosis(
                patient_id=john_older.id,
                visit_id=john_visit_1.id,
                diagnosis_name="Chest pain, unspecified",
                diagnosis_code="R07.9",
                status="resolved",
                diagnosed_on=today - timedelta(days=120),
            ),
            PatientMedication(
                patient_id=john_older.id,
                visit_id=john_visit_1.id,
                medication_name="Amlodipine",
                dosage="5 mg",
                frequency="Once daily",
                route="oral",
                start_date=today - timedelta(days=120),
                status="active",
            ),
            PatientMedication(
                patient_id=john_older.id,
                visit_id=john_visit_2.id,
                medication_name="Atorvastatin",
                dosage="10 mg",
                frequency="Once nightly",
                route="oral",
                start_date=today - timedelta(days=35),
                status="active",
            ),
            PatientClinicalNote(
                patient_id=john_older.id,
                visit_id=john_visit_1.id,
                doctor_id=dr_arjun.id if dr_arjun else None,
                note_type="clinical",
                note_text="Advised home BP monitoring, low-sodium diet, and follow-up in 4 weeks. ECG did not show acute ischemic changes.",
            ),
            PatientClinicalNote(
                patient_id=john_older.id,
                visit_id=john_visit_2.id,
                doctor_id=dr_priya.id if dr_priya else None,
                note_type="follow_up",
                note_text="Patient reports improved exercise tolerance. Continue antihypertensive therapy and review lipid panel at next visit.",
            ),
        ]
    )

    # -------------------------
    # P10002 — John Smith, younger
    # -------------------------
    younger_john_visit = PatientVisit(
        patient_id=john_younger.id,
        doctor_id=dr_kavita.id if dr_kavita else None,
        visit_date=today - timedelta(days=18),
        visit_type="consultation",
        reason_for_visit="Persistent skin rash on forearms",
        summary="Patient presented with itchy rash after possible detergent exposure. No fever or systemic symptoms.",
    )

    db.add(younger_john_visit)
    db.flush()

    db.add_all(
        [
            PatientDiagnosis(
                patient_id=john_younger.id,
                visit_id=younger_john_visit.id,
                diagnosis_name="Contact dermatitis",
                diagnosis_code="L25.9",
                status="active",
                diagnosed_on=today - timedelta(days=18),
            ),
            PatientMedication(
                patient_id=john_younger.id,
                visit_id=younger_john_visit.id,
                medication_name="Hydrocortisone cream",
                dosage="1%",
                frequency="Apply twice daily for 7 days",
                route="topical",
                start_date=today - timedelta(days=18),
                end_date=today - timedelta(days=11),
                status="completed",
            ),
            PatientClinicalNote(
                patient_id=john_younger.id,
                visit_id=younger_john_visit.id,
                doctor_id=dr_kavita.id if dr_kavita else None,
                note_type="clinical",
                note_text="Likely irritant contact dermatitis. Advised avoiding suspected detergent and returning if rash spreads or worsens.",
            ),
        ]
    )

    # -------------------------
    # P10003 — Aisha Rahman
    # -------------------------
    aisha_visit_1 = PatientVisit(
        patient_id=aisha.id,
        doctor_id=dr_arjun.id if dr_arjun else None,
        visit_date=today - timedelta(days=75),
        visit_type="consultation",
        reason_for_visit="Palpitations and fatigue",
        summary="Patient reported episodic palpitations and fatigue. Basic cardiac evaluation was reassuring. Thyroid testing was recommended.",
    )

    aisha_visit_2 = PatientVisit(
        patient_id=aisha.id,
        doctor_id=dr_priya.id if dr_priya else None,
        visit_date=today - timedelta(days=20),
        visit_type="follow_up",
        reason_for_visit="Follow-up after lab review",
        summary="Symptoms improved. Lab review suggested mild iron deficiency. Supplementation and dietary counseling provided.",
    )

    db.add_all([aisha_visit_1, aisha_visit_2])
    db.flush()

    db.add_all(
        [
            PatientDiagnosis(
                patient_id=aisha.id,
                visit_id=aisha_visit_1.id,
                diagnosis_name="Palpitations",
                diagnosis_code="R00.2",
                status="monitoring",
                diagnosed_on=today - timedelta(days=75),
            ),
            PatientDiagnosis(
                patient_id=aisha.id,
                visit_id=aisha_visit_2.id,
                diagnosis_name="Iron deficiency anemia, mild",
                diagnosis_code="D50.9",
                status="active",
                diagnosed_on=today - timedelta(days=20),
            ),
            PatientMedication(
                patient_id=aisha.id,
                visit_id=aisha_visit_2.id,
                medication_name="Ferrous sulfate",
                dosage="325 mg",
                frequency="Once daily",
                route="oral",
                start_date=today - timedelta(days=20),
                status="active",
            ),
            PatientMedication(
                patient_id=aisha.id,
                visit_id=aisha_visit_1.id,
                medication_name="Multivitamin",
                dosage="One tablet",
                frequency="Once daily",
                route="oral",
                start_date=today - timedelta(days=75),
                status="active",
            ),
            PatientClinicalNote(
                patient_id=aisha.id,
                visit_id=aisha_visit_1.id,
                doctor_id=dr_arjun.id if dr_arjun else None,
                note_type="clinical",
                note_text="No syncope, chest pain, or shortness of breath reported. Advised symptom diary and follow-up after labs.",
            ),
            PatientClinicalNote(
                patient_id=aisha.id,
                visit_id=aisha_visit_2.id,
                doctor_id=dr_priya.id if dr_priya else None,
                note_type="follow_up",
                note_text="Patient reports fewer palpitations. Discussed iron-rich diet and repeat CBC in 8 weeks.",
            ),
        ]
    )

    db.commit()
    print("Clinical history seeded successfully.")

def main() -> None:
    db = SessionLocal()

    try:
        roles = seed_roles_permissions(db)
        seed_users(db, roles)
        seed_patients(db)

        doctors = seed_doctors(db)
        seed_doctor_availability(db, doctors)
        seed_sample_appointments(db)

        seed_clinical_history(db)

        print("\nSeed completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()