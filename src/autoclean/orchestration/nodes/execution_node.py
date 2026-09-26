"""ExecutionNode: real cleaning execution (Phase 8, replaces the Phase 5 stub).

Loads the raw dataset, applies the human-approved strategy via
ExecuteCleaningUseCase (which itself reuses StrategyExecutor -- the same
class RealMetricsEngine used to score candidates in Phase 6), and saves the
real cleaned output to disk.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from autoclean.application.ports.dataset_repository import IDatasetRepository
from autoclean.application.use_cases.execute_cleaning import ExecuteCleaningUseCase
from autoclean.orchestration.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class ExecutionNode:
    """LangGraph node: approved strategy -> real cleaned dataset, saved to disk."""

    def __init__(
        self,
        dataset_repository: IDatasetRepository,
        execute_use_case: ExecuteCleaningUseCase,
        output_dir: str = "data/cleaned",
    ) -> None:
        self._dataset_repository = dataset_repository
        self._execute_use_case = execute_use_case
        self._output_dir = output_dir

    def run(self, state: WorkflowState) -> dict[str, Any]:
        approved_id = state["recommended_strategy_id"]
        strategy = next(s for s in state["candidate_strategies"] if s.strategy_id == approved_id)

        df = self._dataset_repository.load(state["dataset_path"])
        output_path = f"{self._output_dir}/{state['experiment_id']}_cleaned.csv"
        _, saved_path = self._execute_use_case.execute(df, strategy, output_path)

        audit_entry = {
            "id": str(uuid.uuid4()),
            "event_type": "strategy_executed",
            "actor": "ExecutionNode",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {"approved_strategy_id": approved_id, "cleaned_dataset_path": saved_path},
        }
        logger.info("ExecutionNode.run complete", extra={"approved_strategy_id": approved_id})

        return {
            "approved_strategy_id": approved_id,
            "cleaned_dataset_path": saved_path,
            "current_node": "execution_node",
            "audit_log_entries": [*state.get("audit_log_entries", []), audit_entry],
        }
