import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# DATABASE_URL aus der Umgebung – Standard: SQLite-Datei im Projektstamm
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tanos.db")

# Für SQLite braucht's beim Threading diesen Parameter
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
# SQLite: Fremdschlüssel-Cascades aktivieren
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# FastAPI-Dependency: pro Request eine Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

