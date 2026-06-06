"""
SQLAlchemy tool — writes Cease records to SQLite.
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Session
from utils.config import config
from loguru import logger


class Base(DeclarativeBase):
    pass


class CeaseRecord(Base):
    __tablename__ = "cease_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_name = Column(String(256), nullable=False)
    received_at = Column(String(64))
    classification = Column(String(32))
    confidence_score = Column(Float)
    reasoning = Column(Text)
    detected_language = Column(String(16))
    key_phrases = Column(Text)         # JSON-serialised list
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseTool:
    """LangGraph-compatible tool to persist cease records."""

    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL, echo=False)
        Base.metadata.create_all(self.engine)

    def write_cease_record(
        self,
        document_name: str,
        received_at: str,
        classification: str,
        confidence_score: float,
        reasoning: str,
        detected_language: str,
        key_phrases: list[str],
    ) -> int:
        """Inserts a cease record; returns the new row id."""
        import json
        record = CeaseRecord(
            document_name=document_name,
            received_at=received_at,
            classification=classification,
            confidence_score=confidence_score,
            reasoning=reasoning,
            detected_language=detected_language,
            key_phrases=json.dumps(key_phrases),
        )
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(f"DB record created: id={record.id} doc={document_name}")
            return record.id

    def fetch_all_records(self) -> list[dict]:
        """Returns all cease records as list of dicts (for the Streamlit dashboard)."""
        import json
        with Session(self.engine) as session:
            rows = session.query(CeaseRecord).order_by(CeaseRecord.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "document_name": r.document_name,
                    "received_at": r.received_at,
                    "classification": r.classification,
                    "confidence_score": r.confidence_score,
                    "reasoning": r.reasoning,
                    "detected_language": r.detected_language,
                    "key_phrases": json.loads(r.key_phrases or "[]"),
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]