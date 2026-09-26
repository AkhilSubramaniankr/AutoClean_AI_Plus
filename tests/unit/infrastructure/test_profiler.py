"""Unit tests for infrastructure.data_processing.profiler.DatasetProfiler."""

from __future__ import annotations

import pandas as pd
import pytest

from autoclean.infrastructure.data_processing.profiler import DatasetProfiler

pytestmark = pytest.mark.unit


class TestDatasetProfiler:
    def test_clean_dataframe_has_no_issues(self, clean_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(clean_dataframe)
        assert profile.row_count == 5
        assert profile.column_count == 3
        assert profile.missing_value_pct == 0.0
        assert profile.duplicate_row_count == 0
        assert profile.outlier_count == 0
        assert profile.dtype_issue_columns == {}

    def test_messy_dataframe_detects_all_issue_categories(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        assert profile.missing_value_pct > 0
        assert profile.duplicate_row_count > 0
        assert profile.outlier_count > 0
        assert "income" in profile.dtype_issue_columns

    def test_zero_column_dataframe_raises(self) -> None:
        with pytest.raises(ValueError, match="zero columns"):
            DatasetProfiler().profile(pd.DataFrame())

    def test_numeric_and_categorical_columns_partitioned(self, clean_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(clean_dataframe)
        assert "age" in profile.numeric_columns
        assert "income" in profile.numeric_columns
        assert "city" in profile.categorical_columns
        # Every column accounted for exactly once
        assert set(profile.numeric_columns) | set(profile.categorical_columns) == set(
            profile.column_names
        )
        assert set(profile.numeric_columns) & set(profile.categorical_columns) == set()

    def test_missing_value_pct_is_cell_level_not_row_level(self) -> None:
        # 1 missing cell out of 2 rows x 2 columns = 4 cells -> 25%
        df = pd.DataFrame({"a": [1, None], "b": [3, 4]})
        profile = DatasetProfiler().profile(df)
        assert profile.missing_value_pct == pytest.approx(25.0)
