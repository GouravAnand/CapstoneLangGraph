"""
Cease agent — handles confirmed 'cease' documents.
Writes record to SQLite datastore.
"""
from loguru import logger
from utils.state import CeaseDesistState
from tools.db_tool import DatabaseTool


class CeaseAgent:
    """LangGraph node: persists cease requests to the database."""

    def __init__(self):
        self.db = DatabaseTool()

    def run(self, state: CeaseDesistState) -> CeaseDesistState:
        logger.info(f"CeaseAgent processing: {state.document_name}")
        try:
            record_id = self.db.write_cease_record(
                document_name=state.document_name,
                received_at=state.received_at,
                classification=state.classification,
                confidence_score=state.confidence_score,
                reasoning=state.classification_reasoning,
                detected_language=state.detected_language,
                key_phrases=state.key_phrases,
            )
            state.db_record_id = record_id
            logger.success(f"Cease record saved. DB id={record_id}")
        except Exception as e:
            logger.error(f"CeaseAgent DB write failed: {e}")
            state.error_message = str(e)
        return state