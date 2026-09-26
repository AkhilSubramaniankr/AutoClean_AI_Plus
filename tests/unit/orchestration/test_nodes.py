"""Unit tests for ExecutionNode, ValidationNode, ReportingNode (Phase 8),
using real FileDatasetRepository against real temp files -- these nodes'
entire job is real file I/O, so a fake repository would prove nothing.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from autoclean.application.use_cases.execute_cleaning import ExecuteCleaningUseCase
from autoclean.application.use_cases.generate_report import GenerateReportUseCase
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.application.use_cases.validate_cleaned_dataset import ValidateCleanedDatasetUseCase
from autoclean.infrastructure.persistence.file_dataset_repository import FileDatasetRepository
from autoclean.orchestration.nodes.execution_node import ExecutionNode
from autoclean.orchestration.nodes.reporting_node import ReportingNode
from autoclean.orchestration.nodes.validation_node import ValidationNode

pytestmark = pytest.mark.unit


def _analyzed_state(df: pd.DataFrame, dataset_path: str) -> dict:
    profile, issues = ProfileDatasetUseCase().execute(df)
    strategies = GenerateStrategiesUseCase().execute(issues)
    return {
        "experiment_id": "e1", "dataset_path": dataset_path, "dataset_profile": profile,
        "candidate_strategies": strategies, "recommended_strategy_id": strategies[0].strategy_id,
        "audit_log_entries": [],
    }


class TestExecutionNode:
    def test_run_produces_a_real_cleaned_file(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        input_path = str(tmp_path / "input.csv")
        messy_dataframe.to_csv(input_path, index=False)
        state = _analyzed_state(messy_dataframe, input_path)

        repo = FileDatasetRepository()
        node = ExecutionNode(repo, ExecuteCleaningUseCase(repo), output_dir=str(tmp_path / "cleaned"))
        result = node.run(state)

        assert Path(result["cleaned_dataset_path"]).exists()
        assert result["approved_strategy_id"] == state["recommended_strategy_id"]
        assert result["current_node"] == "execution_node"
        assert len(result["audit_log_entries"]) == 1


class TestValidationNode:
    def test_run_produces_a_real_validation_report(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        input_path = str(tmp_path / "input.csv")
        messy_dataframe.to_csv(input_path, index=False)
        state = _analyzed_state(messy_dataframe, input_path)

        repo = FileDatasetRepository()
        execution_result = ExecutionNode(
            repo, ExecuteCleaningUseCase(repo), output_dir=str(tmp_path / "cleaned")
        ).run(state)
        state.update(execution_result)

        validation_node = ValidationNode(repo, ValidateCleanedDatasetUseCase())
        result = validation_node.run(state)

        assert isinstance(result["validation_passed"], bool)
        assert result["validation_report"] is not None
        assert result["current_node"] == "validation_node"


class TestReportingNode:
    def test_run_produces_real_report_and_script(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        input_path = str(tmp_path / "input.csv")
        messy_dataframe.to_csv(input_path, index=False)
        state = _analyzed_state(messy_dataframe, input_path)
        strategy_id = state["recommended_strategy_id"]

        repo = FileDatasetRepository()
        execution_result = ExecutionNode(
            repo, ExecuteCleaningUseCase(repo), output_dir=str(tmp_path / "cleaned")
        ).run(state)
        state.update(execution_result)
        validation_result = ValidationNode(repo, ValidateCleanedDatasetUseCase()).run(state)
        state.update(validation_result)

        # Minimal fields a real DecisionReportingAgent pass would have set:
        state["strategy_scores"] = {
            strategy_id: {
                "data_quality_score": 0.8, "computational_cost_score": 0.9,
                "information_preservation_score": 0.7, "statistical_validity_score": 0.9,
                "fairness_impact_score": 0.5, "downstream_ml_score": 0.5, "em_confidence": 1.0,
            }
        }
        state["ranked_strategy_ids"] = [strategy_id]
        state["explanation_text"] = "Test explanation."
        state["decided_by"] = "tester"
        state["decided_at"] = "2026-01-01T00:00:00"

        reporting_node = ReportingNode(
            GenerateReportUseCase(), report_dir=str(tmp_path / "reports"), script_dir=str(tmp_path / "scripts")
        )
        result = reporting_node.run(state)

        assert Path(result["executive_report_path"]).exists()
        assert Path(result["reproducible_script_path"]).exists()
        assert result["current_node"] == "reporting_node"
