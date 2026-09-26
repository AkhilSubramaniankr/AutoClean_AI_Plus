"""Unit tests for fairness_metrics.py and downstream_ml_metrics.py (Phase 6)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from autoclean.infrastructure.metrics.downstream_ml_metrics import (
    compute_downstream_ml_score,
    select_default_target_column,
)
from autoclean.infrastructure.metrics.fairness_metrics import (
    compute_fairness_score,
    select_default_sensitive_column,
)

pytestmark = pytest.mark.unit


class TestFairnessMetrics:
    def test_even_retention_across_groups_scores_full_marks(self) -> None:
        original = pd.DataFrame({"group": ["A", "A", "B", "B"], "val": [1, 2, 3, 4]})
        cleaned = original.iloc[[0, 2]]  # drops 1 of 2 from EACH group -- even impact
        assert compute_fairness_score(original, cleaned, "group") == pytest.approx(1.0)

    def test_uneven_retention_across_groups_scores_below_full(self) -> None:
        original = pd.DataFrame({"group": ["A"] * 10 + ["B"] * 10, "val": range(20)})
        cleaned = original[original["group"] == "A"]  # drops ALL of group B, none of A
        assert compute_fairness_score(original, cleaned, "group") == pytest.approx(0.0)

    def test_no_sensitive_column_returns_neutral(self) -> None:
        original = pd.DataFrame({"a": [1, 2, 3]})
        assert compute_fairness_score(original, original, None) == 0.5

    def test_select_default_sensitive_column_picks_lowest_cardinality(self) -> None:
        df = pd.DataFrame({"binary_flag": [0, 1, 0, 1], "high_card": ["a", "b", "c", "d"]})
        selected = select_default_sensitive_column(df, ("binary_flag", "high_card"))
        assert selected == "binary_flag"

    def test_select_default_sensitive_column_returns_none_if_no_candidates(self) -> None:
        df = pd.DataFrame({"constant": [1, 1, 1]})
        assert select_default_sensitive_column(df, ("constant",)) is None

    def test_result_is_a_plain_python_float(self) -> None:
        original = pd.DataFrame({"group": ["A", "B"], "val": [1, 2]})
        result = compute_fairness_score(original, original, "group")
        assert type(result) is float  # noqa: E721 -- regression test for the numpy.float64 bug


class TestDownstreamMlMetrics:
    def _classification_dataframe(self, n: int = 60) -> pd.DataFrame:
        rng = np.random.default_rng(0)
        target = rng.integers(0, 2, size=n)
        # feature strongly correlated with target, so a real model can score well above chance
        feature = target * 5 + rng.normal(0, 0.5, size=n)
        return pd.DataFrame({"feature": feature, "target": target})

    def test_learnable_pattern_scores_well_above_chance(self) -> None:
        df = self._classification_dataframe()
        score = compute_downstream_ml_score(df, "target", ("feature",))
        assert score > 0.7  # a near-perfectly-separable synthetic pattern

    def test_insufficient_rows_returns_neutral_not_a_crash(self) -> None:
        tiny_df = pd.DataFrame({"feature": [1.0, 2.0], "target": [0, 1]})
        assert compute_downstream_ml_score(tiny_df, "target", ("feature",)) == 0.5

    def test_missing_target_column_returns_neutral(self) -> None:
        df = pd.DataFrame({"feature": range(20)})
        assert compute_downstream_ml_score(df, "nonexistent", ("feature",)) == 0.5

    def test_no_feature_columns_returns_neutral(self) -> None:
        df = pd.DataFrame({"target": [0, 1] * 10})
        assert compute_downstream_ml_score(df, "target", ()) == 0.5

    def test_select_default_target_column_excludes_given_column(self) -> None:
        df = pd.DataFrame({"sensitive": [0, 1, 0, 1], "target_candidate": ["x", "y", "x", "y"]})
        selected = select_default_target_column(
            df, ("sensitive", "target_candidate"), exclude="sensitive"
        )
        assert selected == "target_candidate"

    def test_result_is_a_plain_python_float(self) -> None:
        df = self._classification_dataframe()
        result = compute_downstream_ml_score(df, "target", ("feature",))
        assert type(result) is float  # noqa: E721 -- regression test for the numpy.float64 bug
