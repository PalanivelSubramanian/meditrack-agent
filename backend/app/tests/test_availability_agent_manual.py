from datetime import date, timedelta

from app.agents.doctor_availability_agent import DoctorAvailabilityAgent
from app.db.database import SessionLocal


db = SessionLocal()

try:
    agent = DoctorAvailabilityAgent()
    tomorrow = date.today() + timedelta(days=1)

    result = agent.find_slots(
        db=db,
        specialization="cardiology",
        target_date=tomorrow,
    )

    print(result)

finally:
    db.close()