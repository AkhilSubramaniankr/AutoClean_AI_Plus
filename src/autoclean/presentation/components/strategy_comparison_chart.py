"""strategy_comparison_chart.py: renders a Plotly grouped bar chart
comparing every candidate strategy across all six real objectives.

Design decision: `build_comparison_figure()` returns a plain
`plotly.graph_objects.Figure` rather than calling `st.plotly_chart()`
directly, so it stays a pure, independently unit-testable function (assert
on trace count, labels, values) -- the page itself calls `st.plotly_chart`
on the returned figure. This mirrors the same "keep Streamlit-framework
calls at the page boundary, keep logic testable underneath" principle used
throughout this project's Clean Architecture layers.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

_OBJECTIVE_LABELS = {
    "data_quality_score": "Data Quality",
    "computational_cost_score": "Computational Cost",
    "information_preservation_score": "Information Preservation",
    "statistical_validity_score": "Statistical Validity",
    "fairness_impact_score": "Fairness Impact",
    "downstream_ml_score": "Downstream ML",
}


def build_comparison_figure(
    strategy_names: dict[str, str], strategy_scores: dict[str, dict[str, Any]]
) -> go.Figure:
    """Args:
        strategy_names: strategy_id -> display name.
        strategy_scores: strategy_id -> score dict (EvaluationScore.as_dict()).

    Returns a grouped bar chart: one bar group per objective, one bar per
    strategy within each group -- makes it easy to see, e.g., which
    strategy wins on Information Preservation at a glance.
    """
    fig = go.Figure()
    objective_keys = list(_OBJECTIVE_LABELS.keys())
    objective_display_names = [_OBJECTIVE_LABELS[key] for key in objective_keys]

    for strategy_id, name in strategy_names.items():
        scores = strategy_scores.get(strategy_id, {})
        values = [scores.get(key, 0.0) for key in objective_keys]
        fig.add_trace(go.Bar(name=name, x=objective_display_names, y=values))

    fig.update_layout(
        barmode="group",
        yaxis=dict(title="Score (0.0-1.0, higher is better)", range=[0, 1]),
        xaxis=dict(title="Objective"),
        legend_title_text="Strategy",
        margin=dict(t=30, b=10),
    )
    return fig
