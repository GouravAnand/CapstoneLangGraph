"""
Structured audit logger — records every decision to a log file.
"""
import json
import os
from datetime import datetime
from utils.config import config
from loguru import logger


class AuditTool:
    """Writes structured audit events for every document processed."""

    def __init__(self):
        os.makedirs(os.path.dirname(config.AUDIT_LOG_FILE) or ".", exist_ok=True)
        # Configure loguru to also write to the audit file
        logger.add(
            config.AUDIT_LOG_FILE,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            rotation="10 MB",
            retention="30 days",
            level="INFO",
        )

    def log_event(
        self,
        document_name: str,
        classification: str,
        confidence_score: float,
        reasoning: str,
        detected_language: str,
        human_decision: str | None = None,
        review_notes: str = "",
        error: str = "",
    ) -> None:
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "document_name": document_name,
            "classification": classification,
            "confidence_score": confidence_score,
            "reasoning": reasoning,
            "detected_language": detected_language,
            "human_decision": human_decision,
            "review_notes": review_notes,
            "error": error,
        }
        logger.info(f"AUDIT | {json.dumps(event)}")