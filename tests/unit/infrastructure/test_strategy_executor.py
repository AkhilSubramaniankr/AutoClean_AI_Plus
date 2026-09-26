"""Unit tests for StrategyExecutor (Phase 6)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)
from autoclean.infrastructure.data_processing.strategy_executor import StrategyExecutor

pytestmark = pytest.mark.unit


def _strategy(*steps: CleaningStep) -> CleaningStrategy:
    return CleaningStrategy(strategy_id="s1", name="Test", steps=tuple(steps))


class TestStrategyExecutor:
    def test_never_mutates_the_input_dataframe(self) -> None:
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
        original_copy = df.copy()
        StrategyExecutor().apply(df, _strategy(CleaningStep(operation=CleaningOperation.MEAN_IMPUTATION, target_column="a")))
        pd.testing.assert_frame_equal(df, original_copy)

    def test_no_op_returns_unchanged_data(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = StrategyExecutor().apply(df, _strategy(CleaningStep(operation=CleaningOperation.NO_OP)))
        pd.testing.assert_frame_equal(result, df)

    def test_median_imputation_fills_missing_values(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0]})
        result = StrategyExecutor().apply(
            df, _strategy(CleaningStep(operation=CleaningOperation.MEDIAN_IMPUTATION, target_column="a"))
        )
        assert result["a"].isna().sum() == 0
        assert result.loc[2, "a"] == 2.0  # median of [1, 2, 4]

    def test_exact_deduplication_preserves_original_index_of_survivors(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 1]})  # row 2 duplicates row 0
        result = StrategyExecutor().apply(
            df, _strategy(CleaningStep(operation=CleaningOperation.EXACT_DEDUPLICATION))
        )
        assert len(result) == 2
        assert list(result.index) == [0, 1]  # NOT reset to [0, 1] artificially -- these ARE the originals

    def test_drop_rows_with_missing_removes_only_flagged_column(self) -> None:
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0], "b": [10, 20, 30]})
        result = StrategyExecutor().apply(
            df, _strategy(CleaningStep(operation=CleaningOperation.DROP_ROWS_WITH_MISSING, target_column="a"))
        )
        assert len(result) == 2
        assert result.index.tolist() == [0, 2]

    def test_iqr_outlier_clipping_bounds_values_without_removing_rows(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0, 1000.0]})
        result = StrategyExecutor().apply(
            df, _strategy(CleaningStep(operation=CleaningOperation.IQR_OUTLIER_CLIPPING, target_column="a"))
        )
        assert len(result) == len(df)
        assert result["a"].max() < 1000.0

    def test_iqr_outlier_removal_drops_outlier_rows(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0, 1000.0]})
        result = StrategyExecutor().apply(
            df, _strategy(CleaningStep(operation=CleaningOperation.IQR_OUTLIER_REMOVAL, target_column="a"))
        )
        assert len(result) < len(df)
        assert 1000.0 not in result["a"].to_numpy()

    def test_type_coercion_converts_numeric_like_strings(self) -> None:
        df = pd.DataFrame({"a": ["1", "2", "abc", "4"]})
        result = StrategyExecutor().apply(
            df, _strategy(CleaningStep(operation=CleaningOperation.TYPE_COERCION, target_column="a"))
        )
        assert pd.api.types.is_numeric_dtype(result["a"])
        assert result["a"].isna().sum() == 1  # "abc" becomes NaN

    def test_multiple_steps_apply_in_order(self) -> None:
        df = pd.DataFrame({"a": ["1", "2", None, "4"]})
        result = StrategyExecutor().apply(
            df,
            _strategy(
                CleaningStep(operation=CleaningOperation.TYPE_COERCION, target_column="a"),
                CleaningStep(operation=CleaningOperation.MEDIAN_IMPUTATION, target_column="a"),
            ),
        )
        assert pd.api.types.is_numeric_dtype(result["a"])
        assert result["a"].isna().sum() == 0

    def test_constant_imputation_uses_given_fill_value(self) -> None:
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
        result = StrategyExecutor().apply(
            df,
            _strategy(
                CleaningStep(
                    operation=CleaningOperation.CONSTANT_IMPUTATION, target_column="a", parameters={"fill_value": -1}
                )
            ),
        )
        assert result.loc[1, "a"] == -1
