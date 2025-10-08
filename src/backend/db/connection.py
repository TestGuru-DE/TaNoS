from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite für lokalen Start, später PostgreSQL möglich
DATABASE_URL = "sqlite:///./getecade.db"

# Engine erstellen
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Session-Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Basis für alle ORM-Modelle
Base = declarative_base()


def get_db():
    """Erzeugt und liefert eine DB-Session (Dependency für FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
