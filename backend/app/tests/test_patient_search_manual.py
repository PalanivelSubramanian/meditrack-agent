from app.db.database import SessionLocal
from app.tools.patient_tools import search_patient_tool


queries = [
    "John Smith",
    "John",
    "Aisha Rahman",
    "P10001",
    "1992",
    "9011",
    "Unknown Person",
]


db = SessionLocal()

try:
    for query in queries:
        result = search_patient_tool(db, query)
        print(f"Query: {query}")
        print(result.model_dump())
        print("-" * 60)
finally:
    db.close()