"""AnalysisAgent: thin LangGraph node wrapping Phase 4's real, deterministic
profiling/detection/generation logic via the Phase 5 use cases.

Per Phase 2 Section 1: agents contain NO business logic themselves -- this
class only translates WorkflowState <-> use case calls.
"""

from __future__ import annotations

from typing import Any

import logging
import uuid
from datetime import UTC, datetime

from autoclean.application.ports.dataset_repository import IDatasetRepository
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.orchestration.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """LangGraph node: dataset_path -> dataset_profile, detected_issues,
    candidate_strategies. Has NO dependency on IMetricsEngine or ILLMClient.
    """

    def __init__(
        self,
        dataset_repository: IDatasetRepository,
        profile_use_case: ProfileDatasetUseCase,
        generate_strategies_use_case: GenerateStrategiesUseCase,
    ) -> None:
        self._dataset_repository = dataset_repository
        self._profile_use_case = profile_use_case
        self._generate_strategies_use_case = generate_strategies_use_case

    def run(self, state: WorkflowState) -> dict[str, Any]:
        df = self._dataset_repository.load(state["dataset_path"])
        profile, issues = self._profile_use_case.execute(df)
        strategies = self._generate_strategies_use_case.execute(issues)

        audit_payload = {
            "row_count": profile.row_count,
            "issue_count": len(issues),
            "strategy_count": len(strategies),
        }
        audit_entry = {
            "id": str(uuid.uuid4()),
            "event_type": "dataset_profiled_and_strategies_generated",
            "actor": "AnalysisAgent",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": audit_payload,
        }
        logger.info("AnalysisAgent.run complete", extra=audit_payload)

        return {
            "dataset_profile": profile,
            "detected_issues": issues,
            "candidate_strategies": strategies,
            "current_node": "analysis_agent",
            "audit_log_entries": [*state.get("audit_log_entries", []), audit_entry],
        }
