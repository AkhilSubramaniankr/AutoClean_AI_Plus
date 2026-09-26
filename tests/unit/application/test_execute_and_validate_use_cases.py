"""Unit tests for ExecuteCleaningUseCase and ValidateCleanedDatasetUseCase (Phase 8)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from autoclean.application.use_cases.execute_cleaning import ExecuteCleaningUseCase
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.application.use_cases.validate_cleaned_dataset import ValidateCleanedDatasetUseCase
from autoclean.infrastructure.persistence.file_dataset_repository import FileDatasetRepository

pytestmark = pytest.mark.unit


def _strategies(df: pd.DataFrame):
    profile, issues = ProfileDatasetUseCase().execute(df)
    return GenerateStrategiesUseCase().execute(issues), profile


class TestExecuteCleaningUseCase:
    def test_execute_saves_a_real_cleaned_file(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        strategies, _ = _strategies(messy_dataframe)
        conservative = next(s for s in strategies if s.name.startswith("Conservative"))
        output_path = str(tmp_path / "cleaned.csv")

        cleaned_df, saved_path = ExecuteCleaningUseCase(FileDatasetRepository()).execute(
            messy_dataframe, conservative, output_path
        )

        assert Path(saved_path).exists()
        assert len(pd.read_csv(saved_path)) == len(cleaned_df)

    def test_baseline_never_reduces_row_count_below_original(
        self, messy_dataframe: pd.DataFrame, tmp_path: Path
    ) -> None:
        strategies, _ = _strategies(messy_dataframe)
        baseline = next(s for s in strategies if s.is_baseline)
        cleaned_df, _ = ExecuteCleaningUseCase(FileDatasetRepository()).execute(
            messy_dataframe, baseline, str(tmp_path / "out.csv")
        )
        assert len(cleaned_df) <= len(messy_dataframe)


class TestValidateCleanedDatasetUseCase:
    def test_identical_data_passes_validation(self, clean_dataframe: pd.DataFrame) -> None:
        report = ValidateCleanedDatasetUseCase().execute(clean_dataframe, clean_dataframe)
        assert report.passed is True
        assert report.schema_consistent is True
        assert report.remaining_issue_count == 0

    def test_improved_data_meets_quality_threshold(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        strategies, _ = _strategies(messy_dataframe)
        conservative = next(s for s in strategies if s.name.startswith("Conservative"))
        cleaned_df, _ = ExecuteCleaningUseCase(FileDatasetRepository()).execute(
            messy_dataframe, conservative, str(tmp_path / "out.csv")
        )
        report = ValidateCleanedDatasetUseCase().execute(messy_dataframe, cleaned_df)
        assert report.quality_threshold_met is True
        assert report.row_count_before == len(messy_dataframe)
        assert report.row_count_after == len(cleaned_df)

    def test_schema_change_is_detected(self, clean_dataframe: pd.DataFrame) -> None:
        dropped_column_df = clean_dataframe.drop(columns=["city"])
        report = ValidateCleanedDatasetUseCase().execute(clean_dataframe, dropped_column_df)
        assert report.schema_consistent is False
        assert report.passed is False

    def test_custom_quality_threshold_is_respected(self, clean_dataframe: pd.DataFrame) -> None:
        # An impossibly high threshold should fail even on already-clean data staying clean.
        report = ValidateCleanedDatasetUseCase().execute(
            clean_dataframe, clean_dataframe, quality_threshold=1.5
        )
        assert report.quality_threshold_met is False
