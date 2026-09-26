"""Page 1: Upload & Profile a Dataset.

Runs the workflow up to (and including) the human-approval interrupt in
one shot: Analysis -> Evaluation -> Decision/Explanation, then pauses.
Results are stashed in `st.session_state` for pages 2 and 3, and the
experiment/candidate strategies/scores are persisted immediately (matching
scripts/run_workflow_cli.py's behavior) so the experiment shows up in
Experiment History even if the analyst never gets to approving it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import streamlit as st

from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.entities.experiment import Experiment, ExperimentStatus
from autoclean.presentation.workflow_session import get_workflow_session

st.set_page_config(page_title="Upload & Profile — AutoClean AI+", page_icon="📤", layout="wide")
st.title("📤 Upload & Profile a Dataset")

session = get_workflow_session()

uploaded_file = st.file_uploader("Choose a CSV, XLSX, or Parquet file", type=["csv", "xlsx", "parquet"])

if uploaded_file is not None:
    file_path = session.upload_dir / f"{uuid.uuid4()}_{uploaded_file.name}"
    file_path.write_bytes(uploaded_file.getvalue())
    st.success(f"Uploaded: {uploaded_file.name} ({len(uploaded_file.getvalue()):,} bytes)")

    if st.button("Analyze Dataset", type="primary"):
        experiment_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": experiment_id}}

        with st.spinner("Profiling dataset, generating strategies, scoring, and preparing an explanation..."):
            result = session.graph.invoke(
                {"experiment_id": experiment_id, "dataset_path": str(file_path)}, config
            )

        experiment = Experiment(
            id=experiment_id, dataset_name=uploaded_file.name, dataset_hash=str(hash(str(file_path))),
            status=ExperimentStatus.AWAITING_APPROVAL, dataset_profile=result["dataset_profile"],
            candidate_strategies=result["candidate_strategies"],
        )
        session.repository.save_experiment(experiment)
        session.repository.save_candidate_strategies(experiment_id, result["candidate_strategies"])
        for strategy_id, score_dict in result["strategy_scores"].items():
            score = EvaluationScore(**score_dict)
            session.repository.save_strategy_score(
                strategy_id, score, score.compute_weighted_total(session.weights),
                {
                    "data_quality": session.weights.data_quality,
                    "computational_cost": session.weights.computational_cost,
                    "information_preservation": session.weights.information_preservation,
                    "statistical_validity": session.weights.statistical_validity,
                    "fairness_impact": session.weights.fairness_impact,
                    "downstream_ml": session.weights.downstream_ml,
                },
            )
        persisted_count = 0
        for entry in result.get("audit_log_entries", []):
            session.repository.append_audit_event(
                AuditEvent(
                    id=entry["id"], experiment_id=experiment_id, event_type=entry["event_type"],
                    actor=entry["actor"], timestamp=datetime.fromisoformat(entry["timestamp"]),
                    payload=entry["payload"],
                )
            )
            persisted_count += 1

        st.session_state["experiment_id"] = experiment_id
        st.session_state["config"] = config
        st.session_state["dataset_path"] = str(file_path)
        st.session_state["dataset_name"] = uploaded_file.name
        st.session_state["latest_result"] = result
        st.session_state["persisted_audit_count"] = persisted_count

        st.rerun()

if st.session_state.get("latest_result") and st.session_state.get("dataset_name"):
    result = st.session_state["latest_result"]
    profile = result["dataset_profile"]

    st.subheader(f"Profile: {st.session_state['dataset_name']}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", profile.row_count)
    col2.metric("Columns", profile.column_count)
    col3.metric("Missing %", f"{profile.missing_value_pct:.2f}%")
    col4.metric("Duplicate Rows", profile.duplicate_row_count)

    st.subheader(f"Detected Issues ({len(result['detected_issues'])})")
    if result["detected_issues"]:
        for issue in result["detected_issues"]:
            st.markdown(f"- **{issue.issue_type.value}**{f' (`{issue.column}`)' if issue.column else ''}: {issue.description}")
    else:
        st.info("No data-quality issues detected.")

    st.success(
        f"Generated {len(result['candidate_strategies'])} candidate strategies. "
        "Continue to **2. Compare Candidate Strategies**."
    )
