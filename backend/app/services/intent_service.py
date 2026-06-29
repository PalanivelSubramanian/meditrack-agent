import re

from app.schemas.chat import IntentResult


PATIENT_SEARCH_PATTERNS = [
    r"^search patient\s+(?P<query>.+)$",
    r"^find patient\s+(?P<query>.+)$",
    r"^look up patient\s+(?P<query>.+)$",
    r"^lookup patient\s+(?P<query>.+)$",
    r"^check patient\s+(?P<query>.+)$",
    r"^search\s+(?P<query>.+)$",
    r"^find\s+(?P<query>.+)$",
]

BOOK_APPOINTMENT_PATTERNS = [
    r"^book appointment for (?P<patient_query>.+?) with (?P<specialization>\w+) tomorrow at (?P<time>\d{1,2}:\d{2})$",
    r"^schedule appointment for (?P<patient_query>.+?) with (?P<specialization>\w+) tomorrow at (?P<time>\d{1,2}:\d{2})$",
]

PUBLIC_HEALTH_KEYWORDS = [
    "headache",
    "fever",
    "cough",
    "stomach pain",
    "symptom",
    "health tip",
    "diet",
    "exercise",
    "chest pain",
    "cold",
    "flu",
    "pain",
]

AVAILABILITY_PATTERNS = [
    r"^which (?P<specialization>\w+) doctors are available tomorrow\??$",
    r"^which (?P<specialization>\w+) are available tomorrow\??$",
    r"^check (?P<specialization>\w+) availability tomorrow$",
    r"^show (?P<specialization>\w+) slots tomorrow$",
    r"^find (?P<specialization>\w+) availability tomorrow$",
]

def clean_patient_query(query: str) -> str:
    query = query.strip()

    # Remove filler words that users commonly include.
    query = re.sub(r"\bcalled\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\bnamed\b", "", query, flags=re.IGNORECASE)

    return " ".join(query.split())

def normalize_specialization(value: str) -> str:
    value = value.lower().strip()

    mapping = {
        "cardiologist": "cardiology",
        "cardiologists": "cardiology",
        "cardiology": "cardiology",
        "dermatologist": "dermatology",
        "dermatologists": "dermatology",
        "dermatology": "dermatology",
    }

    return mapping.get(value, value)

def detect_intent(message: str) -> IntentResult:
    normalized = message.lower().strip()

    for pattern in BOOK_APPOINTMENT_PATTERNS:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return IntentResult(
                intent="book_appointment",
                confidence=0.90,
                entities={
                    "patient_query": clean_patient_query(match.group("patient_query")),
                    "specialization": match.group("specialization").lower().strip(),
                    "date_text": "tomorrow",
                    "time": match.group("time"),
                },
            )

    for pattern in AVAILABILITY_PATTERNS:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            specialization = normalize_specialization(match.group("specialization"))

            # Normalize common plural words.
            if specialization.endswith("s"):
                specialization = specialization[:-1]

            return IntentResult(
                intent="check_doctor_availability",
                confidence=0.90,
                entities={
                    "specialization": specialization,
                    "date_text": "tomorrow",
                },
            )

    for pattern in PATIENT_SEARCH_PATTERNS:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            raw_query = match.group("query")
            patient_query = clean_patient_query(raw_query)

            # Avoid classifying health questions like "find headache causes" as patient search.
            if any(keyword in patient_query for keyword in PUBLIC_HEALTH_KEYWORDS):
                return IntentResult(
                    intent="public_health_question",
                    confidence=0.75,
                    entities={},
                )

            return IntentResult(
                intent="search_patient",
                confidence=0.95,
                entities={
                    "patient_query": patient_query,
                },
            )

    if "patient" in normalized and any(
        word in normalized for word in ["search", "find", "lookup", "look up", "check"]
    ):
        return IntentResult(
            intent="search_patient",
            confidence=0.80,
            entities={
                "patient_query": normalized.replace("patient", "").strip(),
            },
        )

    if any(keyword in normalized for keyword in PUBLIC_HEALTH_KEYWORDS):
        return IntentResult(
            intent="public_health_question",
            confidence=0.80,
            entities={},
        )

    return IntentResult(
        intent="unknown",
        confidence=0.20,
        entities={},
    )