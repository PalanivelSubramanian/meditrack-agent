import os
from typing import Any

from openai import OpenAI


LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")


def _format_history_for_summary(history_data: dict[str, Any]) -> str:
    patient = history_data.get("patient", {})
    visits = history_data.get("recent_visits", [])
    diagnoses = history_data.get("active_diagnoses", [])
    medications = history_data.get("current_medications", [])
    notes = history_data.get("clinical_notes", [])

    lines: list[str] = []

    lines.append("PATIENT")
    lines.append(f"Name: {patient.get('full_name')}")
    lines.append(f"Patient number: {patient.get('patient_number')}")
    lines.append(f"DOB: {patient.get('date_of_birth')}")
    lines.append("")

    lines.append("RECENT VISITS")
    for visit in visits:
        lines.append(
            "- "
            f"{visit.get('visit_date')} | "
            f"{visit.get('visit_type')} | "
            f"Doctor: {visit.get('doctor_name')} | "
            f"Reason: {visit.get('reason_for_visit')} | "
            f"Summary: {visit.get('summary')}"
        )
    lines.append("")

    lines.append("ACTIVE DIAGNOSES")
    for diagnosis in diagnoses:
        lines.append(
            "- "
            f"{diagnosis.get('diagnosis_name')} | "
            f"Code: {diagnosis.get('diagnosis_code')} | "
            f"Status: {diagnosis.get('status')} | "
            f"Since: {diagnosis.get('diagnosed_on')}"
        )
    lines.append("")

    lines.append("CURRENT MEDICATIONS")
    for medication in medications:
        lines.append(
            "- "
            f"{medication.get('medication_name')} | "
            f"Dose: {medication.get('dosage')} | "
            f"Frequency: {medication.get('frequency')} | "
            f"Route: {medication.get('route')} | "
            f"Status: {medication.get('status')}"
        )
    lines.append("")

    lines.append("CLINICAL NOTES")
    for note in notes:
        lines.append(
            "- "
            f"{note.get('note_type')} | "
            f"Doctor: {note.get('doctor_name')} | "
            f"Note: {note.get('note_preview')}"
        )

    return "\n".join(lines)


def summarize_patient_history_with_llm(history_data: dict[str, Any]) -> dict[str, Any]:
    """
    Summarizes already-authorized patient history data.

    Safety rules:
    - Does not fetch data.
    - Does not make diagnoses.
    - Does not prescribe treatment.
    - Does not replace clinician judgment.
    """

    if not os.getenv("OPENAI_API_KEY"):
        return {
            "status": "disabled",
            "summary": (
                "LLM summary is not configured because OPENAI_API_KEY is missing."
            ),
            "model": None,
        }

    client = OpenAI()

    formatted_history = _format_history_for_summary(history_data)

    response = client.responses.create(
        model=LLM_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a clinical operations assistant for authorized clinic staff. "
                    "Summarize the provided patient history clearly and cautiously. "
                    "Do not diagnose. Do not recommend medication changes. "
                    "Do not invent facts. Use only the provided data. "
                    "Include a short safety note that clinicians should verify details in the chart."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize this patient history for staff handoff. "
                    "Use concise bullets under these headings: "
                    "Overview, Recent visits, Active problems, Current medications, Notes for staff.\n\n"
                    f"{formatted_history}"
                ),
            },
        ],
    )

    return {
        "status": "success",
        "summary": response.output_text,
        "model": LLM_MODEL,
    }

def answer_public_health_question_with_llm(question: str) -> dict[str, Any]:
    """
    Answers public/general health questions safely.

    Safety rules:
    - No diagnosis.
    - No prescriptions.
    - No medication dose instructions.
    - No patient-specific clinical decisions.
    - Must include urgent red flags when relevant.
    """

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key or api_key == "your_api_key_here":
        return {
            "status": "disabled",
            "answer": (
                "I can share general health information, but LLM public health answers "
                "are not configured because OPENAI_API_KEY is missing. "
                "If symptoms are severe, worsening, or urgent, please contact a healthcare professional."
            ),
            "model": None,
        }

    client = OpenAI()

    response = client.responses.create(
        model=LLM_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a cautious public health education assistant. "
                    "Answer general health questions in plain language. "
                    "Do not diagnose the user. "
                    "Do not prescribe treatment. "
                    "Do not give medication dosage instructions. "
                    "Do not claim certainty. "
                    "Do not ask for or use private patient records. "
                    "Include urgent warning signs or red flags when relevant. "
                    "Recommend contacting a licensed healthcare professional for persistent, severe, worsening, or concerning symptoms."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Give a safe, general educational answer to this health question. "
                    "Use this structure:\n"
                    "1. A short direct answer\n"
                    "2. Common possible causes or explanations\n"
                    "3. Basic self-care or monitoring ideas, without medication dosing\n"
                    "4. Red flags / when to seek urgent care\n"
                    "5. A brief note that this is not a diagnosis\n\n"
                    f"Question: {question}"
                ),
            },
        ],
    )

    return {
        "status": "success",
        "answer": response.output_text,
        "model": LLM_MODEL,
    }