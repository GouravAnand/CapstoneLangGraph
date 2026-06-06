"""
Archive agent — handles 'irrelevant' documents.
Writes to flat CSV file.
"""
from loguru import logger
from utils.state import CeaseDesistState
from tools.archive_tool import ArchiveTool


class ArchiveAgent:
    """LangGraph node: archives irrelevant documents to CSV."""

    def __init__(self):
        self.archive = ArchiveTool()

    def run(self, state: CeaseDesistState) -> CeaseDesistState:
        logger.info(f"ArchiveAgent processing: {state.document_name}")
        try:
            row_str = self.archive.archive_record(
                document_name=state.document_name,
                received_at=state.received_at,
                classification=state.classification,
                confidence_score=state.confidence_score,
                reasoning=state.classification_reasoning,
                detected_language=state.detected_language,
            )
            state.archive_row = row_str
            logger.success(f"Archived: {state.document_name}")
        except Exception as e:
            logger.error(f"ArchiveAgent error: {e}")
            state.error_message = str(e)
        return state