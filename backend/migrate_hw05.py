from sqlalchemy import inspect, text

from .database import engine
from .models import TransitAgency


def column_names(table_name):
    return {
        column["name"]
        for column in inspect(engine).get_columns(table_name)
    }


def index_names(table_name):
    inspector = inspect(engine)

    names = {
        index["name"]
        for index in inspector.get_indexes(table_name)
    }

    names.update(
        constraint["name"]
        for constraint in inspector.get_unique_constraints(
            table_name
        )
        if constraint.get("name")
    )

    return names


def foreign_key_names(table_name):
    return {
        foreign_key["name"]
        for foreign_key in inspect(engine).get_foreign_keys(
            table_name
        )
        if foreign_key.get("name")
    }


def main():
    TransitAgency.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    columns = column_names("incidents")

    with engine.begin() as connection:
        if "incident_code" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE incidents "
                    "ADD COLUMN incident_code VARCHAR(30) NULL"
                )
            )

        if "severity" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE incidents "
                    "ADD COLUMN severity INT NOT NULL DEFAULT 1"
                )
            )

        if "agency_id" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE incidents "
                    "ADD COLUMN agency_id INT NULL"
                )
            )

        if "created_at" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE incidents "
                    "ADD COLUMN created_at DATETIME "
                    "NOT NULL DEFAULT CURRENT_TIMESTAMP"
                )
            )

        if "updated_at" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE incidents "
                    "ADD COLUMN updated_at DATETIME "
                    "NOT NULL DEFAULT CURRENT_TIMESTAMP "
                    "ON UPDATE CURRENT_TIMESTAMP"
                )
            )

        connection.execute(
            text(
                """
                INSERT INTO transit_agencies
                    (
                        name,
                        jurisdiction,
                        agency_code,
                        created_at,
                        updated_at
                    )
                SELECT
                    'Valley Transportation Authority',
                    'Santa Clara County',
                    'VTA',
                    NOW(),
                    NOW()
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM transit_agencies
                    WHERE agency_code = 'VTA'
                )
                """
            )
        )

        agency_id = connection.execute(
            text(
                """
                SELECT id
                FROM transit_agencies
                WHERE agency_code = 'VTA'
                """
            )
        ).scalar_one()

        connection.execute(
            text(
                """
                UPDATE incidents
                SET incident_code = CONCAT(
                    'INC-',
                    LPAD(id, 6, '0')
                )
                WHERE incident_code IS NULL
                   OR incident_code = ''
                """
            )
        )

        connection.execute(
            text(
                """
                UPDATE incidents
                SET agency_id = :agency_id
                WHERE agency_id IS NULL
                """
            ),
            {"agency_id": agency_id},
        )

        connection.execute(
            text(
                """
                ALTER TABLE incidents
                MODIFY incident_code VARCHAR(30) NOT NULL,
                MODIFY agency_id INT NOT NULL
                """
            )
        )

    indexes = index_names("incidents")

    with engine.begin() as connection:
        if "uq_incidents_incident_code" not in indexes:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX "
                    "uq_incidents_incident_code "
                    "ON incidents (incident_code)"
                )
            )

        if "ix_incidents_agency_id" not in indexes:
            connection.execute(
                text(
                    "CREATE INDEX ix_incidents_agency_id "
                    "ON incidents (agency_id)"
                )
            )

    foreign_keys = foreign_key_names("incidents")

    if "fk_incidents_agency" not in foreign_keys:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    ALTER TABLE incidents
                    ADD CONSTRAINT fk_incidents_agency
                    FOREIGN KEY (agency_id)
                    REFERENCES transit_agencies(id)
                    ON DELETE RESTRICT
                    """
                )
            )

    with engine.connect() as connection:
        agency_count = connection.execute(
            text("SELECT COUNT(*) FROM transit_agencies")
        ).scalar_one()

        incident_count = connection.execute(
            text("SELECT COUNT(*) FROM incidents")
        ).scalar_one()

        incomplete_count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM incidents
                WHERE incident_code IS NULL
                   OR agency_id IS NULL
                """
            )
        ).scalar_one()

    print("HW5 database migration completed")
    print(f"Transit agencies: {agency_count}")
    print(f"Incidents preserved: {incident_count}")
    print(f"Incomplete incidents: {incomplete_count}")


if __name__ == "__main__":
    main()