"""Unit tests for quality_metrics.py and cost_metrics.py (Phase 6)."""

from __future__ import annotations

import pytest

from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.infrastructure.metrics.cost_metrics import compute_cost_score
from autoclean.infrastructure.metrics.quality_metrics import compute_quality_score

pytestmark = pytest.mark.unit


def _profile(**overrides) -> DatasetProfile:
    defaults = dict(
        row_count=100, column_count=5, missing_value_pct=10.0,
        duplicate_row_count=2, outlier_count=3, dtype_issue_columns={},
    )
    defaults.update(overrides)
    return DatasetProfile(**defaults)


class TestQualityMetrics:
    def test_no_change_scores_neutral(self) -> None:
        profile = _profile()
        assert compute_quality_score(profile, profile) == pytest.approx(0.5)

    def test_full_improvement_scores_near_one(self) -> None:
        before = _profile(missing_value_pct=20.0, duplicate_row_count=5, outlier_count=5)
        after = _profile(missing_value_pct=0.0, duplicate_row_count=0, outlier_count=0)
        assert compute_quality_score(before, after) == pytest.approx(1.0)

    def test_making_things_worse_scores_below_neutral(self) -> None:
        before = _profile(missing_value_pct=5.0, duplicate_row_count=0, outlier_count=0)
        after = _profile(missing_value_pct=20.0, duplicate_row_count=5, outlier_count=5)
        assert compute_quality_score(before, after) < 0.5

    def test_already_clean_dataset_that_stays_clean_scores_full_credit(self) -> None:
        clean = _profile(missing_value_pct=0.0, duplicate_row_count=0, outlier_count=0)
        assert compute_quality_score(clean, clean) == 1.0

    def test_result_is_a_plain_python_float(self) -> None:
        result = compute_quality_score(_profile(missing_value_pct=10.0), _profile(missing_value_pct=5.0))
        assert type(result) is float  # noqa: E721 -- explicitly checking it's not numpy.float64


class TestCostMetrics:
    def _strategy(self, *operations: CleaningOperation) -> CleaningStrategy:
        return CleaningStrategy(
            strategy_id="s1", name="Test",
            steps=tuple(CleaningStep(operation=op, target_column="col") for op in operations),
        )

    def test_more_steps_cost_more(self) -> None:
        one_step = self._strategy(CleaningOperation.MEDIAN_IMPUTATION)
        three_steps = self._strategy(
            CleaningOperation.MEDIAN_IMPUTATION, CleaningOperation.IQR_OUTLIER_CLIPPING, CleaningOperation.TYPE_COERCION
        )
        assert compute_cost_score(one_step, 1000) > compute_cost_score(three_steps, 1000)

    def test_linearithmic_operation_costs_more_than_linear_at_same_step_count(self) -> None:
        linear = self._strategy(CleaningOperation.MEDIAN_IMPUTATION)
        linearithmic = self._strategy(CleaningOperation.IQR_OUTLIER_REMOVAL)
        assert compute_cost_score(linear, 10_000) > compute_cost_score(linearithmic, 10_000)

    def test_empty_strategy_costs_nothing(self) -> None:
        empty = CleaningStrategy(strategy_id="s1", name="Empty", steps=())
        assert compute_cost_score(empty, 1000) == 1.0

    def test_deterministic_across_repeated_calls(self) -> None:
        strategy = self._strategy(CleaningOperation.MEDIAN_IMPUTATION, CleaningOperation.EXACT_DEDUPLICATION)
        first = compute_cost_score(strategy, 5000)
        second = compute_cost_score(strategy, 5000)
        assert first == second  # no timing variance -- same inputs, same output, always

    def test_result_is_a_plain_python_float(self) -> None:
        result = compute_cost_score(self._strategy(CleaningOperation.MEDIAN_IMPUTATION), 100)
        assert type(result) is float  # noqa: E721
