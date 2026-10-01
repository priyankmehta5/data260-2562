import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv(Path(__file__).with_name(".env"))

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD"),
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    database=os.getenv("MYSQL_DATABASE", "s2562_rel"),
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

db_session_basede26 = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    database = db_session_basede26()

    try:
        yield database
    finally:
        database.close()