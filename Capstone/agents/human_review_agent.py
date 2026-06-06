from loguru import logger
from utils.state import CeaseDesistState


class HumanReviewAgent:
    """
    Human-in-the-loop agent.
    Marks state as awaiting human review.
    """

    def run(self, state: CeaseDesistState) -> CeaseDesistState:
        logger.info(
            f"HumanReviewAgent: document '{state.document_name}' "
            f"requires human review."
        )
        state.awaiting_human = True
        state.review_notes = state.review_notes or "Awaiting human review."
        return state

    def apply_human_decision(
        self,
        state: CeaseDesistState,
        decision: str,
        notes: str = "",
    ) -> CeaseDesistState:
        state.human_decision = decision
        state.classification = decision
        state.human_notes = notes or ""
        state.awaiting_human = False
        logger.info(f"Human decided: {decision} — notes: {notes}")
        return state