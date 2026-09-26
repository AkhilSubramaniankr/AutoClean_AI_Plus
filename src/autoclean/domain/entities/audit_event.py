"""Domain entity representing one entry in the audit trail (Phase 1, FR-13).

Every agent appends an AuditEvent to the shared WorkflowState on every
meaningful state mutation (Phase 2, Section 5), so the audit trail is a
natural by-product of normal workflow execution rather than a bolt-on
logging pass added after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    """A single, immutable audit-trail entry.

    Attributes:
        event_type: A short machine-readable event name, e.g.
            "dataset_profiled", "strategies_generated", "strategy_scored",
            "recommendation_explained", "human_decision_recorded",
            "strategy_executed", "validation_completed", "report_generated".
        actor: Which agent or component produced this event (e.g.
            "AnalysisAgent", "EvaluationAgent", "DecisionReportingAgent",
            "human:<decided_by>").
        payload: Structured, JSON-serializable event detail. Kept generic
            (dict) rather than a per-event-type subclass, matching the
            deliberate, bounded denormalization decision already made for
            the SQLite `event_payload_json` column (Phase 2, Section 7).
    """

    id: str
    experiment_id: str
    event_type: str
    actor: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("id", "experiment_id", "event_type", "actor"):
            if not getattr(self, field_name):
                raise ValueError(f"AuditEvent.{field_name} must not be empty")
