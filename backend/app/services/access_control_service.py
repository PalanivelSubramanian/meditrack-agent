PROTECTED_INTENT_PERMISSIONS = {
    "search_patient": "search_patient",
    "view_patient_history": "view_patient_history",
    "patient_context_followup": "view_patient_history",
    "summarize_patient_history": "view_patient_history",
    "register_patient": "search_patient",
    "book_appointment": "book_appointment",
    "cancel_appointment": "cancel_appointment",
    "reschedule_appointment": "reschedule_appointment",
    "check_doctor_availability": "check_doctor_availability",
    "create_reminder": "create_reminder",
    "manage_appointment": "cancel_appointment",
}


def get_required_permission(intent: str) -> str | None:
    return PROTECTED_INTENT_PERMISSIONS.get(intent)


def is_protected_intent(intent: str) -> bool:
    return intent in PROTECTED_INTENT_PERMISSIONS


def has_permission(user_permissions: list[str], required_permission: str) -> bool:
    return required_permission in user_permissions