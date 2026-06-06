"""
Audit agent — always runs last; logs full decision trail.
"""
from loguru import logger
from utils.state import CeaseDesistState
from tools.audit_tool import AuditTool


class AuditAgent:
    """LangGraph node: writes a structured audit entry for every document."""

    def __init__(self):
        self.audit = AuditTool()

    def run(self, state: CeaseDesistState) -> CeaseDesistState:
        logger.info(f"AuditAgent logging: {state.document_name}")
        self.audit.log_event(
            document_name=state.document_name,
            classification=state.human_decision or state.classification or "unknown",
            confidence_score=state.confidence_score,
            reasoning=state.classification_reasoning,
            detected_language=state.detected_language,
            human_decision=state.human_decision,
            review_notes=state.review_notes,
            error=state.error_message,
        )
        state.audit_logged = True
        return state