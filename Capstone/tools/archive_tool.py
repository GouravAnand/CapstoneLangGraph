"""
Flat-file (CSV) archive tool for Irrelevant documents.
"""
import csv
import os
from datetime import datetime
from utils.config import config
from loguru import logger


class ArchiveTool:
    """Appends irrelevant document records to a CSV archive file."""

    FIELDNAMES = [
        "document_name", "received_at", "classification",
        "confidence_score", "reasoning", "detected_language", "archived_at"
    ]

    def __init__(self):
        self.filepath = config.ARCHIVE_FILE
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        self._ensure_header()

    def _ensure_header(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()

    def archive_record(
        self,
        document_name: str,
        received_at: str,
        classification: str,
        confidence_score: float,
        reasoning: str,
        detected_language: str,
    ) -> str:
        """Appends a row to the CSV and returns the row as a string."""
        row = {
            "document_name": document_name,
            "received_at": received_at,
            "classification": classification,
            "confidence_score": confidence_score,
            "reasoning": reasoning,
            "detected_language": detected_language,
            "archived_at": datetime.utcnow().isoformat(),
        }
        with open(self.filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writerow(row)
        logger.info(f"Archived irrelevant doc: {document_name}")
        return str(row)