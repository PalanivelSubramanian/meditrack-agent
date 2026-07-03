from app.db.database import SessionLocal
from app.models.patient import Patient
from app.tools.patient_history_tools import get_patient_history_tool


def main():
    db = SessionLocal()

    try:
        patient = (
            db.query(Patient)
            .filter(Patient.patient_number == "P10003")
            .first()
        )

        if not patient:
            print("Patient P10003 not found.")
            return

        result = get_patient_history_tool(db, patient.id)

        print("\nStatus:")
        print(result.status)

        print("\nPatient:")
        print(result.patient)

        print("\nRecent visits:")
        for visit in result.recent_visits:
            print("-", visit.visit_date, visit.visit_type, visit.reason_for_visit)

        print("\nActive diagnoses:")
        for diagnosis in result.active_diagnoses:
            print("-", diagnosis.diagnosis_name, diagnosis.status)

        print("\nCurrent medications:")
        for medication in result.current_medications:
            print("-", medication.medication_name, medication.dosage, medication.frequency)

        print("\nClinical notes:")
        for note in result.clinical_notes:
            print("-", note.note_type, note.note_preview)

    finally:
        db.close()


if __name__ == "__main__":
    main()