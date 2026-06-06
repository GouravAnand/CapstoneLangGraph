from pathlib import Path
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from utils.state import CeaseDesistState
from utils.pdf_extractor import PDFExtractor
from agents.classifier_agent import ClassifierAgent
from agents.reviewer_agent import ReviewerAgent
from agents.cease_agent import CeaseAgent
from agents.archive_agent import ArchiveAgent
from agents.audit_agent import AuditAgent
from agents.human_review_agent import HumanReviewAgent
from loguru import logger

extractor = PDFExtractor()
classifier = ClassifierAgent()
reviewer = ReviewerAgent()
cease_agent = CeaseAgent()
archive_agent = ArchiveAgent()
audit_agent = AuditAgent()
human_agent = HumanReviewAgent()


def node_extract_text(state: CeaseDesistState) -> CeaseDesistState:
    logger.info(f"Extracting text from: {state.document_name}")
    if state.document_bytes:
        state.extracted_text = extractor.extract_text(state.document_bytes) or ""
    else:
        state.error_message = "No document bytes provided"
        state.extracted_text = ""

    # If extraction fails badly, force uncertain for human review
    if len((state.extracted_text or "").strip()) < 20:
        state.classification = "uncertain"
        state.confidence_score = 0.0
        state.classification_reasoning = (
            "Text extraction returned very little content. "
            "Document may be image-based or OCR may be incomplete. "
            "Routing to human review."
        )
        state.awaiting_human = True

    return state


def node_classify(state: CeaseDesistState) -> CeaseDesistState:
    # Skip classifier if already forced to uncertain due to extraction issue
    if state.classification == "uncertain" and state.awaiting_human:
        return state
    return classifier.run(state)


def node_review(state: CeaseDesistState) -> CeaseDesistState:
    return reviewer.run(state)


def node_cease(state: CeaseDesistState) -> CeaseDesistState:
    return cease_agent.run(state)


def node_archive(state: CeaseDesistState) -> CeaseDesistState:
    return archive_agent.run(state)


def node_human_review(state: CeaseDesistState) -> CeaseDesistState:
    return human_agent.run(state)


def node_audit(state: CeaseDesistState) -> CeaseDesistState:
    return audit_agent.run(state)


def route_after_review(state: CeaseDesistState) -> str:
    classification = state.classification
    if classification == "cease":
        return "cease"
    elif classification == "irrelevant":
        return "irrelevant"
    else:
        return "uncertain"


def route_after_human(state: CeaseDesistState) -> str:
    decision = state.human_decision
    if decision == "cease":
        return "cease"
    elif decision == "irrelevant":
        return "irrelevant"
    else:
        return "audit"


def build_graph() -> StateGraph:
    graph = StateGraph(CeaseDesistState)

    graph.add_node("extract_text", node_extract_text)
    graph.add_node("classify", node_classify)
    graph.add_node("review", node_review)
    graph.add_node("cease", node_cease)
    graph.add_node("archive", node_archive)
    graph.add_node("human_review", node_human_review)
    graph.add_node("audit", node_audit)

    graph.set_entry_point("extract_text")
    graph.add_edge("extract_text", "classify")
    graph.add_edge("classify", "review")

    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "cease": "cease",
            "irrelevant": "archive",
            "uncertain": "human_review",
        },
    )

    graph.add_edge("cease", "audit")
    graph.add_edge("archive", "audit")

    graph.add_conditional_edges(
        "human_review",
        route_after_human,
        {
            "cease": "cease",
            "irrelevant": "archive",
            "audit": "audit",
        },
    )

    graph.add_edge("audit", END)
    return graph


def create_compiled_graph():
    memory = MemorySaver()
    graph = build_graph()
    return graph.compile(checkpointer=memory, interrupt_before=["human_review"])


def run_pipeline(document_name: str, document_bytes: bytes, thread_id: str = "default") -> CeaseDesistState:
    app = create_compiled_graph()
    initial_state = CeaseDesistState(
        document_name=document_name,
        document_bytes=document_bytes,
    )
    cfg = {"configurable": {"thread_id": thread_id}}
    final_state = app.invoke(initial_state, config=cfg)
    final = CeaseDesistState(**final_state)

    # Business rule: uncertain must go to manual review
    if final.classification == "uncertain":
        final.awaiting_human = True
        final.review_notes = final.review_notes or "Queued for human review due to uncertain classification."

    return final


def resume_pipeline_after_human(thread_id: str, human_decision: str, human_notes: str = "") -> CeaseDesistState:
    app = create_compiled_graph()
    cfg = {"configurable": {"thread_id": thread_id}}
    current = app.get_state(cfg)
    updated_state = dict(current.values)

    updated_state["human_decision"] = human_decision or None
    updated_state["human_notes"] = human_notes or ""
    updated_state["awaiting_human"] = False

    if human_decision in {"cease", "irrelevant", "uncertain"}:
        updated_state["classification"] = human_decision

    app.update_state(cfg, updated_state)
    final = app.invoke(None, config=cfg)
    return CeaseDesistState(**final)


def export_mermaid_graph(output_file: str = "graph.mmd") -> str:
    app = create_compiled_graph()
    mermaid = app.get_graph().draw_mermaid()
    Path(output_file).write_text(mermaid, encoding="utf-8")
    return mermaid


def export_ascii_graph() -> str:
    app = create_compiled_graph()
    return app.get_graph().draw_ascii()


def export_mermaid_png(output_file: str = "graph.png") -> str:
    app = create_compiled_graph()
    png_bytes = app.get_graph().draw_mermaid_png()
    Path(output_file).write_bytes(png_bytes)
    return output_file