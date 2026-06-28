from datetime import date, timedelta

from app.db.database import SessionLocal
from app.tools.scheduling_tools import find_available_slots_tool


db = SessionLocal()

try:
    tomorrow = date.today() + timedelta(days=1)

    result = find_available_slots_tool(
        db=db,
        specialization="cardiology",
        target_date=tomorrow,
        limit=20,
    )

    print(f"Available cardiology slots for {tomorrow}")
    print(result.model_dump())

finally:
    db.close()