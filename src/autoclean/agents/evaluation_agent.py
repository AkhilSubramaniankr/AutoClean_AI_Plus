"""EvaluationAgent: thin LangGraph node wrapping EvaluateStrategiesUseCase.

ARCHITECTURAL RULE, enforced here structurally: this constructor has NO
parameter of type ILLMClient anywhere -- inspect its signature yourself
(`inspect.signature(EvaluationAgent.__init__)`) to confirm there is no way
to inject an LLM client into this class, by construction, not convention.

PHASE 6 UPDATE: this agent now also depends on `IDatasetRepository`, to
reload the raw dataset from `dataset_path` (the Phase 6 metrics engine needs
actual data, not just the profile -- see application/ports/metrics_engine.py).
Reloading rather than threading the DataFrame through WorkflowState keeps
the shared state small and cleanly checkpoint-serializable (a design
decision already made in Phase 5); re-reading a CSV is cheap relative to
the six-objective computation that follows it.
"""

from __future__ import annotations

from typing import Any

import logging
import uuid
from datetime import UTC, datetime

from autoclean.application.ports.dataset_repository import IDatasetRepository
from autoclean.application.use_cases.evaluate_strategies import EvaluateStrategiesUseCase
from autoclean.orchestration.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class EvaluationAgent:
    """LangGraph node: candidate_strategies + dataset_profile -> strategy_scores,
    ranked_strategy_ids.
    """

    def __init__(
        self, dataset_repository: IDatasetRepository, evaluate_use_case: EvaluateStrategiesUseCase
    ) -> None:
        self._dataset_repository = dataset_repository
        self._evaluate_use_case = evaluate_use_case

    def run(self, state: WorkflowState) -> dict[str, Any]:
        df = self._dataset_repository.load(state["dataset_path"])
        scores, ranked_ids = self._evaluate_use_case.execute(
            state["candidate_strategies"], df, state["dataset_profile"]
        )
        scores_as_dicts = {strategy_id: score.as_dict() for strategy_id, score in scores.items()}

        audit_entry = {
            "id": str(uuid.uuid4()),
            "event_type": "strategies_scored_and_ranked",
            "actor": "EvaluationAgent",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {"ranked_strategy_ids": ranked_ids},
        }
        logger.info("EvaluationAgent.run complete", extra={"top_ranked": ranked_ids[0] if ranked_ids else None})

        return {
            "strategy_scores": scores_as_dicts,
            "ranked_strategy_ids": ranked_ids,
            "current_node": "evaluation_agent",
            "audit_log_entries": [*state.get("audit_log_entries", []), audit_entry],
        }
