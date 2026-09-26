"""Unit tests for the Phase 5 TEMPORARY placeholder implementations:
PlaceholderMetricsEngine and TemplateLLMClient. These tests exist to lock
down the *interim* behavior (so Phase 6/7's replacements have a clear
before/after to diff against), not to validate real evaluation quality.
"""

from __future__ import annotations

import pytest

from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.infrastructure.llm.template_llm_client import TemplateLLMClient
from autoclean.infrastructure.metrics.placeholder_metrics_engine import PlaceholderMetricsEngine

pytestmark = pytest.mark.unit


class TestPlaceholderMetricsEngine:
    def _profile(self, **overrides) -> DatasetProfile:
        defaults = dict(
            row_count=100, column_count=5, missing_value_pct=10.0,
            duplicate_row_count=2, outlier_count=3,
            dtype_issue_columns={"income": "looks numeric"},
        )
        defaults.update(overrides)
        return DatasetProfile(**defaults)

    def test_scores_are_within_valid_range(self) -> None:
        strategy = CleaningStrategy(
            strategy_id="s1", name="Test",
            steps=(CleaningStep(operation=CleaningOperation.MEDIAN_IMPUTATION, target_column="age"),),
        )
        score = PlaceholderMetricsEngine().score(strategy, self._profile())
        for value in score.as_dict().values():
            assert 0.0 <= value <= 1.0

    def test_placeholder_objectives_are_fixed_at_neutral_value(self) -> None:
        strategy = CleaningStrategy(
            strategy_id="s1", name="Test", steps=(CleaningStep(operation=CleaningOperation.NO_OP),)
        )
        score = PlaceholderMetricsEngine().score(strategy, self._profile())
        assert score.information_preservation_score == 0.5
        assert score.statistical_validity_score == 0.5
        assert score.fairness_impact_score == 0.5
        assert score.downstream_ml_score == 0.5

    def test_no_op_strategy_scores_lower_quality_than_intervening_strategy(self) -> None:
        no_op = CleaningStrategy(
            strategy_id="s1", name="No-op", steps=(CleaningStep(operation=CleaningOperation.NO_OP),)
        )
        intervening = CleaningStrategy(
            strategy_id="s2", name="Intervening",
            steps=(CleaningStep(operation=CleaningOperation.MEDIAN_IMPUTATION, target_column="age"),),
        )
        profile = self._profile()
        engine = PlaceholderMetricsEngine()
        assert engine.score(no_op, profile).data_quality_score < engine.score(intervening, profile).data_quality_score

    def test_row_removing_strategy_scores_lower_cost_than_clipping_strategy(self) -> None:
        removal = CleaningStrategy(
            strategy_id="s1", name="Removal",
            steps=(CleaningStep(operation=CleaningOperation.IQR_OUTLIER_REMOVAL, target_column="age"),),
        )
        clipping = CleaningStrategy(
            strategy_id="s2", name="Clipping",
            steps=(CleaningStep(operation=CleaningOperation.IQR_OUTLIER_CLIPPING, target_column="age"),),
        )
        profile = self._profile()
        engine = PlaceholderMetricsEngine()
        assert engine.score(removal, profile).computational_cost_score < engine.score(clipping, profile).computational_cost_score


class TestTemplateLLMClient:
    def test_explanation_contains_only_numbers_from_context(self) -> None:
        context = {
            "recommended_strategy_name": "Conservative",
            "recommended_strategy_description": "Imputes and clips.",
            "recommended_score": {
                "data_quality_score": 0.83, "computational_cost_score": 0.71,
                "information_preservation_score": 0.5, "statistical_validity_score": 0.5,
                "fairness_impact_score": 0.5, "downstream_ml_score": 0.5, "em_confidence": 0.0,
            },
            "alternatives": [],
        }
        explanation = TemplateLLMClient().explain(context)
        assert "Conservative" in explanation
        assert "0.83" in explanation
        assert "0.71" in explanation

    def test_explanation_lists_alternatives_when_present(self) -> None:
        base_score = {
            "data_quality_score": 0.5, "computational_cost_score": 0.5,
            "information_preservation_score": 0.5, "statistical_validity_score": 0.5,
            "fairness_impact_score": 0.5, "downstream_ml_score": 0.5, "em_confidence": 0.0,
        }
        context = {
            "recommended_strategy_name": "Top",
            "recommended_strategy_description": "desc",
            "recommended_score": base_score,
            "alternatives": [{"name": "Alt1", "description": "d", "score": base_score}],
        }
        explanation = TemplateLLMClient().explain(context)
        assert "Alt1" in explanation
        assert "1 alternative(s)" in explanation
