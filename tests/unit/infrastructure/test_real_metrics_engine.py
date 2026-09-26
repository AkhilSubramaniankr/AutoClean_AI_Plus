"""Unit tests for RealMetricsEngine (Phase 6) -- the batch orchestrator
tying together StrategyExecutor, the six metric modules, and the EM
estimator. Uses the shared `messy_dataframe` fixture (conftest.py) plus
generated candidate strategies, mirroring how EvaluateStrategiesUseCase
actually calls this engine in production.
"""

from __future__ import annotations

import pandas as pd
import pytest

from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
from autoclean.infrastructure.data_processing.strategy_generator import StrategyGenerator
from autoclean.infrastructure.metrics.real_metrics_engine import RealMetricsEngine

pytestmark = pytest.mark.unit


def _candidate_strategies(df: pd.DataFrame):
    profile = DatasetProfiler().profile(df)
    issues = IssueDetector().detect(df, profile)
    strategies = StrategyGenerator().generate(issues)
    return strategies, profile


class TestRealMetricsEngine:
    def test_scores_every_strategy_in_the_batch(self, messy_dataframe: pd.DataFrame) -> None:
        strategies, profile = _candidate_strategies(messy_dataframe)
        scores = RealMetricsEngine().score_all(strategies, messy_dataframe, profile)
        assert set(scores.keys()) == {s.strategy_id for s in strategies}

    def test_all_score_values_are_plain_python_floats_in_range(self, messy_dataframe: pd.DataFrame) -> None:
        """Regression test for the numpy.float64/msgpack serialization bug
        found while running scripts/run_workflow_cli.py -- every value in
        every EvaluationScore must be a genuine Python float.
        """
        strategies, profile = _candidate_strategies(messy_dataframe)
        scores = RealMetricsEngine().score_all(strategies, messy_dataframe, profile)
        for score in scores.values():
            for value in score.as_dict().values():
                assert type(value) is float  # noqa: E721
                assert 0.0 <= value <= 1.0

    def test_does_not_mutate_the_input_dataframe(self, messy_dataframe: pd.DataFrame) -> None:
        strategies, profile = _candidate_strategies(messy_dataframe)
        original_copy = messy_dataframe.copy()
        RealMetricsEngine().score_all(strategies, messy_dataframe, profile)
        pd.testing.assert_frame_equal(messy_dataframe, original_copy)

    def test_conservative_preserves_more_information_than_aggressive(
        self, messy_dataframe: pd.DataFrame
    ) -> None:
        """A meaningful, directionally-checkable assertion (not just 'it ran
        without crashing'): the Conservative strategy (impute + clip) should
        score higher on information preservation than Aggressive (drop + remove),
        because Aggressive removes rows and Conservative does not.
        """
        strategies, profile = _candidate_strategies(messy_dataframe)
        scores = RealMetricsEngine().score_all(strategies, messy_dataframe, profile)
        strategies_by_name = {s.name: s for s in strategies}

        conservative = strategies_by_name.get("Conservative (impute + clip)")
        aggressive = strategies_by_name.get("Aggressive (drop + remove)")
        assert conservative is not None and aggressive is not None

        conservative_score = scores[conservative.strategy_id].information_preservation_score
        aggressive_score = scores[aggressive.strategy_id].information_preservation_score
        assert conservative_score > aggressive_score

    def test_explicit_sensitive_and_target_column_overrides_are_respected(
        self, messy_dataframe: pd.DataFrame
    ) -> None:
        strategies, profile = _candidate_strategies(messy_dataframe)
        engine = RealMetricsEngine(sensitive_column="city", target_column="city")
        scores = engine.score_all(strategies, messy_dataframe, profile)
        # Should run without error and produce valid scores using the override.
        for score in scores.values():
            assert 0.0 <= score.fairness_impact_score <= 1.0
