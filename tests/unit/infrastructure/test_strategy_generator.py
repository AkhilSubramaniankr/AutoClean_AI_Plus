"""Unit tests for infrastructure.data_processing.strategy_generator.StrategyGenerator.

Includes an explicit test asserting FR-3 ("at least two candidate cleaning
strategies per detected issue profile") for both the messy and the
zero-issue edge case.
"""

from __future__ import annotations

import pandas as pd
import pytest

from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
from autoclean.infrastructure.data_processing.strategy_generator import StrategyGenerator

pytestmark = pytest.mark.unit


class TestStrategyGenerator:
    def test_fr3_at_least_two_strategies_for_messy_data(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        strategies = StrategyGenerator().generate(issues)
        assert len(strategies) >= 2

    def test_fr3_at_least_two_strategies_for_clean_data(self, clean_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(clean_dataframe)
        issues = IssueDetector().detect(clean_dataframe, profile)
        strategies = StrategyGenerator().generate(issues)
        assert len(strategies) >= 2

    def test_exactly_one_baseline_strategy(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        strategies = StrategyGenerator().generate(issues)
        baseline_strategies = [s for s in strategies if s.is_baseline]
        assert len(baseline_strategies) == 1

    def test_strategy_ids_are_unique(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        strategies = StrategyGenerator().generate(issues)
        ids = [s.strategy_id for s in strategies]
        assert len(ids) == len(set(ids))

    def test_aggressive_strategy_uses_removal_not_clipping(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        strategies = StrategyGenerator().generate(issues)
        aggressive = next(s for s in strategies if s.name.startswith("Aggressive"))
        operations = {step.operation.value for step in aggressive.steps}
        assert "iqr_outlier_removal" in operations
        assert "drop_rows_with_missing" in operations

    def test_conservative_strategy_uses_imputation_not_dropping(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        strategies = StrategyGenerator().generate(issues)
        conservative = next(s for s in strategies if s.name.startswith("Conservative"))
        operations = {step.operation.value for step in conservative.steps}
        assert "median_imputation" in operations
        assert "iqr_outlier_clipping" in operations
        assert "drop_rows_with_missing" not in operations

    def test_baseline_never_imputes_or_removes(self, messy_dataframe: pd.DataFrame) -> None:
        profile = DatasetProfiler().profile(messy_dataframe)
        issues = IssueDetector().detect(messy_dataframe, profile)
        strategies = StrategyGenerator().generate(issues)
        baseline = next(s for s in strategies if s.is_baseline)
        operations = {step.operation.value for step in baseline.steps}
        assert operations.isdisjoint(
            {"median_imputation", "mean_imputation", "mode_imputation",
             "drop_rows_with_missing", "iqr_outlier_removal", "iqr_outlier_clipping"}
        )
