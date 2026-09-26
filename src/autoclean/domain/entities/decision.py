"""Domain entity representing a human decision made during a workflow run.

Distinct from Experiment.approved_strategy_id (Phase 2, Section 7 design
decision): Experiment tracks the *final* approved strategy, while a Decision
row is recorded for *every* decision event, including rejections of earlier-
ranked strategies -- this is what makes "show me every rejection" queryable
against the DECISIONS table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class DecisionType(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Decision:
    """A single human approval/rejection event for one candidate strategy."""

    id: str
    experiment_id: str
    strategy_id: str
    decision_type: DecisionType
    decided_by: str
    decided_at: datetime
    rationale: str = ""

    def __post_init__(self) -> None:
        for field_name in ("id", "experiment_id", "strategy_id", "decided_by"):
            if not getattr(self, field_name):
                raise ValueError(f"Decision.{field_name} must not be empty")
