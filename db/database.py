# db/database.py
# SQLAlchemy ORM - supports both SQLite (local) and PostgreSQL (Render)

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config import settings
import os

# ---- Fix for Render PostgreSQL URL ----
# Render provides postgres:// but SQLAlchemy requires postgresql://
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ---- SQLAlchemy Engine ----
# SQLite needs check_same_thread=False, PostgreSQL doesn't need it
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---- ORM Model ----
class QAResult(Base):
    __tablename__ = "qa_results"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String, index=True)
    workflow_name = Column(String)
    url = Column(String)
    goal = Column(Text)
    status = Column(String)          # PASSED / FAILED / ERROR
    agent_output = Column(Text)
    steps = Column(Text)             # JSON string
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---- Create tables on startup ----
def init_db():
    Base.metadata.create_all(bind=engine)


# ---- Dependency: get DB session ----
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- CRUD Operations ----
def create_qa_result(
    db,
    workflow_name: str,
    url: str,
    goal: str,
    status: str,
    agent_output: str,
    steps: str,
    duration_seconds: float = 0.0,
    workflow_id: str = ""
):
    """Save a QA run result to the database."""
    record = QAResult(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        url=url,
        goal=goal,
        status=status,
        agent_output=agent_output,
        steps=steps,
        duration_seconds=duration_seconds,
        created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_all_results(db, limit: int = 50):
    """Fetch last N QA results ordered by most recent."""
    return db.query(QAResult).order_by(QAResult.id.desc()).limit(limit).all()


def get_results_by_status(db, status: str):
    """Fetch results filtered by status (PASSED/FAILED/ERROR)."""
    return db.query(QAResult).filter(QAResult.status == status).order_by(QAResult.id.desc()).all()


# Auto-initialize tables when module is imported
init_db()
