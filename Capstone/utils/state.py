from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

ClassificationResult = Literal["cease", "uncertain", "irrelevant"]


class SignalAnalysis(BaseModel):
    """Structured signal checks used to explain the classification decision."""
    demands_stop_communication: Optional[bool] = None
    legal_threat_to_cease: Optional[bool] = None
    requests_engagement_or_dialogue: Optional[bool] = None
    related_to_admin_legal_inquiry: Optional[bool] = None
    ambiguous_cease_language: Optional[bool] = None
    multilingual_content: Optional[bool] = None
    partial_or_conditional_cease: Optional[bool] = None


class CeaseDesistState(BaseModel):
    document_name: str = ""
    document_bytes: Optional[bytes] = None
    received_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    extracted_text: str = ""
    detected_language: str = "en"

    classification: Optional[ClassificationResult] = None
    confidence_score: float = 0.0
    classification_reasoning: str = ""
    key_phrases: list[str] = Field(default_factory=list)

    # Signal analysis breakdown
    signal_analysis: Optional[SignalAnalysis] = None

    review_passed: bool = False
    review_notes: str = ""

    human_decision: Optional[ClassificationResult] = None
    human_notes: str = ""
    awaiting_human: bool = False

    db_record_id: Optional[int] = None
    archive_row: Optional[str] = None
    audit_logged: bool = False
    error_message: str = ""

    @field_validator(
        "document_name", "received_at", "extracted_text", "detected_language",
        "classification_reasoning", "review_notes", "human_notes", "error_message",
        mode="before",
    )
    @classmethod
    def none_to_empty_string(cls, value):
        return "" if value is None else value

    @field_validator("key_phrases", mode="before")
    @classmethod
    def none_to_empty_list(cls, value):
        return [] if value is None else value

    @field_validator("confidence_score", mode="before")
    @classmethod
    def normalize_confidence(cls, value):
        if value in (None, ""):
            return 0.0
        try:
            return float(value)
        except Exception:
            return 0.0

    class Config:
        arbitrary_types_allowed = True