"""Unit tests for information_preservation.py and statistical_validity.py (Phase 6)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from autoclean.infrastructure.metrics.information_preservation import (
    compute_information_preservation_score,
)
from autoclean.infrastructure.metrics.statistical_validity import compute_statistical_validity_score

pytestmark = pytest.mark.unit


class TestInformationPreservation:
    def test_identical_dataframe_scores_full_marks(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
        assert compute_information_preservation_score(df, df) == pytest.approx(1.0)

    def test_dropping_half_the_rows_scores_around_half(self) -> None:
        original = pd.DataFrame({"a": range(10)})
        cleaned = original.iloc[:5]
        assert compute_information_preservation_score(original, cleaned) == pytest.approx(0.5)

    def test_dropping_all_rows_scores_zero(self) -> None:
        original = pd.DataFrame({"a": range(10)})
        cleaned = original.iloc[0:0]
        assert compute_information_preservation_score(original, cleaned) == pytest.approx(0.0)

    def test_altering_values_without_dropping_rows_scores_below_full(self) -> None:
        original = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0]})
        cleaned = original.copy()
        cleaned.loc[0, "a"] = 999.0  # simulate an imputed/clipped value
        score = compute_information_preservation_score(original, cleaned)
        assert 0.0 < score < 1.0

    def test_still_missing_value_not_counted_as_altered(self) -> None:
        original = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
        cleaned = original.copy()  # untouched -- still missing, not "changed"
        assert compute_information_preservation_score(original, cleaned) == pytest.approx(1.0)

    def test_empty_original_dataframe_scores_full_marks(self) -> None:
        empty = pd.DataFrame({"a": pd.Series(dtype="float64")})
        assert compute_information_preservation_score(empty, empty) == 1.0

    def test_result_is_a_plain_python_float(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = compute_information_preservation_score(df, df.iloc[:2])
        assert type(result) is float  # noqa: E721


class TestStatisticalValidity:
    def test_identical_distributions_score_full_marks(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0] * 5})
        assert compute_statistical_validity_score(df, df, ("a",)) == pytest.approx(1.0)

    def test_wildly_different_distributions_score_low(self) -> None:
        rng = np.random.default_rng(42)
        original = pd.DataFrame({"a": rng.normal(loc=0, scale=1, size=200)})
        # An entirely different, non-overlapping distribution:
        shifted = pd.DataFrame({"a": rng.normal(loc=1000, scale=1, size=200)})
        score = compute_statistical_validity_score(original, shifted, ("a",))
        assert score < 0.2

    def test_no_numeric_columns_returns_neutral(self) -> None:
        df = pd.DataFrame({"a": ["x", "y", "z"]})
        assert compute_statistical_validity_score(df, df, ()) == 0.5

    def test_missing_column_in_one_side_is_skipped_not_crashed(self) -> None:
        original = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        cleaned = pd.DataFrame({"b": [1.0, 2.0, 3.0]})
        # column "a" doesn't exist in cleaned -- should not raise, falls back to neutral
        assert compute_statistical_validity_score(original, cleaned, ("a",)) == 0.5

    def test_result_is_a_plain_python_float(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]})
        result = compute_statistical_validity_score(df, df, ("a",))
        assert type(result) is float  # noqa: E721 -- regression test for the numpy.float64 bug
