import json
import os
from typing import Any

from openai import OpenAI


LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")


ALLOWED_INTENTS = {
    "search_patient",
    "view_patient_history",
    "patient_context_followup",
    "summarize_patient_history",
    "check_doctor_availability",
    "book_appointment",
    "manage_appointment",
    "cancel_appointment",
    "register_patient",
    "public_health_question",
    "clear_patient_context",
    "unknown",
}


INTENT_ENTITY_GUIDE = {
    "search_patient": {
        "required": ["patient_query"],
        "example": {
            "patient_query": "Palanivel Subramanian"
        },
    },
    "view_patient_history": {
        "required": ["patient_query"],
        "example": {
            "patient_query": "Palanivel Subramanian"
        },
    },
    "patient_context_followup": {
        "required": ["followup_text"],
        "example": {
            "followup_text": "show medications"
        },
    },
    "summarize_patient_history": {
        "required": [],
        "example": {
            "patient_query": "Palanivel Subramanian"
        },
    },
    "check_doctor_availability": {
        "required": ["specialization"],
        "example": {
            "specialization": "cardiology",
            "date": "2026-07-10"
        },
    },
    "book_appointment": {
        "required": [],
        "example": {
            "patient_query": "Palanivel Subramanian",
            "specialization": "cardiology",
            "date": "2026-07-10"
        },
    },
    "manage_appointment": {
        "required": ["patient_query"],
        "example": {
            "patient_query": "Palanivel Subramanian"
        },
    },
    "cancel_appointment": {
        "required": ["appointment_id"],
        "example": {
            "appointment_id": 6
        },
    },
    "register_patient": {
        "required": [],
        "example": {
            "first_name": "Palanivel",
            "last_name": "Subramanian",
            "date_of_birth": "1981-02-18",
            "gender": "male",
            "phone": "9876543210"
        },
    },
    "public_health_question": {
        "required": [],
        "example": {},
    },
    "clear_patient_context": {
        "required": [],
        "example": {},
    },
    "unknown": {
        "required": [],
        "example": {},
    },
}


def _no_llm_response(reason: str) -> dict[str, Any]:
    return {
        "intent": "unknown",
        "confidence": 0.0,
        "entities": {},
        "intent_source": "llm_disabled",
        "reason": reason,
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")

    return json.loads(cleaned[start : end + 1])


SYMPTOM_MARKERS = [
    "hurt", "hurts", "pain", "ache", "aches", "fever", "cough",
    "dizzy", "dizziness", "nausea", "vomit", "vomiting", "rash",
    "bleeding", "breath", "breathing", "headache", "sore", "swollen",
]

RECORD_MARKERS = [
    "medication", "medications", "meds", "diagnosis", "diagnoses",
    "visit", "visits", "note", "notes", "history", "record", "chart",
    "clinical", "current patient", "selected patient", "this patient",
]


def _apply_symptom_vs_record_guard(message: str, sanitized: dict[str, Any]) -> dict[str, Any]:
    if sanitized["intent"] != "patient_context_followup":
        return sanitized

    normalized = message.lower()

    has_symptom_marker = any(marker in normalized for marker in SYMPTOM_MARKERS)
    has_record_marker = any(marker in normalized for marker in RECORD_MARKERS)

    if has_symptom_marker and not has_record_marker:
        sanitized["intent"] = "public_health_question"
        sanitized["reason"] = (
            "Guard override: symptom question without explicit record/chart keywords."
        )

    return sanitized


def _sanitize_llm_router_result(raw_result: dict[str, Any]) -> dict[str, Any]:
    intent = str(raw_result.get("intent", "unknown")).strip()

    if intent not in ALLOWED_INTENTS:
        intent = "unknown"

    confidence = raw_result.get("confidence", 0.0)

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(confidence, 1.0))

    entities = raw_result.get("entities", {})

    if not isinstance(entities, dict):
        entities = {}

    reason = raw_result.get("reason", "")

    if reason is None:
        reason = ""

    return {
        "intent": intent,
        "confidence": confidence,
        "entities": entities,
        "intent_source": "llm",
        "reason": str(reason),
    }


def classify_intent_with_llm(
    message: str,
    selected_patient_available: bool = False,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or api_key.strip() == "" or api_key == "your_api_key_here":
        return _no_llm_response("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=api_key)

    system_prompt = f"""
You are an intent router for MediTrack Agent, a healthcare clinic coordination assistant.

Your job is ONLY to classify the user's message into one allowed intent and extract entities.
Do not answer the user directly.
Do not make database changes.
Do not invent patients, appointments, doctors, dates, or medical facts.
Return JSON only.

Allowed intents:
{sorted(ALLOWED_INTENTS)}

Entity guide:
{json.dumps(INTENT_ENTITY_GUIDE, indent=2)}

Rules:
1. Choose exactly one intent.
2. Use "unknown" if the message does not match a clinic workflow or general health question.
3. If the user asks whether a patient exists, wants to find a patient, or asks if the clinic has someone, use "search_patient".
4. If the user asks to open, show, or view history for a patient, use "view_patient_history".
5. Use "patient_context_followup" ONLY when the user explicitly asks about the selected patient's chart or record, such as medications, diagnoses, visits, or clinical notes (e.g. "show medications", "show diagnoses", "what is in the selected patient history"). A patient being selected does NOT by itself turn a general symptom or health question into "patient_context_followup".
6. If the user asks to summarize patient history, use "summarize_patient_history".
7. If the user asks about doctor availability, use "check_doctor_availability".
8. If the user asks to book/schedule an appointment, use "book_appointment".
9. If the user asks to show/list appointments for a patient, use "manage_appointment".
10. If the user asks to cancel appointment by ID, use "cancel_appointment".
11. If the user gives full new patient registration details, use "register_patient".
12. If the user asks general symptoms or general health education (e.g. "my arm hurts", "I have chest pain", "what should I do for fever"), use "public_health_question", even if a patient is currently selected.
13. If the user asks to clear selected/current patient context, use "clear_patient_context".
14. Preserve patient names exactly from the user message where possible.
15. Extract dates only if clearly present.
16. For ambiguous requests, choose the safest intent and use lower confidence.

Return this exact JSON shape:
{{
  "intent": "one_allowed_intent",
  "confidence": 0.0,
  "entities": {{}},
  "reason": "brief reason"
}}
""".strip()

    user_prompt = {
        "message": message,
        "selected_patient_available": selected_patient_available,
    }

    try:
        response = client.responses.create(
            model=LLM_MODEL,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(user_prompt),
                },
            ],
            temperature=0,
        )

        raw_text = response.output_text
        raw_result = _extract_json_object(raw_text)

        sanitized_result = _sanitize_llm_router_result(raw_result)

        return _apply_symptom_vs_record_guard(message, sanitized_result)

    except Exception as exc:
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "entities": {},
            "intent_source": "llm_error",
            "reason": f"LLM intent routing failed: {exc}",
        }