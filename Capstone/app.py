import os
import uuid
import streamlit as st
import pandas as pd
from datetime import datetime

from main import (
    run_pipeline,
    resume_pipeline_after_human,
    export_mermaid_graph,
    export_ascii_graph,
    export_mermaid_png,
)
from tools.db_tool import DatabaseTool
from utils.state import CeaseDesistState
from utils.config import config as app_config

st.set_page_config(
    page_title="Cease & Desist Automation",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "pending_reviews" not in st.session_state:
    st.session_state.pending_reviews = {}
if "processed_docs" not in st.session_state:
    st.session_state.processed_docs = []

with st.sidebar:
    st.title("⚖️ C&D Automation")
    st.caption("Powered by LangGraph + LLM")
    st.divider()
    page = st.radio(
        "Navigation",
        [
            "📄 Upload & Process",
            "🔍 Pending Reviews",
            "📊 Dashboard",
            "📋 Audit Log",
            "🕸️ Graph View",
        ],
        index=0,
    )


def classification_badge(label: str) -> str:
    colors = {"cease": "🔴", "uncertain": "🟡", "irrelevant": "🟢"}
    return f"{colors.get(label, '⚪')} **{label.upper()}**"


def render_signal_table(signal_analysis):
    if not signal_analysis:
        st.info("No signal analysis available.")
        return

    signal_labels = {
        "demands_stop_communication": "Any demand to stop communication?",
        "legal_threat_to_cease": "Any legal threat to cease contact?",
        "requests_engagement_or_dialogue": "Requesting engagement or dialogue?",
        "related_to_admin_legal_inquiry": "Related to admin/legal inquiry?",
        "ambiguous_cease_language": "Ambiguous cease language present?",
        "multilingual_content": "Document in non-English language?",
        "partial_or_conditional_cease": "Partial or conditional cease request?",
    }

    rows = []
    for field, label in signal_labels.items():
        value = getattr(signal_analysis, field, None)
        if value is True:
            indicator = "✅ Yes"
        elif value is False:
            indicator = "❌ No"
        else:
            indicator = "⚪ Unknown"
        rows.append({"Signal": label, "Assessment": indicator})

    df = pd.DataFrame(rows)
    st.table(df)


if page == "📄 Upload & Process":
    st.header("📄 Upload Cease & Desist Document")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        accept_multiple_files=False,
    )

    if uploaded_file:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"📎 Loaded: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")
        with col2:
            process_btn = st.button("🚀 Process Document", type="primary", use_container_width=True)

        if process_btn:
            thread_id = str(uuid.uuid4())
            pdf_bytes = uploaded_file.read()

            with st.spinner("Running AI pipeline…"):
                result: CeaseDesistState = run_pipeline(
                    document_name=uploaded_file.name,
                    document_bytes=pdf_bytes,
                    thread_id=thread_id,
                )

            st.subheader("Classification Result")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Classification", result.classification.upper() if result.classification else "N/A")
            col_b.metric("Confidence Score", f"{result.confidence_score:.0%}")
            col_c.metric("Language Detected", result.detected_language.upper())

            with st.expander("📝 Reasoning & Key Phrases", expanded=True):
                st.write("**Reasoning:**", result.classification_reasoning)
                if result.key_phrases:
                    st.write("**Key Phrases Identified:**")
                    for phrase in result.key_phrases:
                        st.markdown(f"- `{phrase}`")

            with st.expander("🔍 Signal Analysis Breakdown", expanded=True):
                render_signal_table(result.signal_analysis)

            # Always queue uncertain documents for human review
            if result.classification == "uncertain" or result.awaiting_human:
                st.warning("⚠️ This document requires human review.")
                if thread_id not in st.session_state.pending_reviews:
                    st.session_state.pending_reviews[thread_id] = {
                        "thread_id": thread_id,
                        "document_name": uploaded_file.name,
                        "extracted_text": result.extracted_text,
                        "classification": result.classification,
                        "confidence_score": result.confidence_score,
                        "reasoning": result.classification_reasoning,
                        "key_phrases": result.key_phrases,
                        "signal_analysis": result.signal_analysis,
                    }
                st.info("📌 Added to Pending Reviews.")
            elif result.classification == "cease":
                st.success(f"✅ Cease record saved to database (ID: {result.db_record_id})")
            elif result.classification == "irrelevant":
                st.info("📁 Document archived to CSV.")

            st.session_state.processed_docs.append({
                "document": uploaded_file.name,
                "classification": result.classification,
                "confidence": result.confidence_score,
                "language": result.detected_language,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            })


