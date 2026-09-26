"""ApproveStrategyUseCase: records a human decision (Phase 1, FR-9).

Depends on `IExperimentRepository` to persist the Decision and append an
AuditEvent -- this is what makes every approval/rejection queryable later
(FR-13, FR-15), not just an in-memory workflow-state field that disappears
when the process ends.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from autoclean.application.ports.experiment_repository import IExperimentRepository
from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.decision import Decision, DecisionType

logger = logging.getLogger(__name__)


class ApproveStrategyUseCase:
    """Records a human approval or rejection decision for one candidate strategy."""

    def __init__(self, repository: IExperimentRepository) -> None:
        self._repository = repository

    def execute(
        self,
        experiment_id: str,
        strategy_id: str,
        decision_type: DecisionType,
        decided_by: str,
        rationale: str = "",
    ) -> Decision:
        decision = Decision(
            id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            strategy_id=strategy_id,
            decision_type=decision_type,
            decided_by=decided_by,
            decided_at=datetime.now(UTC),
            rationale=rationale,
        )
        self._repository.save_decision(decision)
        self._repository.append_audit_event(
            AuditEvent(
                id=str(uuid.uuid4()),
                experiment_id=experiment_id,
                event_type="human_decision_recorded",
                actor=f"human:{decided_by}",
                payload={"strategy_id": strategy_id, "decision": decision_type.value, "rationale": rationale},
            )
        )
        logger.info(
            "ApproveStrategyUseCase complete",
            extra={"experiment_id": experiment_id, "strategy_id": strategy_id, "decision": decision_type.value},
        )
        return decision
