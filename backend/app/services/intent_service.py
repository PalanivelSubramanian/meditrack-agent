def detect_intent(message: str) -> str:
    normalized = message.lower().strip()

    patient_keywords = [
        "search patient",
        "find patient",
        "look up patient",
        "lookup patient",
        "check patient",
        "patient john",
        "patient aisha",
    ]

    if any(keyword in normalized for keyword in patient_keywords):
        return "search_patient"

    if normalized.startswith("search ") or normalized.startswith("find "):
        if "patient" in normalized or "john" in normalized or "aisha" in normalized:
            return "search_patient"

    health_keywords = [
        "headache",
        "fever",
        "cough",
        "stomach pain",
        "symptom",
        "health tip",
        "diet",
        "exercise",
        "chest pain",
    ]

    if any(keyword in normalized for keyword in health_keywords):
        return "public_health_question"

    return "unknown"