from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.tools.scheduling_tools import find_available_slots_tool


@dataclass
class DoctorAvailabilityAgentResult:
    message: str
    ui_type: str
    ui_data: dict[str, Any]


class DoctorAvailabilityAgent:
    """
    Finds appointment slots by doctor specialization and date.
    """

    def find_slots(
        self,
        db: Session,
        specialization: str,
        target_date: date,
    ) -> DoctorAvailabilityAgentResult:
        result = find_available_slots_tool(
            db=db,
            specialization=specialization,
            target_date=target_date,
            limit=10,
        )

        if result.count == 0:
            return DoctorAvailabilityAgentResult(
                message=(
                    f"No available {specialization} slots were found "
                    f"for {target_date.isoformat()}."
                ),
                ui_type="availability_no_slots",
                ui_data={
                    "specialization": specialization,
                    "target_date": target_date.isoformat(),
                    "slots": [],
                },
            )

        slots_payload = [slot.model_dump() for slot in result.slots]

        return DoctorAvailabilityAgentResult(
            message=(
                f"I found {result.count} available {specialization} slots "
                f"for {target_date.isoformat()}."
            ),
            ui_type="availability_slots",
            ui_data={
                "specialization": specialization,
                "target_date": target_date.isoformat(),
                "slots": slots_payload,
            },
        )