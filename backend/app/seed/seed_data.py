from datetime import date

import pyotp
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.auth import Permission, Role, RolePermission, User
from app.models.patient import Patient


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


def main() -> None:
    db = SessionLocal()

    try:
        roles = seed_roles_permissions(db)
        seed_users(db, roles)
        seed_patients(db)
        print("\nSeed completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()