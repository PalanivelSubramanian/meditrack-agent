from app.services.intent_service import detect_intent


examples = [
    "Search patient John",
    "Find patient John Smith",
    "Look up patient Aisha Rahman",
    "Search John Smith",
    "Find headache causes",
    "What causes headache?",
    "hello",
    "Book appointment for Aisha Rahman with cardiology tomorrow at 09:00",
]


for example in examples:
    result = detect_intent(example)
    print(example)
    print(result.model_dump())
    print("-" * 40)