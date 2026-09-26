"""In-memory fake implementations of the Application ports, used only in
tests. Proves the Repository/Adapter patterns' actual payoff (Phase 2,
Section 12): use cases and agents can be fully tested with zero real
database, zero real LLM, zero real file I/O.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from autoclean.application.ports.dataset_repository import IDatasetRepository
from autoclean.application.ports.experiment_repository import IExperimentRepository
from autoclean.application.ports.llm_client import ILLMClient
from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.decision import Decision
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.entities.experiment import Experiment


class FakeDatasetRepository(IDatasetRepository):
    """Returns a pre-set DataFrame instead of reading from disk."""

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df
        self.loaded_paths: list[str] = []

    def load(self, path: str) -> pd.DataFrame:
        self.loaded_paths.append(path)
        return self._df

    def save(self, df: pd.DataFrame, path: str) -> str:
        return path


class FakeLLMClient(ILLMClient):
    """Returns a fixed string, recording the context it was given so tests
    can assert on exactly what evidence the use case passed it.
    """

    def __init__(self) -> None:
        self.last_context: dict[str, Any] | None = None

    def explain(self, context: dict[str, Any]) -> str:
        self.last_context = context
        return f"FAKE EXPLANATION for {context['recommended_strategy_name']}"


class InMemoryExperimentRepository(IExperimentRepository):
    """Stores everything in plain Python dicts/lists -- no SQLite involved."""

    def __init__(self) -> None:
        self.experiments: dict[str, Experiment] = {}
        self.strategies_by_experiment: dict[str, list[CleaningStrategy]] = {}
        self.scores_by_strategy: dict[str, tuple[EvaluationScore, float, dict]] = {}
        self.decisions: list[Decision] = []
        self.audit_events: list[AuditEvent] = []

    def save_experiment(self, experiment: Experiment) -> None:
        self.experiments[experiment.id] = experiment

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self.experiments.get(experiment_id)

    def list_experiments(self) -> list[Experiment]:
        return list(self.experiments.values())

    def save_candidate_strategies(self, experiment_id: str, strategies: list[CleaningStrategy]) -> None:
        self.strategies_by_experiment[experiment_id] = strategies

    def save_strategy_score(
        self, strategy_id: str, score: EvaluationScore, weighted_total: float, weights_used: dict
    ) -> None:
        self.scores_by_strategy[strategy_id] = (score, weighted_total, weights_used)

    def save_decision(self, decision: Decision) -> None:
        self.decisions.append(decision)

    def append_audit_event(self, event: AuditEvent) -> None:
        self.audit_events.append(event)

    def get_audit_trail(self, experiment_id: str) -> list[AuditEvent]:
        return [event for event in self.audit_events if event.experiment_id == experiment_id]
