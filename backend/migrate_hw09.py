"""Additive migration; preserves legacy rows and creates four clearly labeled demo incidents."""

from sqlalchemy import inspect, text

from .database import engine
from .hw09_common import event


def migrate():
    columns = {column["name"] for column in inspect(engine).get_columns("incidents")}
    with engine.begin() as connection:
        for name in ("view_count", "cache_version"):
            if name not in columns:
                connection.execute(text(f"ALTER TABLE incidents ADD COLUMN {name} INT NOT NULL DEFAULT 0"))
        agency = connection.execute(text("SELECT id FROM transit_agencies ORDER BY id LIMIT 1")).scalar_one()
        for route, severity, delay in [(2, 3, 12), (3, 4, 25), (4, 2, 8), (5, 1, 4)]:
            code = f"HW9-ROUTE-{route}"
            if not connection.execute(
                text("SELECT id FROM incidents WHERE incident_code=:code"), {"code": code}
            ).first():
                connection.execute(
                    text(
                        "INSERT INTO incidents (title,description,incident_code,severity,agency_id) "
                        "VALUES (:title,:description,:code,:severity,:agency)"
                    ),
                    {
                        "title": f"HW9 demo Route {route} signal delay",
                        "description": f"Synthetic HW9 exercise: Route {route} delay is {delay} minutes; status open.",
                        "code": code,
                        "severity": severity,
                        "agency": agency,
                    },
                )
        count = connection.execute(text("SELECT COUNT(*) FROM incidents")).scalar_one()
    event("HW9 migration complete", total_incidents=count, new_columns=["view_count", "cache_version"])


if __name__ == "__main__":
    migrate()
