"""Redis access counter and MySQL-backed domain/version lookup."""

import re

from sqlalchemy import text

from .hw09_common import PREFIX, event


class IncidentDatabaseWithCache:
    def __init__(self, engine, redis_client):
        self.engine, self.redis_client = engine, redis_client

    def incident(self, incident_id):
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        "SELECT id,title,description,severity,agency_id,view_count,cache_version "
                        "FROM incidents WHERE id=:id"
                    ),
                    {"id": incident_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ValueError("Incident not found")
        return dict(row)

    def increment_incident_views(self, incident_id):
        if isinstance(incident_id, bool) or not isinstance(incident_id, int) or incident_id <= 0:
            raise ValueError("incident_id must be a positive integer")
        key = f"{PREFIX}:views:incident:{incident_id}"
        # Only a cold Redis key needs a database read; SETNX avoids resetting another caller.
        if not self.redis_client.exists(key):
            self.redis_client.setnx(key, self.incident(incident_id)["view_count"])
        count = self.redis_client.incr(key)
        if count % 10 == 0:
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE incidents SET view_count=CASE WHEN view_count<:count THEN :count "
                        "ELSE view_count END WHERE id=:id"
                    ),
                    {"count": count, "id": incident_id},
                )
            event("Synced views to database", incident_id=incident_id, count=count)
        return count

    def context(self, question):
        match = re.search(r"\broute\s+(\d+)\b", question, re.I)
        if not match:
            return {"record": None, "version": "unrelated"}
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        "SELECT i.id,i.title,i.description,i.severity,i.agency_id,i.cache_version, "
                        "a.agency_code AS agency FROM incidents i JOIN transit_agencies a ON a.id=i.agency_id "
                        "WHERE i.incident_code=:code"
                    ),
                    {"code": f"HW9-ROUTE-{match[1]}"},
                )
                .mappings()
                .first()
            )
        if row is None:
            return {"record": None, "version": "unknown-route"}
        row = dict(row)
        row["route"] = int(match[1])
        delay = re.search(r"delay(?: is)? (\d+) minutes", row["description"], re.I)
        if delay:
            row["delay_minutes"] = int(delay[1])
        status = re.search(r"status (\w+)", row["description"], re.I)
        if status:
            row["status"] = status[1].lower()
        return {
            "record": row,
            "version": f"incident-{row['id']}-v{row['cache_version']}",
            "temporal_scope": "Current incident facts only. Historical facts are unavailable.",
        }

    def update_fixture(self, incident_id, severity, description):
        with self.engine.begin() as connection:
            result = connection.execute(
                text(
                    "UPDATE incidents SET severity=:severity, description=:description, "
                    "cache_version=cache_version+1 WHERE id=:id AND incident_code LIKE 'HW9-ROUTE-%'"
                ),
                {"severity": severity, "description": description, "id": incident_id},
            )
            if result.rowcount != 1:
                raise ValueError("Only an HW9 demonstration record may be updated")
        return self.incident(incident_id)
