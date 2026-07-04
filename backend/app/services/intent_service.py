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

AVAILABILITY_PATTERNS = [
    r"^which (?P<specialization>\w+) doctors are available tomorrow\??$",
    r"^which (?P<specialization>\w+) are available tomorrow\??$",
    r"^check (?P<specialization>\w+) availability tomorrow$",
    r"^show (?P<specialization>\w+) slots tomorrow$",
    r"^find (?P<specialization>\w+) availability tomorrow$",
]

PATIENT_HISTORY_PATTERNS = [
    r"^show history for (?P<patient_query>.+)$",
    r"^show patient history for (?P<patient_query>.+)$",
    r"^view history for (?P<patient_query>.+)$",
    r"^view patient history for (?P<patient_query>.+)$",
    r"^open (?P<patient_query>p\d+)$",
    r"^select (?P<patient_query>p\d+)$",
    r"^choose (?P<patient_query>p\d+)$",
    r"^show (?P<patient_query>.+?) history$",
    r"^show (?P<patient_query>.+?) patient history$",
    r"^view (?P<patient_query>.+?) history$",
    r"^view (?P<patient_query>.+?) patient history$",
    r"^summarize patient (?P<patient_query>.+?) history$",
    r"^summarize (?P<patient_query>.+?) history$",
    r"^what medications is (?P<patient_query>.+?) taking\??$",
    r"^what medication is (?P<patient_query>.+?) taking\??$",
    r"^what meds is (?P<patient_query>.+?) taking\??$",
    r"^show medications for (?P<patient_query>.+)$",
    r"^show medication for (?P<patient_query>.+)$",
    r"^show meds for (?P<patient_query>.+)$",
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


def clean_patient_query(query: str) -> str:
    query = query.strip()

    query = re.sub(r"\bcalled\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\bnamed\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\bpatient\b", "", query, flags=re.IGNORECASE)

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

    # 1. Book appointment
    for pattern in BOOK_APPOINTMENT_PATTERNS:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return IntentResult(
                intent="book_appointment",
                confidence=0.90,
                entities={
                    "patient_query": clean_patient_query(match.group("patient_query")),
                    "specialization": normalize_specialization(match.group("specialization")),
                    "date_text": "tomorrow",
                    "time": match.group("time"),
                },
            )

    # 2. Doctor availability
    for pattern in AVAILABILITY_PATTERNS:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return IntentResult(
                intent="check_doctor_availability",
                confidence=0.90,
                entities={
                    "specialization": normalize_specialization(match.group("specialization")),
                    "date_text": "tomorrow",
                },
            )

    # 3. Patient history
    for pattern in PATIENT_HISTORY_PATTERNS:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return IntentResult(
                intent="view_patient_history",
                confidence=0.90,
                entities={
                    "patient_query": clean_patient_query(match.group("patient_query")),
                },
            )

    # 4. Explicit patient search
    for pattern in PATIENT_SEARCH_PATTERNS:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            patient_query = clean_patient_query(match.group("query"))

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

    # 5. Public health
    if any(keyword in normalized for keyword in PUBLIC_HEALTH_KEYWORDS):
        return IntentResult(
            intent="public_health_question",
            confidence=0.80,
            entities={},
        )

    # 6. Unknown
    return IntentResult(
        intent="unknown",
        confidence=0.20,
        entities={},
    )