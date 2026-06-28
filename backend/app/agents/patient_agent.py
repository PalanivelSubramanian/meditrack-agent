from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.tools.patient_tools import search_patient_tool


@dataclass
class PatientAgentResult:
    message: str
    ui_type: str
    ui_data: dict[str, Any]


class PatientAgent:
    """
    Patient Agent handles patient identity search and match resolution.

    It only returns safe identification data in the search phase.
    """

    def search_patient(self, db: Session, query: str) -> PatientAgentResult:
        result = search_patient_tool(db, query)

        if result.count == 0:
            return PatientAgentResult(
                message=(
                    "No matching patient was found. Please check the name, "
                    "phone number, date of birth, or patient number."
                ),
                ui_type="patient_no_match",
                ui_data={
                    "query": query,
                    "patients": [],
                },
            )

        patients_payload = [
            patient.model_dump()
            for patient in result.patients
        ]

        if result.count == 1:
            patient = result.patients[0]
            return PatientAgentResult(
                message=(
                    f"I found one matching patient: {patient.full_name}, "
                    f"DOB: {patient.date_of_birth}, "
                    f"phone ending {patient.phone_ending}."
                ),
                ui_type="patient_single_match",
                ui_data={
                    "query": query,
                    "selected_patient": patient.model_dump(),
                },
            )

        return PatientAgentResult(
            message=(
                f"I found {result.count} matching patients. "
                "Please confirm which patient you mean."
            ),
            ui_type="patient_matches",
            ui_data={
                "query": query,
                "patients": patients_payload,
            },
        )