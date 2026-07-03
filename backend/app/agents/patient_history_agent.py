from typing import Any

from sqlalchemy.orm import Session

from app.tools.patient_history_tools import get_patient_history_tool
from app.tools.patient_tools import search_patient_tool


class PatientHistoryAgent:
    """
    Agent responsible for resolving a patient query and retrieving
    structured clinical history.

    Security boundary:
    - This agent assumes RBAC has already approved view_patient_history.
    - Do not call this agent for guests or unauthorized users.
    """

    def get_history_for_query(
        self,
        db: Session,
        patient_query: str,
    ) -> dict[str, Any]:
        normalized_query = patient_query.strip()

        if not normalized_query:
            return {
                "ui_type": "history_patient_no_match",
                "message": "Please provide a patient name or patient number.",
                "ui_data": {
                    "query": patient_query,
                    "matches": [],
                },
            }

        search_result = search_patient_tool(db, normalized_query)
        patients = search_result.patients

        if search_result.count == 0:
            return {
                "ui_type": "history_patient_no_match",
                "message": f"No patient found for '{patient_query}'.",
                "ui_data": {
                    "query": patient_query,
                    "matches": [],
                },
            }

        if search_result.count > 1:
            return {
                "ui_type": "history_patient_matches",
                "message": (
                    f"Multiple patients matched '{patient_query}'. "
                    "Please select the correct patient before viewing history."
                ),
                "ui_data": {
                    "query": patient_query,
                    "matches": [
                        patient.model_dump()
                        for patient in patients
                    ],
                },
            }

        patient_match = patients[0]
        history_result = get_patient_history_tool(db, patient_match.patient_id)

        if history_result.status == "not_found":
            return {
                "ui_type": "history_patient_no_match",
                "message": "Patient was found in search but history record could not be loaded.",
                "ui_data": {
                    "query": patient_query,
                    "matches": [],
                },
            }

        return {
            "ui_type": "patient_history",
            "message": f"Retrieved history for {history_result.patient.full_name}.",
            "ui_data": {
                "patient": history_result.patient.model_dump(),
                "recent_visits": [
                    visit.model_dump()
                    for visit in history_result.recent_visits
                ],
                "active_diagnoses": [
                    diagnosis.model_dump()
                    for diagnosis in history_result.active_diagnoses
                ],
                "current_medications": [
                    medication.model_dump()
                    for medication in history_result.current_medications
                ],
                "clinical_notes": [
                    note.model_dump()
                    for note in history_result.clinical_notes
                ],
            },
        }