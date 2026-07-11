import re
from datetime import date, timedelta

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

DATE_TEXT_GROUP = r"(?:on )?(?P<date_text>today|tomorrow|\d{4}-\d{2}-\d{2})"

AVAILABILITY_PATTERNS = [
    rf"^which (?P<specialization>\w+) doctors are available {DATE_TEXT_GROUP}\??$",
    rf"^which (?P<specialization>\w+) are available {DATE_TEXT_GROUP}\??$",
    rf"^check (?P<specialization>\w+) availability {DATE_TEXT_GROUP}$",
    rf"^show (?P<specialization>\w+) slots {DATE_TEXT_GROUP}$",
    rf"^find (?P<specialization>\w+) availability {DATE_TEXT_GROUP}$",
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

PATIENT_CONTEXT_FOLLOWUP_PATTERNS = [
    r"^what medications is he taking\??$",
    r"^what medications is she taking\??$",
    r"^what medication is he taking\??$",
    r"^what medication is she taking\??$",
    r"^what meds is he taking\??$",
    r"^what meds is she taking\??$",
    r"^show medications$",
    r"^show medication$",
    r"^show meds$",
    r"^current medications$",
    r"^current meds$",
    r"^show recent visits$",
    r"^recent visits$",
    r"^visit history$",
    r"^show visits$",
    r"^any active diagnoses\??$",
    r"^active diagnoses$",
    r"^show diagnoses$",
    r"^show diagnosis$",
    r"^diagnoses$",
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

APPOINTMENT_MANAGEMENT_PATTERNS = [
    r"^cancel appointment for (?P<patient_query>.+)$",
    r"^cancel (?P<patient_query>.+?) appointment$",
    r"^cancel (?P<patient_query>.+?)'s appointment$",
    r"^show (?P<patient_query>.+?) upcoming appointments$",
    r"^show appointments for (?P<patient_query>.+)$",
    r"^list appointments for (?P<patient_query>.+)$",
]

CANCEL_APPOINTMENT_ID_PATTERNS = [
    r"^cancel appointment (?P<appointment_id>\d+)$",
    r"^cancel appointment id (?P<appointment_id>\d+)$",
    r"^cancel booking (?P<appointment_id>\d+)$",
]

PATIENT_HISTORY_SUMMARY_CURRENT_PATIENT_PATTERNS = [
    r"^summarize current patient history$",
    r"^summarize selected patient history$",
    r"^summarize this patient history$",
]

PATIENT_HISTORY_SUMMARY_PATTERNS = [
    r"^summarize (?P<patient_query>.+?) history$",
    r"^summarize (?P<patient_query>.+?)'s history$",
    r"^summarize history for (?P<patient_query>.+)$",
    r"^summary for (?P<patient_query>.+?) history$",
]

PATIENT_REGISTRATION_PATTERNS = [
    r"^register patient (?P<full_name>[a-zA-Z ]+) dob (?P<date_of_birth>\d{4}-\d{2}-\d{2}) phone (?P<phone>[0-9+\-\s]+) gender (?P<gender>male|female|other|unknown)$",
    r"^register new patient (?P<full_name>[a-zA-Z ]+) dob (?P<date_of_birth>\d{4}-\d{2}-\d{2}) phone (?P<phone>[0-9+\-\s]+) gender (?P<gender>male|female|other|unknown)$",
    r"^register patient (?P<full_name>[a-zA-Z ]+) date of birth (?P<date_of_birth>\d{4}-\d{2}-\d{2}) phone (?P<phone>[0-9+\-\s]+) gender (?P<gender>male|female|other|unknown)$",
    r"^register new patient (?P<full_name>[a-zA-Z ]+) date of birth (?P<date_of_birth>\d{4}-\d{2}-\d{2}) phone (?P<phone>[0-9+\-\s]+) gender (?P<gender>male|female|other|unknown)$",
]

def split_full_name(full_name: str) -> tuple[str | None, str | None]:
    parts = full_name.strip().split()

    if len(parts) < 2:
        return None, None

    first_name = parts[0]
    last_name = " ".join(parts[1:])

    return first_name, last_name

def clean_patient_query(query: str) -> str:
    query = query.strip()

    query = re.sub(r"\bcalled\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\bnamed\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\bpatient\b", "", query, flags=re.IGNORECASE)

    return " ".join(query.split())


def resolve_target_date(date_text: str) -> date | None:
    normalized = (date_text or "").strip().lower()

    if normalized == "today":
        return date.today()

    if normalized == "tomorrow":
        return date.today() + timedelta(days=1)

    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


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
                    "date_text": match.group("date_text"),
                },
            )

    for pattern in PATIENT_HISTORY_SUMMARY_CURRENT_PATIENT_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            return IntentResult(
                intent="summarize_patient_history",
                confidence=0.94,
                entities={},
            )

    for pattern in PATIENT_HISTORY_SUMMARY_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            entities = {
                key: value.strip()
                for key, value in match.groupdict().items()
                if value
            }

            return IntentResult(
                intent="summarize_patient_history",
                confidence=0.92,
                entities=entities,
            )

    # 3. Patient context follow-up
    for pattern in PATIENT_CONTEXT_FOLLOWUP_PATTERNS:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return IntentResult(
                intent="patient_context_followup",
                confidence=0.85,
                entities={
                    "followup_text": normalized,
                },
            )

    for pattern in PATIENT_REGISTRATION_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            full_name = match.group("full_name").strip()
            first_name, last_name = split_full_name(full_name)

            if not first_name or not last_name:
                return IntentResult(
                    intent="register_patient",
                    confidence=0.7,
                    entities={
                        "registration_status": "missing_last_name",
                        "full_name": full_name,
                    },
                )

            return IntentResult(
                intent="register_patient",
                confidence=0.95,
                entities={
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": match.group("date_of_birth"),
                    "phone": match.group("phone").strip(),
                    "gender": match.group("gender"),
                },
            )

    # 4. Patient history
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

    # 5. Explicit patient search
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

    for pattern in CANCEL_APPOINTMENT_ID_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            return IntentResult(
                intent="cancel_appointment",
                confidence=0.95,
                entities={
                    "appointment_id": int(match.group("appointment_id")),
                },
            )

    for pattern in APPOINTMENT_MANAGEMENT_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            entities = {
                key: value.strip()
                for key, value in match.groupdict().items()
                if value
            }

            return IntentResult(
                intent="manage_appointment",
                confidence=0.9,
                entities=entities,
            )

    # 6. Public health
    if any(keyword in normalized for keyword in PUBLIC_HEALTH_KEYWORDS):
        return IntentResult(
            intent="public_health_question",
            confidence=0.80,
            entities={},
        )

    # 7. Unknown
    return IntentResult(
        intent="unknown",
        confidence=0.20,
        entities={},
    )