elif page == "🔍 Pending Reviews":
    st.header("🔍 Pending Human Reviews")

    if not st.session_state.pending_reviews:
        st.info("✅ No documents pending human review.")
    else:
        st.caption(f"{len(st.session_state.pending_reviews)} document(s) awaiting review.")
        for tid, doc in list(st.session_state.pending_reviews.items()):
            with st.expander(
                f"📄 {doc['document_name']} (confidence: {doc['confidence_score']:.0%})",
                expanded=True,
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**AI Classification:** {classification_badge(doc['classification'])}")
                    st.write("**AI Reasoning:**", doc["reasoning"])
                    if doc["key_phrases"]:
                        st.write("**Key Phrases:**", ", ".join(doc["key_phrases"]))
                    st.write("**Signal Analysis:**")
                    render_signal_table(doc.get("signal_analysis"))
                    with st.expander("Show extracted document text"):
                        st.text(doc["extracted_text"][:3000])

                with col2:
                    decision = st.selectbox(
                        "Classify as:",
                        ["cease", "irrelevant", "skip"],
                        key=f"decision_{tid}",
                    )
                    notes = st.text_area("Notes (optional)", key=f"notes_{tid}", height=100)
                    submit = st.button("✅ Submit Decision", key=f"submit_{tid}", type="primary")

                    if submit:
                        resume_pipeline_after_human(
                            thread_id=tid,
                            human_decision=decision,
                            human_notes=notes,
                        )
                        del st.session_state.pending_reviews[tid]
                        st.success(f"Decision submitted: **{decision.upper()}**")
                        st.rerun()


elif page == "📊 Dashboard":
    st.header("📊 Cease & Desist Dashboard")
    db = DatabaseTool()
    records = db.fetch_all_records()

    if not records:
        st.info("No cease records in the database yet.")
    else:
        df = pd.DataFrame(records)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Cease Records", len(df))
        col2.metric("Avg Confidence", f"{df['confidence_score'].mean():.0%}")
        col3.metric("Languages", df["detected_language"].nunique())
        col4.metric(
            "Today's Records",
            len(df[df["created_at"].str.startswith(datetime.utcnow().strftime("%Y-%m-%d"))]),
        )

        st.subheader("Recent Cease Records")
        display_cols = ["document_name", "received_at", "confidence_score", "detected_language", "created_at"]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)


elif page == "📋 Audit Log":
    st.header("📋 Audit Log")
    log_path = app_config.AUDIT_LOG_FILE
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            log_lines = f.readlines()
        st.code("".join(reversed(log_lines[-200:])), language="text")
    else:
        st.info("No audit log file found yet.")

    if st.session_state.processed_docs:
        st.subheader("Current Session")
        st.dataframe(
            pd.DataFrame(st.session_state.processed_docs),
            use_container_width=True,
            hide_index=True,
        )


elif page == "🕸️ Graph View":
    st.header("🕸️ LangGraph Flow Visualization")
    st.caption("View the workflow as Mermaid, ASCII, or PNG.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Generate Mermaid", use_container_width=True):
            st.session_state["mermaid_code"] = export_mermaid_graph("graph.mmd")
    with col2:
        if st.button("Generate ASCII", use_container_width=True):
            st.session_state["ascii_graph"] = export_ascii_graph()
    with col3:
        if st.button("Generate PNG", use_container_width=True):
            try:
                st.session_state["png_path"] = export_mermaid_png("graph.png")
            except Exception as e:
                st.error(f"PNG generation failed: {e}")

    if "mermaid_code" in st.session_state:
        st.subheader("Mermaid Source")
        st.code(st.session_state["mermaid_code"], language="mermaid")
        st.download_button(
            "Download Mermaid (.mmd)",
            st.session_state["mermaid_code"],
            "graph.mmd",
            "text/plain",
        )

    if "ascii_graph" in st.session_state:
        st.subheader("ASCII Graph")
        st.code(st.session_state["ascii_graph"], language="text")

    if "png_path" in st.session_state and os.path.exists(st.session_state["png_path"]):
        st.subheader("PNG Graph")
        st.image(
            st.session_state["png_path"],
            caption="LangGraph Mermaid PNG",
            use_container_width=True,
        )
        with open(st.session_state["png_path"], "rb") as f:
            st.download_button("Download PNG", f, "graph.png", "image/png")