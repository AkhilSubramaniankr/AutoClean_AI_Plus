"""Unit tests for infrastructure.data_processing.issue_detector.IssueDetector."""

from __future__ import annotations

import pandas as pd
import pytest

from autoclean.domain.entities.data_issue import IssueType
from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler

pytestmark = pytest.mark.unit


class TestIssueDetector:
    def test_clean_dataframe_yields_no_issues(self, clean_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(clean_dataframe)
        issues = IssueDetector().detect(clean_dataframe, profile)
        assert issues == []

    def test_messy_dataframe_yields_one_of_each_issue_type(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        found_types = {issue.issue_type for issue in issues}
        assert found_types == {
            IssueType.MISSING_VALUES,
            IssueType.DUPLICATE_ROWS,
            IssueType.OUTLIERS,
            IssueType.INCONSISTENT_DTYPE,
        }

    def test_missing_value_issue_has_correct_column_and_count(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        missing_issues = [i for i in issues if i.issue_type == IssueType.MISSING_VALUES]
        assert len(missing_issues) == 1
        assert missing_issues[0].column == "age"
        assert missing_issues[0].affected_row_count == 1

    def test_duplicate_issue_is_dataset_wide(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        duplicate_issues = [i for i in issues if i.issue_type == IssueType.DUPLICATE_ROWS]
        assert len(duplicate_issues) == 1
        assert duplicate_issues[0].column is None

    def test_dtype_issue_has_severity_one(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        dtype_issues = [i for i in issues if i.issue_type == IssueType.INCONSISTENT_DTYPE]
        assert len(dtype_issues) == 1
        assert dtype_issues[0].severity == 1.0

    def test_empty_dataframe_row_count_zero_yields_no_missing_or_outlier_issues(self) -> None:
        df = pd.DataFrame({"a": pd.Series(dtype="float64"), "b": pd.Series(dtype="float64")})
        profile = DatasetProfiler().profile(df)
        issues = IssueDetector().detect(df, profile)
        assert issues == []
