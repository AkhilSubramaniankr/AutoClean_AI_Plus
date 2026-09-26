"""Domain entity representing one end-to-end run of the AutoClean AI+ workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.dataset import DatasetProfile


class ExperimentStatus(str, Enum):
    """Lifecycle states of an Experiment, mirroring the LangGraph workflow
    (Phase 2, Section 4) so `EXPERIMENTS.status` in SQLite is always one of
    a known, closed set of values.
    """

    PROFILING = "profiling"
    EVALUATING = "evaluating"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class Experiment:
    """One complete AutoClean AI+ run: a dataset, its candidate strategies,
    and (eventually) the approved strategy and outcome.

    Mutable (not frozen), unlike the other entities in this package, because
    an Experiment's status and candidate list legitimately change as the
    LangGraph workflow (Phase 5) progresses through its nodes -- this mirrors
    the mutability of the shared WorkflowState itself (Phase 2, Section 6).
    """

    id: str
    dataset_name: str
    dataset_hash: str
    status: ExperimentStatus = ExperimentStatus.PROFILING
    dataset_profile: DatasetProfile | None = None
    candidate_strategies: list[CleaningStrategy] = field(default_factory=list)
    approved_strategy_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Experiment.id must not be empty")
        if not self.dataset_name:
            raise ValueError("Experiment.dataset_name must not be empty")

    def mark_completed(self, approved_strategy_id: str, completed_at: datetime | None = None) -> None:
        """Transition to COMPLETED and record the approved strategy.

        Raises:
            ValueError: if `approved_strategy_id` does not match any
                candidate strategy generated for this experiment -- an
                Experiment can only complete with a strategy it actually
                considered, never an invented one.
        """
        known_ids = {strategy.strategy_id for strategy in self.candidate_strategies}
        if approved_strategy_id not in known_ids:
            raise ValueError(
                f"approved_strategy_id {approved_strategy_id!r} was not among this "
                f"experiment's candidate strategies {sorted(known_ids)}"
            )
        self.approved_strategy_id = approved_strategy_id
        self.status = ExperimentStatus.COMPLETED
        self.completed_at = completed_at or datetime.now(UTC)
