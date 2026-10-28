"""Add HW7 username and role columns to the existing MySQL users table."""
from sqlalchemy import inspect, text
import bcrypt

from .database import db_session_basede26, engine


def migrate():
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as connection:
        if "username" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(100) NULL UNIQUE"))
        if "role" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'reader'"))
        connection.execute(text("UPDATE users SET username = LOWER(email) WHERE username IS NULL"))
        connection.execute(text("UPDATE users SET role = 'reader' WHERE role IS NULL OR role NOT IN ('reader','writer','moderator')"))
        password_hash = bcrypt.hashpw(b"Transit2562!", bcrypt.gensalt()).decode("utf-8")
        for username, role in (("writer@example.com", "writer"), ("moderator@example.com", "moderator")):
            existing = connection.execute(text("SELECT id FROM users WHERE email = :email"), {"email": username}).first()
            if existing is None:
                connection.execute(text("INSERT INTO users (name, username, email, password_hash, role) VALUES (:name, :username, :email, :password_hash, :role)"), {"name": role.title(), "username": username, "email": username, "password_hash": password_hash, "role": role})
            else:
                connection.execute(text("UPDATE users SET username = :username, role = :role WHERE email = :email"), {"username": username, "role": role, "email": username})
    print("HW7 users schema ready: username and role columns verified.")


if __name__ == "__main__":
    migrate()
