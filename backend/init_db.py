import bcrypt

from .database import Base, db_session_basede26, engine
from .models import User


DEFAULT_EMAIL = "student@example.com"
DEFAULT_PASSWORD = "Transit2562!"


def initialize_database():
    Base.metadata.create_all(bind=engine)

    database = db_session_basede26()

    try:
        existing_user = (
            database.query(User)
            .filter(User.email == DEFAULT_EMAIL)
            .first()
        )

        if existing_user is None:
            password_hash = bcrypt.hashpw(
                DEFAULT_PASSWORD.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")

            database.add(
                User(
                    name="HW4 Student",
                    email=DEFAULT_EMAIL,
                    password_hash=password_hash,
                )
            )
            database.commit()
            print("Created default login user.")
        else:
            print("Default login user already exists.")

        print("Database tables are ready.")
    finally:
        database.close()


if __name__ == "__main__":
    initialize_database()