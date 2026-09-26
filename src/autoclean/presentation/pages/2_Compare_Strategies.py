"""Page 2: Compare Candidate Strategies.

Shows every candidate strategy's real six-objective scores (Phase 6) in a
table plus a Plotly comparison chart (Phase 9 component).
"""

from __future__ import annotations

import streamlit as st

from autoclean.presentation.components.strategy_comparison_chart import build_comparison_figure

st.set_page_config(page_title="Compare Strategies — AutoClean AI+", page_icon="📊", layout="wide")
st.title("📊 Compare Candidate Strategies")

result = st.session_state.get("latest_result")
if result is None:
    st.warning("No dataset has been analyzed yet. Go to **1. Upload & Profile a Dataset** first.")
    st.stop()

strategies = result["candidate_strategies"]
scores = result["strategy_scores"]
ranked_ids = result["ranked_strategy_ids"]
strategy_names = {s.strategy_id: s.name for s in strategies}
strategies_by_id = {s.strategy_id: s for s in strategies}

st.subheader("Scores by Objective")
fig = build_comparison_figure(strategy_names, scores)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Ranking")
for rank, strategy_id in enumerate(ranked_ids, start=1):
    strategy = strategies_by_id[strategy_id]
    score = scores[strategy_id]
    is_top = rank == 1
    with st.container(border=True):
        st.markdown(f"**#{rank}. {strategy.name}**" + (" 🏆 *Recommended*" if is_top else ""))
        st.caption(strategy.description)
        cols = st.columns(6)
        labels = [
            ("Quality", "data_quality_score"), ("Cost", "computational_cost_score"),
            ("Info. Preservation", "information_preservation_score"),
            ("Statistical Validity", "statistical_validity_score"),
            ("Fairness", "fairness_impact_score"), ("Downstream ML", "downstream_ml_score"),
        ]
        for col, (label, key) in zip(cols, labels, strict=True):
            col.metric(label, f"{score[key]:.2f}")

st.success("Continue to **3. Review Explanation & Approve** to review the top-ranked recommendation.")
