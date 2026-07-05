import json
import os
from typing import Any

from openai import OpenAI


LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")


ALLOWED_SPECIALIZATIONS = {
    "cardiology",
    "dermatology",
    "endocrinology",
    "general_medicine",
    "neurology",
    "ophthalmology",
    "orthopedics",
    "pediatrics",
    "psychiatry",
    "pulmonology",
}


def _fallback_reason_result(reason: str, message: str) -> dict[str, Any]:
    return {
        "status": "fallback",
        "reason": reason,
        "suggested_specialization": "general_medicine",
        "confidence": 0.4,
        "urgency": "routine",
        "red_flags": [],
        "patient_message": message,
        "llm_model": None,
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


def _sanitize_reason_result(raw_result: dict[str, Any], reason: str) -> dict[str, Any]:
    suggested_specialization = str(
        raw_result.get("suggested_specialization", "general_medicine")
    ).strip().lower()

    if suggested_specialization not in ALLOWED_SPECIALIZATIONS:
        suggested_specialization = "general_medicine"

    try:
        confidence = float(raw_result.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5

    confidence = max(0.0, min(confidence, 1.0))

    urgency = str(raw_result.get("urgency", "routine")).strip().lower()

    if urgency not in ["routine", "soon", "urgent"]:
        urgency = "routine"

    red_flags = raw_result.get("red_flags", [])

    if not isinstance(red_flags, list):
        red_flags = []

    red_flags = [str(item) for item in red_flags[:6]]

    patient_message = str(
        raw_result.get(
            "patient_message",
            "Based on the appointment reason, general medicine may be appropriate.",
        )
    )

    return {
        "status": "success",
        "reason": reason,
        "suggested_specialization": suggested_specialization,
        "confidence": confidence,
        "urgency": urgency,
        "red_flags": red_flags,
        "patient_message": patient_message,
        "llm_model": LLM_MODEL,
    }


def suggest_specialization_for_reason(reason: str) -> dict[str, Any]:
    cleaned_reason = (reason or "").strip()

    if not cleaned_reason:
        return _fallback_reason_result(
            reason="",
            message="Please provide the reason for the appointment.",
        )

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or api_key.strip() == "" or api_key == "your_api_key_here":
        return _fallback_reason_result(
            reason=cleaned_reason,
            message=(
                "Based on the appointment reason, general medicine may be appropriate. "
                "Please choose a specialization or provide more details."
            ),
        )

    client = OpenAI(api_key=api_key)

    system_prompt = f"""
You are a safe appointment-routing assistant for MediTrack Agent.

Your job is to suggest an appropriate clinic specialization from a fixed allowlist
based only on the appointment reason.

You must not diagnose the patient.
You must not claim the patient has a condition.
You must include urgent-care safety guidance when the reason may involve red flags.

Allowed specializations:
{sorted(ALLOWED_SPECIALIZATIONS)}

Return JSON only in this exact shape:
{{
  "suggested_specialization": "one_allowed_specialization",
  "confidence": 0.0,
  "urgency": "routine|soon|urgent",
  "red_flags": [],
  "patient_message": "short staff-facing routing message with safety guidance when relevant"
}}

Guidance:
- chest pain, palpitations, fainting with chest symptoms: cardiology; urgency can be urgent.
- severe breathing trouble: pulmonology or urgent depending context.
- skin rash, itching, acne: dermatology.
- diabetes, thyroid, hormone follow-up: endocrinology.
- eye pain or vision changes: ophthalmology.
- joint pain, fracture, back pain, injury: orthopedics.
- headache, seizure, weakness, numbness: neurology.
- fever, cough, routine check-up, general symptoms: general_medicine.
- child patient or child-specific symptoms: pediatrics.
- anxiety, depression, sleep/mood concerns: psychiatry.
""".strip()

    user_prompt = {
        "appointment_reason": cleaned_reason,
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

        raw_result = _extract_json_object(response.output_text)

        return _sanitize_reason_result(raw_result, cleaned_reason)

    except Exception as exc:
        return _fallback_reason_result(
            reason=cleaned_reason,
            message=(
                "I could not automatically suggest a specialization. "
                f"Please choose a specialization manually. Reason: {exc}"
            ),
        )