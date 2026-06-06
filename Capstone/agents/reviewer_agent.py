"""
Optional judge/reviewer agent — validates the classifier's output.
Checks for edge cases, low confidence, or contradictory signals.
"""
import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from utils.state import CeaseDesistState
from agents.classifier_agent import _get_llm
from utils.config import config


REVIEWER_PROMPT = """
You are a senior compliance reviewer. A junior AI has classified a document.
Your job: verify that the classification is correct and flag any concerns.

Respond ONLY with valid JSON:
{
  "review_passed": true | false,
  "review_notes": "<explanation — required if review_passed is false>"
}

Override the classification to "uncertain" by returning review_passed=false if:
  - The confidence score is below 0.75 AND classification is "cease"
  - The text contains contradictory signals (both requesting and NOT requesting cessation)
  - The document appears to be in a language the classifier may not have handled well
  - Key phrases listed do not actually appear in the text
"""


class ReviewerAgent:
    """LangGraph node: judges the classifier's output."""

    def __init__(self):
        self.llm = _get_llm()

    def run(self, state: CeaseDesistState) -> CeaseDesistState:
        logger.info("Reviewer agent running")
        payload = {
            "classification": state.classification,
            "confidence_score": state.confidence_score,
            "reasoning": state.classification_reasoning,
            "key_phrases": state.key_phrases,
            "text_snippet": state.extracted_text[:2000],
        }
        messages = [
            SystemMessage(content=REVIEWER_PROMPT),
            HumanMessage(content=json.dumps(payload, indent=2)),
        ]
        try:
            response = self.llm.invoke(messages)
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)
            state.review_passed = parsed.get("review_passed", True)
            state.review_notes = parsed.get("review_notes", "")

            if not state.review_passed:
                logger.warning(
                    f"Reviewer overrode to 'uncertain': {state.review_notes}"
                )
                state.classification = "uncertain"
        except Exception as e:
            logger.error(f"Reviewer agent error: {e}")
            state.review_passed = True  # fail-open: let classifier decision stand

        return state