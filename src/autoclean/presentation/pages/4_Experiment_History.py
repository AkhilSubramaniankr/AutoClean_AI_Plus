"""Page 4: Browse Experiment History (Phase 1, FR-15).

Reads directly from SQLite via SQLiteExperimentRepository -- every
experiment shown here is real, persisted data, including experiments that
were never approved (Page 1 persists as soon as analysis completes).
"""

from __future__ import annotations

import streamlit as st

from autoclean.presentation.workflow_session import get_workflow_session

st.set_page_config(page_title="Experiment History — AutoClean AI+", page_icon="🕘", layout="wide")
st.title("🕘 Experiment History")

session = get_workflow_session()
experiments = session.repository.list_experiments()

if not experiments:
    st.info("No experiments yet. Go to **1. Upload & Profile a Dataset** to start one.")
    st.stop()

experiment_labels = {
    exp.id: f"{exp.dataset_name} — {exp.status.value} — {exp.created_at:%Y-%m-%d %H:%M}" for exp in experiments
}
selected_id = st.selectbox("Select an experiment", options=list(experiment_labels.keys()), format_func=lambda eid: experiment_labels[eid])
selected = next(exp for exp in experiments if exp.id == selected_id)

col1, col2, col3 = st.columns(3)
col1.metric("Status", selected.status.value)
col2.metric("Candidate Strategies", len(selected.candidate_strategies))
col3.metric("Approved Strategy", selected.approved_strategy_id[:8] + "…" if selected.approved_strategy_id else "—")

if selected.dataset_profile is not None:
    st.subheader("Original Dataset Profile")
    profile = selected.dataset_profile
    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    pcol1.metric("Rows", profile.row_count)
    pcol2.metric("Columns", profile.column_count)
    pcol3.metric("Missing %", f"{profile.missing_value_pct:.2f}%")
    pcol4.metric("Duplicates", profile.duplicate_row_count)

if selected.candidate_strategies:
    st.subheader("Candidate Strategies")
    for strategy in selected.candidate_strategies:
        marker = " 🏆" if strategy.strategy_id == selected.approved_strategy_id else ""
        st.markdown(f"- **{strategy.name}**{marker}: {strategy.description}")

st.subheader("Audit Trail")
audit_trail = session.repository.get_audit_trail(selected.id)
if audit_trail:
    for event in audit_trail:
        st.markdown(f"`{event.timestamp:%Y-%m-%d %H:%M:%S}` **{event.event_type}** — _{event.actor}_")
else:
    st.caption("No audit events recorded for this experiment.")
