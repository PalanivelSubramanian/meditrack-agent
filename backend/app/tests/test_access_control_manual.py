from app.agents.access_control_agent import AccessControlAgent


agent = AccessControlAgent()

test_cases = [
    {
        "name": "Guest asks public health question",
        "intent": "public_health_question",
        "user": None,
        "permissions": [],
    },
    {
        "name": "Guest asks patient search",
        "intent": "search_patient",
        "user": None,
        "permissions": [],
    },
    {
        "name": "Receptionist asks patient search",
        "intent": "search_patient",
        "user": object(),
        "permissions": ["search_patient"],
    },
    {
        "name": "Receptionist asks patient history without permission",
        "intent": "view_patient_history",
        "user": object(),
        "permissions": ["search_patient"],
    },
]


for case in test_cases:
    decision = agent.evaluate(
        intent=case["intent"],
        user=case["user"],
        permissions=case["permissions"],
    )

    print(case["name"])
    print(decision)
    print("-" * 40)