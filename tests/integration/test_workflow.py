"""Integration test: the full LangGraph workflow, end-to-end, including the
human-approval interrupt AND (as of Phase 8) real execution, validation,
and report/script generation against real temporary files.

This is the single most important test file in the project -- it proves
the architecture's central claims actually hold at runtime, not just in
the design document: FR-9 (mandatory human approval), and as of Phase 8,
that the whole pipeline produces real, consistent, round-tripped output on
disk (not just in-memory state).

Uses a REAL FileDatasetRepository against real temporary files (not the
FakeDatasetRepository from tests/fakes.py) specifically because Phase 8's
execution_node writes a real cleaned CSV that validation_node must read
back -- a fake repository whose save() is a no-op and whose load() ignores
its path argument would silently validate against the wrong data and prove
nothing about the real round trip.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd
import pytest
from langgraph.checkpoint.memory import MemorySaver

from autoclean.agents.analysis_agent import AnalysisAgent
from autoclean.agents.decision_reporting_agent import DecisionReportingAgent
from autoclean.agents.evaluation_agent import EvaluationAgent
from autoclean.application.use_cases.evaluate_strategies import EvaluateStrategiesUseCase
from autoclean.application.use_cases.execute_cleaning import ExecuteCleaningUseCase
from autoclean.application.use_cases.explain_recommendation import ExplainRecommendationUseCase
from autoclean.application.use_cases.generate_report import GenerateReportUseCase
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.application.use_cases.validate_cleaned_dataset import ValidateCleanedDatasetUseCase
from autoclean.domain.value_objects.objective_weights import ObjectiveWeights
from autoclean.infrastructure.metrics.placeholder_metrics_engine import PlaceholderMetricsEngine
from autoclean.infrastructure.persistence.file_dataset_repository import FileDatasetRepository
from autoclean.orchestration.graph_builder import build_graph
from autoclean.orchestration.nodes.execution_node import ExecutionNode
from autoclean.orchestration.nodes.reporting_node import ReportingNode
from autoclean.orchestration.nodes.validation_node import ValidationNode
from tests.fakes import FakeLLMClient

pytestmark = pytest.mark.integration


def _build_test_graph(df: pd.DataFrame, tmp_path: Path) -> tuple[object, str]:
    """Writes `df` to a real temp CSV and wires a full graph with real
    FileDatasetRepository I/O throughout. Returns (graph, dataset_path).
    """
    dataset_path = str(tmp_path / "input.csv")
    df.to_csv(dataset_path, index=False)
    repo = FileDatasetRepository()

    analysis_agent = AnalysisAgent(repo, ProfileDatasetUseCase(), GenerateStrategiesUseCase())
    evaluation_agent = EvaluationAgent(
        repo, EvaluateStrategiesUseCase(PlaceholderMetricsEngine(), ObjectiveWeights.uniform())
    )
    decision_agent = DecisionReportingAgent(ExplainRecommendationUseCase(FakeLLMClient()))
    execution_node = ExecutionNode(repo, ExecuteCleaningUseCase(repo), output_dir=str(tmp_path / "cleaned"))
    validation_node = ValidationNode(repo, ValidateCleanedDatasetUseCase())
    reporting_node = ReportingNode(
        GenerateReportUseCase(), report_dir=str(tmp_path / "reports"), script_dir=str(tmp_path / "scripts")
    )
    graph = build_graph(
        analysis_agent, evaluation_agent, decision_agent,
        execution_node, validation_node, reporting_node, MemorySaver(),
    )
    return graph, dataset_path


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


class TestWorkflowInterrupt:
    def test_graph_pauses_before_human_approval(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        graph, dataset_path = _build_test_graph(messy_dataframe, tmp_path)
        config = _config(str(uuid.uuid4()))

        graph.invoke({"experiment_id": "e1", "dataset_path": dataset_path}, config)

        assert graph.get_state(config).next == ("human_approval",)

    def test_graph_never_executes_without_a_human_decision(
        self, messy_dataframe: pd.DataFrame, tmp_path: Path
    ) -> None:
        """The core FR-9 guarantee: calling invoke(None, config) with NO human
        decision set at all must NOT silently proceed as if approved.
        """
        graph, dataset_path = _build_test_graph(messy_dataframe, tmp_path)
        config = _config(str(uuid.uuid4()))

        graph.invoke({"experiment_id": "e1", "dataset_path": dataset_path}, config)
        # Deliberately do NOT call update_state with a decision.
        result = graph.invoke(None, config)

        # Routing falls through to the "not approved" branch (loops back to
        # decision_reporting_agent) rather than proceeding to execution.
        assert result.get("current_node") != "execution_node"
        assert result.get("approved_strategy_id") is None


class TestWorkflowApprovalPath:
    def test_approval_reaches_completion(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        graph, dataset_path = _build_test_graph(messy_dataframe, tmp_path)
        config = _config(str(uuid.uuid4()))

        graph.invoke({"experiment_id": "e1", "dataset_path": dataset_path}, config)
        graph.update_state(config, {"human_decision": "approved", "decided_by": "tester"})
        result = graph.invoke(None, config)

        assert result["current_node"] == "reporting_node"
        assert result["validation_passed"] is True
        assert graph.get_state(config).next == ()

    def test_real_files_are_actually_written_to_disk(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        """The Phase 8 payoff, checked concretely: a real cleaned CSV, a real
        executive report, and a real reproducible script all exist on disk
        after approval -- not just fields in the in-memory state.
        """
        graph, dataset_path = _build_test_graph(messy_dataframe, tmp_path)
        config = _config(str(uuid.uuid4()))

        graph.invoke({"experiment_id": "e2", "dataset_path": dataset_path}, config)
        graph.update_state(config, {"human_decision": "approved", "decided_by": "tester"})
        result = graph.invoke(None, config)

        assert Path(result["cleaned_dataset_path"]).exists()
        assert Path(result["executive_report_path"]).exists()
        assert Path(result["reproducible_script_path"]).exists()

        cleaned_df = pd.read_csv(result["cleaned_dataset_path"])
        assert len(cleaned_df) <= len(messy_dataframe)  # some strategies remove rows, never add them

        report_text = Path(result["executive_report_path"]).read_text()
        assert "## Summary" in report_text
        strategies_by_id = {s.strategy_id: s for s in result["candidate_strategies"]}
        approved_strategy_name = strategies_by_id[result["approved_strategy_id"]].name
        assert approved_strategy_name in report_text  # the real approved strategy's name appears in the real report


class TestWorkflowRejectionPath:
    def test_rejection_recommends_a_different_strategy_and_pauses_again(
        self, messy_dataframe: pd.DataFrame, tmp_path: Path
    ) -> None:
        graph, dataset_path = _build_test_graph(messy_dataframe, tmp_path)
        config = _config(str(uuid.uuid4()))

        first = graph.invoke({"experiment_id": "e1", "dataset_path": dataset_path}, config)
        graph.update_state(config, {"human_decision": "rejected", "decided_by": "tester"})
        second = graph.invoke(None, config)

        assert second["recommended_strategy_id"] != first["recommended_strategy_id"]
        assert graph.get_state(config).next == ("human_approval",)

    def test_rejecting_all_strategies_ends_gracefully(
        self, messy_dataframe: pd.DataFrame, tmp_path: Path
    ) -> None:
        graph, dataset_path = _build_test_graph(messy_dataframe, tmp_path)
        config = _config(str(uuid.uuid4()))

        result = graph.invoke({"experiment_id": "e1", "dataset_path": dataset_path}, config)
        n_candidates = len(result["ranked_strategy_ids"])

        for _ in range(n_candidates):
            graph.update_state(config, {"human_decision": "rejected", "decided_by": "tester"})
            result = graph.invoke(None, config)

        assert result.get("error") == "All candidate strategies have been rejected by the human reviewer."
        assert graph.get_state(config).next == ()


class TestAuditTrail:
    def test_audit_log_grows_monotonically_and_never_resets(
        self, messy_dataframe: pd.DataFrame, tmp_path: Path
    ) -> None:
        graph, dataset_path = _build_test_graph(messy_dataframe, tmp_path)
        config = _config(str(uuid.uuid4()))

        result = graph.invoke({"experiment_id": "e1", "dataset_path": dataset_path}, config)
        count_after_first_pass = len(result["audit_log_entries"])
        assert count_after_first_pass > 0

        graph.update_state(config, {"human_decision": "approved", "decided_by": "tester"})
        result = graph.invoke(None, config)
        assert len(result["audit_log_entries"]) > count_after_first_pass
