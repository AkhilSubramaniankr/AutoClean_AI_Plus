"""Page 3: Review Explanation & Approve.

This is the concrete, interactive form of FR-9: the workflow genuinely
cannot proceed past this page without a human clicking Approve or Reject --
the underlying LangGraph interrupt (Phase 5) is what makes that a real
guarantee, not just a UI convention.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.decision import DecisionType
from autoclean.presentation.components.explanation_panel import render_explanation_panel
from autoclean.presentation.workflow_session import get_workflow_session

st.set_page_config(page_title="Review & Approve — AutoClean AI+", page_icon="✅", layout="wide")
st.title("✅ Review Explanation & Approve")

session = get_workflow_session()
result = st.session_state.get("latest_result")

if result is None:
    st.warning("No dataset has been analyzed yet. Go to **1. Upload & Profile a Dataset** first.")
    st.stop()
assert result is not None  # mypy: st.stop() halts the script, but isn't typed as NoReturn


def _persist_new_audit_entries(current_result: dict[str, Any]) -> None:
    entries = current_result.get("audit_log_entries", [])
    already = st.session_state.get("persisted_audit_count", 0)
    for entry in entries[already:]:
        session.repository.append_audit_event(
            AuditEvent(
                id=entry["id"], experiment_id=st.session_state["experiment_id"], event_type=entry["event_type"],
                actor=entry["actor"], timestamp=datetime.fromisoformat(entry["timestamp"]), payload=entry["payload"],
            )
        )
    st.session_state["persisted_audit_count"] = len(entries)


if result.get("current_node") == "reporting_node":
    st.success(f"Experiment **{st.session_state['experiment_id']}** complete.")
    validation_report = result.get("validation_report")
    if validation_report is not None:
        st.metric("Validation", "PASSED" if validation_report.passed else "FAILED")
        st.caption(validation_report.notes)

    col1, col2, col3 = st.columns(3)
    with open(result["cleaned_dataset_path"], "rb") as f:
        col1.download_button("⬇ Download Cleaned Dataset", f, file_name="cleaned_dataset.csv")
    with open(result["executive_report_path"], "rb") as f:
        col2.download_button("⬇ Download Executive Report", f, file_name="executive_report.md")
    with open(result["reproducible_script_path"], "rb") as f:
        col3.download_button("⬇ Download Reproducible Script", f, file_name="reproduce_cleaning.py")

    with st.expander("View Executive Report"):
        st.markdown(open(result["executive_report_path"]).read())

elif result.get("error"):
    st.error(result["error"])
    st.info("Go back to **1. Upload & Profile a Dataset** to start a new experiment.")

else:
    strategies_by_id = {s.strategy_id: s for s in result["candidate_strategies"]}
    recommended = strategies_by_id[result["recommended_strategy_id"]]

    st.subheader(f"Recommended: {recommended.name}")
    render_explanation_panel(
        result.get("explanation_text", ""), result.get("explanation_consistency_warnings", [])
    )

    decided_by = st.text_input("Your name (for the audit trail)", value="analyst")
    col1, col2 = st.columns(2)

    if col1.button("✅ Approve", type="primary", use_container_width=True):
        session.approve_use_case.execute(
            experiment_id=st.session_state["experiment_id"], strategy_id=recommended.strategy_id,
            decision_type=DecisionType.APPROVED, decided_by=decided_by,
        )
        session.graph.update_state(
            st.session_state["config"], {"human_decision": "approved", "decided_by": decided_by}
        )
        with st.spinner("Executing the approved strategy, validating, and generating your report..."):
            new_result = session.graph.invoke(None, st.session_state["config"])
        st.session_state["latest_result"] = new_result
        result = new_result
        _persist_new_audit_entries(new_result)
        st.rerun()

    if col2.button("❌ Reject", use_container_width=True):
        session.approve_use_case.execute(
            experiment_id=st.session_state["experiment_id"], strategy_id=recommended.strategy_id,
            decision_type=DecisionType.REJECTED, decided_by=decided_by,
        )
        session.graph.update_state(
            st.session_state["config"], {"human_decision": "rejected", "decided_by": decided_by}
        )
        with st.spinner("Finding the next-ranked alternative..."):
            new_result = session.graph.invoke(None, st.session_state["config"])
        st.session_state["latest_result"] = new_result
        _persist_new_audit_entries(new_result)
        st.rerun()
