from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Project root is two levels above this file: backend/app -> backend -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
(_PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{_PROJECT_ROOT / 'data' / 'app.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
