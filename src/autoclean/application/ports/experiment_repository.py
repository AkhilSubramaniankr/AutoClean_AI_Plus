"""Port interface for persisting Experiments, candidate strategies, scores,
decisions, audit events, and reports.

Design decision (Phase 2, Section 12, Repository pattern): use cases and
agents depend on this ABC, never on `sqlite3` or SQLAlchemy directly. This
is what makes the Application layer testable with an in-memory fake
repository, with no real database required (see Phase 5 unit tests).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.decision import Decision
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.entities.experiment import Experiment


class IExperimentRepository(ABC):
    """Persistence operations needed across the full Experiment lifecycle."""

    @abstractmethod
    def save_experiment(self, experiment: Experiment) -> None:
        """Insert or update the experiment's own row (upsert semantics)."""
        raise NotImplementedError

    @abstractmethod
    def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Return the Experiment, or None if no such ID exists."""
        raise NotImplementedError

    @abstractmethod
    def list_experiments(self) -> list[Experiment]:
        """Return all experiments, most recently created first."""
        raise NotImplementedError

    @abstractmethod
    def save_candidate_strategies(
        self, experiment_id: str, strategies: list[CleaningStrategy]
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_strategy_score(
        self, strategy_id: str, score: EvaluationScore, weighted_total: float, weights_used: dict[str, Any]
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_decision(self, decision: Decision) -> None:
        raise NotImplementedError

    @abstractmethod
    def append_audit_event(self, event: AuditEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_audit_trail(self, experiment_id: str) -> list[AuditEvent]:
        raise NotImplementedError
