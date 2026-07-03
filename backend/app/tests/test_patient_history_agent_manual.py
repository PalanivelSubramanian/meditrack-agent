from app.agents.patient_history_agent import PatientHistoryAgent
from app.db.database import SessionLocal


def print_result(title: str, result: dict):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("ui_type:", result["ui_type"])
    print("message:", result["message"])

    ui_data = result.get("ui_data", {})

    if result["ui_type"] == "patient_history":
        patient = ui_data["patient"]
        print("patient:", patient["patient_number"], patient["full_name"])

        print("\nrecent visits:")
        for visit in ui_data["recent_visits"]:
            print("-", visit["visit_date"], visit["visit_type"], visit["reason_for_visit"])

        print("\nactive diagnoses:")
        for diagnosis in ui_data["active_diagnoses"]:
            print("-", diagnosis["diagnosis_name"], diagnosis["status"])

        print("\ncurrent medications:")
        for medication in ui_data["current_medications"]:
            print("-", medication["medication_name"], medication["dosage"], medication["frequency"])

        print("\nclinical notes:")
        for note in ui_data["clinical_notes"]:
            print("-", note["note_type"], note["note_preview"])

    elif result["ui_type"] == "history_patient_matches":
        print("\nmatches:")
        for match in ui_data["matches"]:
            print(
                "-",
                match["patient_number"],
                match["full_name"],
                "DOB:",
                match["date_of_birth"],
                "phone ending:",
                match["phone_ending"],
            )

    else:
        print("data:", ui_data)


def main():
    db = SessionLocal()
    agent = PatientHistoryAgent()

    try:
        test_queries = [
            "Aisha Rahman",
            "P10003",
            "John Smith",
            "Unknown Person",
            "",
        ]

        for query in test_queries:
            result = agent.get_history_for_query(db, query)
            print_result(f"Query: {query!r}", result)

    finally:
        db.close()


if __name__ == "__main__":
    main()