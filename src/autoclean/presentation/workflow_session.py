"""workflow_session.py: builds and caches the LangGraph workflow + its
dependencies in Streamlit's `st.session_state`, so all four pages share one
consistent wiring without duplicating dependency-injection code four times.

Design decision: the compiled graph and its `MemorySaver` checkpointer are
created ONCE per browser session and stored in `st.session_state` -- this is
required, not a convenience, because LangGraph's `interrupt_before`
mechanism only works if the SAME checkpointer instance persists across
Streamlit's rerun-per-interaction execution model. Rebuilding a fresh
`MemorySaver` on every rerun (which happens on every button click) would
silently discard the paused workflow state (Phase 5's interrupt) every time
a page renders.

The SQLite connection is also session-scoped, with `check_same_thread=False`
(Streamlit is not guaranteed to serve one session on exactly one Python
thread across reruns).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st
from langgraph.checkpoint.memory import MemorySaver

from autoclean.agents.analysis_agent import AnalysisAgent
from autoclean.agents.decision_reporting_agent import DecisionReportingAgent
from autoclean.agents.evaluation_agent import EvaluationAgent
from autoclean.application.use_cases.approve_strategy import ApproveStrategyUseCase
from autoclean.application.use_cases.evaluate_strategies import EvaluateStrategiesUseCase
from autoclean.application.use_cases.execute_cleaning import ExecuteCleaningUseCase
from autoclean.application.use_cases.explain_recommendation import ExplainRecommendationUseCase
from autoclean.application.use_cases.generate_report import GenerateReportUseCase
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.application.use_cases.validate_cleaned_dataset import ValidateCleanedDatasetUseCase
from autoclean.config.settings import get_settings
from autoclean.domain.value_objects.objective_weights import ObjectiveWeights
from autoclean.infrastructure.llm.fallback_llm_client import FallbackLLMClient
from autoclean.infrastructure.llm.ollama_llm_client import OllamaLLMClient
from autoclean.infrastructure.llm.template_llm_client import TemplateLLMClient
from autoclean.infrastructure.metrics.real_metrics_engine import RealMetricsEngine
from autoclean.infrastructure.objective_weights_loader import load_objective_weights
from autoclean.infrastructure.persistence.file_dataset_repository import FileDatasetRepository
from autoclean.infrastructure.persistence.sqlite.db_session import apply_schema
from autoclean.infrastructure.persistence.sqlite.experiment_repository_impl import (
    SQLiteExperimentRepository,
)
from autoclean.orchestration.graph_builder import build_graph
from autoclean.orchestration.nodes.execution_node import ExecutionNode
from autoclean.orchestration.nodes.reporting_node import ReportingNode
from autoclean.orchestration.nodes.validation_node import ValidationNode


@dataclass
class WorkflowSession:
    """Everything a page needs to drive the workflow, wired once per browser session."""

    graph: Any  # Compiled LangGraph graph (see graph_builder.build_graph's return type)
    repository: SQLiteExperimentRepository
    dataset_repository: FileDatasetRepository
    approve_use_case: ApproveStrategyUseCase
    upload_dir: Path
    weights: ObjectiveWeights  # the SAME instance actually used to rank strategies this session


def get_workflow_session() -> WorkflowSession:
    """Returns the cached WorkflowSession for this browser session, building
    it on first access. Every page should call this instead of constructing
    its own agents/nodes/repository.
    """
    if "workflow_session" not in st.session_state:
        settings = get_settings()

        connection = sqlite3.connect(str(settings.resolved(settings.database_path)), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        apply_schema(connection)
        repository = SQLiteExperimentRepository(connection)

        dataset_repository = FileDatasetRepository()
        weights = load_objective_weights(settings.resolved(settings.objective_weights_path))

        analysis_agent = AnalysisAgent(dataset_repository, ProfileDatasetUseCase(), GenerateStrategiesUseCase())
        evaluation_agent = EvaluationAgent(
            dataset_repository, EvaluateStrategiesUseCase(RealMetricsEngine(), weights)
        )
        decision_agent = DecisionReportingAgent(
            ExplainRecommendationUseCase(
                FallbackLLMClient(primary=OllamaLLMClient(), fallback=TemplateLLMClient())
            )
        )
        execution_node = ExecutionNode(
            dataset_repository, ExecuteCleaningUseCase(dataset_repository),
            output_dir=str(settings.resolved(settings.data_cleaned_dir)),
        )
        validation_node = ValidationNode(dataset_repository, ValidateCleanedDatasetUseCase())
        reporting_node = ReportingNode(
            GenerateReportUseCase(),
            report_dir=str(settings.resolved(settings.reports_dir)),
            script_dir=str(settings.resolved(settings.scripts_dir)),
        )

        graph = build_graph(
            analysis_agent, evaluation_agent, decision_agent,
            execution_node, validation_node, reporting_node, MemorySaver(),
        )

        upload_dir = settings.resolved(settings.data_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        st.session_state["workflow_session"] = WorkflowSession(
            graph=graph,
            repository=repository,
            dataset_repository=dataset_repository,
            approve_use_case=ApproveStrategyUseCase(repository),
            upload_dir=upload_dir,
            weights=weights,
        )

    session: WorkflowSession = st.session_state["workflow_session"]
    return session
