"""ValidationNode: real validation (Phase 8, replaces the Phase 5 stub).

Reloads the original data, loads the real cleaned output ExecutionNode just
wrote, and runs ValidateCleanedDatasetUseCase to produce a real
ValidationReport -- schema consistency and quality-threshold checks against
actual computed values, not a hardcoded "always passes."
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from autoclean.application.ports.dataset_repository import IDatasetRepository
from autoclean.application.use_cases.validate_cleaned_dataset import ValidateCleanedDatasetUseCase
from autoclean.orchestration.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class ValidationNode:
    """LangGraph node: cleaned dataset -> a real ValidationReport."""

    def __init__(
        self,
        dataset_repository: IDatasetRepository,
        validate_use_case: ValidateCleanedDatasetUseCase,
        quality_threshold: float = 0.5,
    ) -> None:
        self._dataset_repository = dataset_repository
        self._validate_use_case = validate_use_case
        self._quality_threshold = quality_threshold

    def run(self, state: WorkflowState) -> dict[str, Any]:
        original_df = self._dataset_repository.load(state["dataset_path"])
        cleaned_df = self._dataset_repository.load(state["cleaned_dataset_path"])

        report = self._validate_use_case.execute(original_df, cleaned_df, self._quality_threshold)

        audit_entry = {
            "id": str(uuid.uuid4()),
            "event_type": "validation_completed",
            "actor": "ValidationNode",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": asdict(report),
        }
        logger.info("ValidationNode.run complete", extra={"passed": report.passed})

        return {
            "validation_passed": report.passed,
            "validation_report": report,
            "current_node": "validation_node",
            "audit_log_entries": [*state.get("audit_log_entries", []), audit_entry],
        }
