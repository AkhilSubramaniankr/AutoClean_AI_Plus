#!/usr/bin/env python
"""Interactive, non-UI entry point for running the AutoClean AI+ workflow
end-to-end against a real dataset -- the Phase 5 hands-on demo, and a
reproducible alternative to the Streamlit UI (which doesn't exist until
Phase 9).

Usage:
    PYTHONPATH=src python scripts/run_workflow_cli.py path/to/your_data.csv

Wires together:
  - FileDatasetRepository (real CSV/XLSX/Parquet I/O)
  - RealMetricsEngine (Phase 6, real six-objective evaluation)
  - FallbackLLMClient(OllamaLLMClient, TemplateLLMClient) (Phase 7, real
    explanation with graceful fallback)
  - ExecutionNode/ValidationNode/ReportingNode (Phase 8, real execution,
    validation, and report/script generation)
  - SQLiteExperimentRepository (real, persists to data/autoclean.db)
  - The real LangGraph workflow (graph_builder.build_graph)

At the human-approval interrupt, this script prompts you directly in the
terminal -- this is the most concrete way to see FR-9 (mandatory human
approval) actually gating progress.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Allow running as `python scripts/run_workflow_cli.py` without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from autoclean.agents.analysis_agent import AnalysisAgent  # noqa: E402
from autoclean.agents.decision_reporting_agent import DecisionReportingAgent  # noqa: E402
from autoclean.agents.evaluation_agent import EvaluationAgent  # noqa: E402
from autoclean.application.use_cases.evaluate_strategies import EvaluateStrategiesUseCase  # noqa: E402
from autoclean.application.use_cases.explain_recommendation import ExplainRecommendationUseCase  # noqa: E402
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase  # noqa: E402
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase  # noqa: E402
from autoclean.config.settings import get_settings  # noqa: E402
from autoclean.domain.entities.audit_event import AuditEvent  # noqa: E402
from autoclean.domain.entities.decision import DecisionType  # noqa: E402
from autoclean.domain.entities.experiment import Experiment, ExperimentStatus  # noqa: E402
from autoclean.domain.entities.evaluation_score import EvaluationScore  # noqa: E402
from autoclean.infrastructure.llm.fallback_llm_client import FallbackLLMClient  # noqa: E402
from autoclean.infrastructure.llm.ollama_llm_client import OllamaLLMClient  # noqa: E402
from autoclean.infrastructure.llm.template_llm_client import TemplateLLMClient  # noqa: E402
from autoclean.infrastructure.metrics.real_metrics_engine import RealMetricsEngine  # noqa: E402
from autoclean.infrastructure.objective_weights_loader import load_objective_weights  # noqa: E402
from autoclean.infrastructure.persistence.file_dataset_repository import FileDatasetRepository  # noqa: E402
from autoclean.infrastructure.persistence.sqlite.db_session import initialize_database  # noqa: E402
from autoclean.infrastructure.persistence.sqlite.experiment_repository_impl import (  # noqa: E402
    SQLiteExperimentRepository,
)
from autoclean.orchestration.graph_builder import build_graph  # noqa: E402
from autoclean.orchestration.nodes.execution_node import ExecutionNode  # noqa: E402
from autoclean.orchestration.nodes.reporting_node import ReportingNode  # noqa: E402
from autoclean.orchestration.nodes.validation_node import ValidationNode  # noqa: E402
from autoclean.application.use_cases.approve_strategy import ApproveStrategyUseCase  # noqa: E402
from autoclean.application.use_cases.execute_cleaning import ExecuteCleaningUseCase  # noqa: E402
from autoclean.application.use_cases.generate_report import GenerateReportUseCase  # noqa: E402
from autoclean.application.use_cases.validate_cleaned_dataset import ValidateCleanedDatasetUseCase  # noqa: E402
from datetime import datetime  # noqa: E402


def _persist_new_audit_entries(
    repository: SQLiteExperimentRepository, experiment_id: str, state_entries: list[dict], already_persisted: int
) -> int:
    """Copies any audit entries accumulated in WorkflowState (in-memory, per
    agent/node) into the SQLite audit_log table, so the persisted trail
    reflects every workflow step -- not just human decisions (which
    ApproveStrategyUseCase already persists directly).
    """
    for entry in state_entries[already_persisted:]:
        repository.append_audit_event(
            AuditEvent(
                id=entry["id"],
                experiment_id=experiment_id,
                event_type=entry["event_type"],
                actor=entry["actor"],
                timestamp=datetime.fromisoformat(entry["timestamp"]),
                payload=entry["payload"],
            )
        )
    return len(state_entries)


def _prompt_approval(strategy_id: str) -> str:
    while True:
        answer = input(f"\nApprove strategy {strategy_id}? [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return "approved"
        if answer in ("n", "no"):
            return "rejected"
        print("Please answer 'y' or 'n'.")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path/to/dataset.csv", file=sys.stderr)
        return 1

    dataset_path = sys.argv[1]
    if not Path(dataset_path).exists():
        print(f"File not found: {dataset_path}", file=sys.stderr)
        return 1

    settings = get_settings()
    connection = initialize_database(settings.resolved(settings.database_path))
    repository = SQLiteExperimentRepository(connection)

    analysis_agent = AnalysisAgent(FileDatasetRepository(), ProfileDatasetUseCase(), GenerateStrategiesUseCase())
    weights = load_objective_weights(settings.resolved(settings.objective_weights_path))
    evaluation_agent = EvaluationAgent(
        FileDatasetRepository(), EvaluateStrategiesUseCase(RealMetricsEngine(), weights)
    )
    decision_agent = DecisionReportingAgent(
        ExplainRecommendationUseCase(FallbackLLMClient(primary=OllamaLLMClient(), fallback=TemplateLLMClient()))
    )
    approve_use_case = ApproveStrategyUseCase(repository)

    execution_node = ExecutionNode(
        FileDatasetRepository(), ExecuteCleaningUseCase(FileDatasetRepository()),
        output_dir=str(settings.resolved(settings.data_cleaned_dir)),
    )
    validation_node = ValidationNode(FileDatasetRepository(), ValidateCleanedDatasetUseCase())
    reporting_node = ReportingNode(
        GenerateReportUseCase(),
        report_dir=str(settings.resolved(settings.reports_dir)),
        script_dir=str(settings.resolved(settings.scripts_dir)),
    )

    graph = build_graph(
        analysis_agent, evaluation_agent, decision_agent,
        execution_node, validation_node, reporting_node, MemorySaver(),
    )

    experiment_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": experiment_id}}

    print(f"\n=== Starting experiment {experiment_id} on {dataset_path} ===\n")
    result = graph.invoke({"experiment_id": experiment_id, "dataset_path": dataset_path}, config)
    persisted_audit_count = 0

    experiment = Experiment(
        id=experiment_id,
        dataset_name=Path(dataset_path).name,
        dataset_hash=str(hash(dataset_path)),  # placeholder hash; real content hashing is a Phase 6+ nicety
        status=ExperimentStatus.AWAITING_APPROVAL,
        dataset_profile=result["dataset_profile"],
        candidate_strategies=result["candidate_strategies"],
    )
    repository.save_experiment(experiment)
    repository.save_candidate_strategies(experiment_id, result["candidate_strategies"])
    persisted_audit_count = _persist_new_audit_entries(
        repository, experiment_id, result.get("audit_log_entries", []), persisted_audit_count
    )

    weights_used = {
        "data_quality": weights.data_quality,
        "computational_cost": weights.computational_cost,
        "information_preservation": weights.information_preservation,
        "statistical_validity": weights.statistical_validity,
        "fairness_impact": weights.fairness_impact,
        "downstream_ml": weights.downstream_ml,
    }
    for strategy_id, score_dict in result["strategy_scores"].items():
        score = EvaluationScore(**score_dict)
        repository.save_strategy_score(
            strategy_id, score, score.compute_weighted_total(weights), weights_used
        )

    print(f"Detected {len(result['detected_issues'])} issue(s); "
          f"generated {len(result['candidate_strategies'])} candidate strategies.\n")

    while True:
        print("-" * 70)
        print(result["explanation_text"])
        consistency_warnings = result.get("explanation_consistency_warnings", [])
        if consistency_warnings:
            print("\n⚠ CONSISTENCY WARNINGS (explanation may contain unsupported numbers):")
            for warning in consistency_warnings:
                print(f"  - {warning}")
        print("-" * 70)

        decision = _prompt_approval(result["recommended_strategy_id"])
        approve_use_case.execute(
            experiment_id=experiment_id,
            strategy_id=result["recommended_strategy_id"],
            decision_type=DecisionType.APPROVED if decision == "approved" else DecisionType.REJECTED,
            decided_by="cli_user",
        )
        graph.update_state(config, {"human_decision": decision, "decided_by": "cli_user"})
        result = graph.invoke(None, config)
        persisted_audit_count = _persist_new_audit_entries(
            repository, experiment_id, result.get("audit_log_entries", []), persisted_audit_count
        )

        if result.get("error"):
            print(f"\n{result['error']}\n")
            repository.append_audit_event(
                AuditEvent(id=str(uuid.uuid4()), experiment_id=experiment_id,
                           event_type="experiment_ended_no_approval", actor="run_workflow_cli")
            )
            return 0

        if result.get("current_node") == "reporting_node":
            experiment.mark_completed(result["approved_strategy_id"])
            repository.save_experiment(experiment)
            print(f"\n=== Experiment {experiment_id} complete ===")
            print(f"Approved strategy: {result['approved_strategy_id']}")
            print(f"Cleaned dataset saved to: {result['cleaned_dataset_path']}")
            validation_report = result.get("validation_report")
            print(f"Validation passed: {result['validation_passed']}"
                  + (f" ({validation_report.notes})" if validation_report is not None else ""))
            print(f"Executive report: {result['executive_report_path']}")
            print(f"Reproducible script: {result['reproducible_script_path']}")
            print(f"\nAudit trail ({len(repository.get_audit_trail(experiment_id))} events) "
                  f"persisted to {settings.resolved(settings.database_path)}")
            return 0
        # else: rejected -> loop continues with the next-ranked recommendation


if __name__ == "__main__":
    sys.exit(main())
