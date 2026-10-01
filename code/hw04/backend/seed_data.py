import random

from sqlalchemy import text

from .database import db_session_basede26
from .models import Incident, IncidentNote


SEED = 2562
INCIDENT_COUNT = 5000
NOTE_COUNT = 200

INCIDENT_TYPES = [
    "Signal Failure",
    "Bus Delay",
    "Track Maintenance",
    "Station Closure",
    "Power Disruption",
    "Vehicle Breakdown",
    "Service Interruption",
]

LOCATIONS = [
    "Santa Clara",
    "Downtown San Jose",
    "Mountain View",
    "Milpitas",
    "Berryessa",
    "Campbell",
    "Diridon Station",
]

IMPACTS = [
    "minor delays",
    "major delays",
    "temporary rerouting",
    "reduced service",
    "platform congestion",
]


def seed_database():
    random_generator = random.Random(SEED)
    database = db_session_basede26()

    try:
        database.query(IncidentNote).delete()
        database.query(Incident).delete()
        database.commit()

        database.execute(
            text("ALTER TABLE incident_notes AUTO_INCREMENT = 1")
        )
        database.execute(
            text("ALTER TABLE incidents AUTO_INCREMENT = 1")
        )

        incidents = []

        for number in range(1, INCIDENT_COUNT + 1):
            incident_type = random_generator.choice(
                INCIDENT_TYPES
            )
            location = random_generator.choice(LOCATIONS)
            impact = random_generator.choice(IMPACTS)

            incidents.append(
                Incident(
                    title=f"{incident_type} #{number}",
                    description=(
                        f"{incident_type} near {location} caused "
                        f"{impact} for municipal transit passengers."
                    ),
                )
            )

        database.bulk_save_objects(incidents)
        database.commit()

        incident_ids = random_generator.sample(
            range(1, INCIDENT_COUNT + 1),
            NOTE_COUNT,
        )

        notes = [
            IncidentNote(
                incident_id=incident_id,
                note=(
                    f"Operational follow-up recorded for "
                    f"incident {incident_id}."
                ),
            )
            for incident_id in incident_ids
        ]

        database.bulk_save_objects(notes)
        database.commit()

        print(f"SEED: {SEED}")
        print(f"Incidents created: {INCIDENT_COUNT}")
        print(f"Related notes created: {NOTE_COUNT}")
    finally:
        database.close()


if __name__ == "__main__":
    seed_database()