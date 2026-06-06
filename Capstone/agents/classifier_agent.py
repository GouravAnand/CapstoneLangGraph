import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from utils.state import CeaseDesistState, SignalAnalysis
from utils.config import config

SYSTEM_PROMPT = """
You are a compliance analyst AI specialising in Cease & Desist requests.

A "Cease & Desist" request is a formal demand from a customer asking an
enterprise to STOP all direct communication (calls, emails, letters, etc.) with them.

Classify the document into EXACTLY ONE of:
  - "cease"      : Clearly a C&D request to stop all communication.
  - "uncertain"  : May be a C&D but is ambiguous, conditional, or incomplete.
  - "irrelevant" : Has nothing to do with a C&D request.

Also evaluate these 7 signals — answer true/false for each:
  1. demands_stop_communication     : Does the document demand all communication stop?
  2. legal_threat_to_cease          : Does it contain a legal threat if communication continues?
  3. requests_engagement_or_dialogue: Does it actively seek further contact or dialogue?
  4. related_to_admin_legal_inquiry : Is it an administrative/procedural/guardianship inquiry?
  5. ambiguous_cease_language       : Does it use cease-adjacent language but with conditions?
  6. multilingual_content           : Is the document in a language other than English?
  7. partial_or_conditional_cease   : Does it request partial/temporary stop rather than full cease?

Respond ONLY with valid JSON — never return null, use "" or [] instead:
{
  "classification": "cease" | "uncertain" | "irrelevant",
  "confidence_score": <float 0.0-1.0>,
  "reasoning": "<1-3 sentence explanation>",
  "key_phrases": ["phrase1", "phrase2"],
  "detected_language": "<ISO 639-1 code>",
  "signal_analysis": {
    "demands_stop_communication": true | false,
    "legal_threat_to_cease": true | false,
    "requests_engagement_or_dialogue": true | false,
    "related_to_admin_legal_inquiry": true | false,
    "ambiguous_cease_language": true | false,
    "multilingual_content": true | false,
    "partial_or_conditional_cease": true | false
  }
}

Signal-based classification logic:
- demands_stop_communication=true AND legal_threat_to_cease=true  → likely "cease"
- requests_engagement_or_dialogue=true                            → lean "irrelevant"
- ambiguous_cease_language=true OR partial_or_conditional_cease=true → lean "uncertain"
- related_to_admin_legal_inquiry=true AND no cease demand          → lean "irrelevant"
- confidence_score < 0.75 with cease signals                      → prefer "uncertain"
"""


def _get_llm():
    if config.LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.LLM_MODEL or "gemini-2.5-flash",
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0,
        )
    elif config.LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=config.LLM_MODEL or "llama-3.3-70b-versatile",
            groq_api_key=config.GROQ_API_KEY,
            temperature=0,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.LLM_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=0,
        )


class ClassifierAgent:
    def __init__(self):
        self.llm = _get_llm()

    def run(self, state: CeaseDesistState) -> CeaseDesistState:
        logger.info(f"Classifying document: {state.document_name}")
        text_snippet = (state.extracted_text or "")[:4000]

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Document text:\n\n{text_snippet}"),
        ]

        try:
            response = self.llm.invoke(messages)
            raw = (response.content or "").strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)
            state.classification = parsed.get("classification") or "uncertain"
            state.confidence_score = float(parsed.get("confidence_score") or 0.0)
            state.classification_reasoning = parsed.get("reasoning") or ""
            state.key_phrases = parsed.get("key_phrases") or []
            state.detected_language = parsed.get("detected_language") or "en"

            # Parse signal analysis
            signals = parsed.get("signal_analysis") or {}
            state.signal_analysis = SignalAnalysis(
                demands_stop_communication=signals.get("demands_stop_communication"),
                legal_threat_to_cease=signals.get("legal_threat_to_cease"),
                requests_engagement_or_dialogue=signals.get("requests_engagement_or_dialogue"),
                related_to_admin_legal_inquiry=signals.get("related_to_admin_legal_inquiry"),
                ambiguous_cease_language=signals.get("ambiguous_cease_language"),
                multilingual_content=signals.get("multilingual_content"),
                partial_or_conditional_cease=signals.get("partial_or_conditional_cease"),
            )

            logger.info(
                f"Classification: {state.classification} "
                f"(confidence={state.confidence_score:.2f})"
            )
        except Exception as e:
            logger.error(f"Classifier LLM error: {e}")
            state.classification = "uncertain"
            state.confidence_score = 0.0
            state.classification_reasoning = "Model call failed; routed to uncertain for safe handling."
            state.key_phrases = []
            state.detected_language = state.detected_language or "en"
            state.signal_analysis = None
            state.error_message = str(e) or "Unknown classifier error"

        return state