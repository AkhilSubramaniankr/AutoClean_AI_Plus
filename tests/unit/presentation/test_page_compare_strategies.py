"""Headless tests for Page 2 (Compare Candidate Strategies), using AppTest
with real Phase 4/6 engine output seeded into session_state (this page has
no dependency on get_workflow_session at all, so no mocking is needed).
"""

from __future__ import annotations

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
from autoclean.infrastructure.data_processing.strategy_generator import StrategyGenerator
from autoclean.infrastructure.metrics.placeholder_metrics_engine import PlaceholderMetricsEngine

pytestmark = pytest.mark.unit

_PAGE_PATH = "src/autoclean/presentation/pages/2_Compare_Strategies.py"
_TIMEOUT = 30


def _real_result() -> dict:
    df = pd.DataFrame({"age": [25, 30, None, 40, 200], "city": ["NY", "LA", "NY", "SF", "NY"]})
    profile = DatasetProfiler().profile(df)
    issues = IssueDetector().detect(df, profile)
    strategies = StrategyGenerator().generate(issues)
    scores = {s.strategy_id: PlaceholderMetricsEngine().score(s, profile).as_dict() for s in strategies}
    ranked_ids = sorted(scores, key=lambda sid: sum(scores[sid].values()), reverse=True)
    return {"candidate_strategies": strategies, "strategy_scores": scores, "ranked_strategy_ids": ranked_ids}


class TestCompareStrategiesPage:
    def test_shows_warning_when_nothing_analyzed_yet(self) -> None:
        at = AppTest.from_file(_PAGE_PATH)
        at.run(timeout=_TIMEOUT)
        assert not at.exception
        assert any("analyzed yet" in w.value for w in at.warning)

    def test_renders_a_plotly_chart_for_real_results(self) -> None:
        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["latest_result"] = _real_result()
        at.run(timeout=_TIMEOUT)
        assert not at.exception
        assert len(at.get("plotly_chart")) == 1

    def test_top_ranked_strategy_is_marked_recommended(self) -> None:
        result = _real_result()
        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["latest_result"] = result
        at.run(timeout=_TIMEOUT)
        assert not at.exception
        assert any("Recommended" in m.value for m in at.markdown)

    def test_all_candidate_strategies_are_listed(self) -> None:
        result = _real_result()
        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["latest_result"] = result
        at.run(timeout=_TIMEOUT)
        rendered_text = " ".join(m.value for m in at.markdown)
        for strategy in result["candidate_strategies"]:
            assert strategy.name in rendered_text
