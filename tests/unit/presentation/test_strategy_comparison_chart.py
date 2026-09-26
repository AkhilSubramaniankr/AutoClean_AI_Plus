"""Unit tests for strategy_comparison_chart.py (Phase 9).

build_comparison_figure() is a pure function returning a plotly.graph_objects.Figure
-- tested directly, with no Streamlit runtime needed.
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from autoclean.presentation.components.strategy_comparison_chart import build_comparison_figure

pytestmark = pytest.mark.unit

_SAMPLE_SCORES = {
    "s1": {
        "data_quality_score": 0.8, "computational_cost_score": 0.9, "information_preservation_score": 0.7,
        "statistical_validity_score": 0.85, "fairness_impact_score": 0.5, "downstream_ml_score": 0.6,
    },
    "s2": {
        "data_quality_score": 0.6, "computational_cost_score": 0.95, "information_preservation_score": 0.9,
        "statistical_validity_score": 0.7, "fairness_impact_score": 0.5, "downstream_ml_score": 0.5,
    },
}
_SAMPLE_NAMES = {"s1": "Conservative", "s2": "Baseline"}


class TestBuildComparisonFigure:
    def test_returns_a_plotly_figure(self) -> None:
        fig = build_comparison_figure(_SAMPLE_NAMES, _SAMPLE_SCORES)
        assert isinstance(fig, go.Figure)

    def test_has_one_trace_per_strategy(self) -> None:
        fig = build_comparison_figure(_SAMPLE_NAMES, _SAMPLE_SCORES)
        assert len(fig.data) == len(_SAMPLE_NAMES)

    def test_trace_names_match_strategy_display_names(self) -> None:
        fig = build_comparison_figure(_SAMPLE_NAMES, _SAMPLE_SCORES)
        trace_names = {trace.name for trace in fig.data}
        assert trace_names == {"Conservative", "Baseline"}

    def test_each_trace_has_six_objective_values(self) -> None:
        fig = build_comparison_figure(_SAMPLE_NAMES, _SAMPLE_SCORES)
        for trace in fig.data:
            assert len(trace.y) == 6

    def test_real_score_values_appear_in_the_figure_not_placeholders(self) -> None:
        fig = build_comparison_figure(_SAMPLE_NAMES, _SAMPLE_SCORES)
        s1_trace = next(trace for trace in fig.data if trace.name == "Conservative")
        assert 0.8 in s1_trace.y  # the real data_quality_score for s1

    def test_missing_score_key_defaults_to_zero_not_a_crash(self) -> None:
        incomplete_scores = {"s1": {"data_quality_score": 0.8}}  # missing the other 5 keys
        fig = build_comparison_figure({"s1": "Only"}, incomplete_scores)
        assert len(fig.data) == 1
        assert list(fig.data[0].y).count(0.0) == 5

    def test_empty_strategy_set_produces_an_empty_figure_not_a_crash(self) -> None:
        fig = build_comparison_figure({}, {})
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0
