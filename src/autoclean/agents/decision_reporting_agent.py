"""DecisionReportingAgent: thin LangGraph node handling the decision/
explanation phase (execution/validation/reporting are separate stub nodes
in `orchestration/nodes/`, per the Phase 2 graph design -- Phase 8 will give
those real logic).

Handles both the initial recommendation AND re-recommending the next-ranked
alternative after a rejection (Phase 2, Section 4: the rejection loop-back
edge routes back to this same agent, not to Evaluation/Analysis).
"""

from __future__ import annotations

from typing import Any

import logging
import uuid
from datetime import UTC, datetime

from autoclean.application.use_cases.explain_recommendation import ExplainRecommendationUseCase
from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.orchestration.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

_MAX_ALTERNATIVES_IN_EXPLANATION = 2


class DecisionReportingAgent:
    """LangGraph node: picks the best not-yet-rejected strategy and explains it.

    Sets `error` (not an exception) when every candidate has been rejected,
    so the graph can route to a graceful end rather than crashing (NFR-5).
    """

    def __init__(self, explain_use_case: ExplainRecommendationUseCase) -> None:
        self._explain_use_case = explain_use_case

    def run(self, state: WorkflowState) -> dict[str, Any]:
        rejected_ids = set(state.get("rejected_strategy_ids", []))
        previous_recommendation = state.get("recommended_strategy_id")
        if state.get("human_decision") == "rejected" and previous_recommendation:
            rejected_ids.add(previous_recommendation)

        ranked_ids = state.get("ranked_strategy_ids", [])
        remaining_ids = [sid for sid in ranked_ids if sid not in rejected_ids]

        audit_entries = list(state.get("audit_log_entries", []))

        if not remaining_ids:
            audit_entries.append(self._audit_entry("all_strategies_rejected", {"rejected_strategy_ids": list(rejected_ids)}))
            logger.warning("DecisionReportingAgent: all candidate strategies rejected")
            return {
                "error": "All candidate strategies have been rejected by the human reviewer.",
                "rejected_strategy_ids": list(rejected_ids),
                "current_node": "decision_reporting_agent",
                "audit_log_entries": audit_entries,
            }

        strategies_by_id = {s.strategy_id: s for s in state["candidate_strategies"]}
        recommended_id = remaining_ids[0]
        recommended_strategy = strategies_by_id[recommended_id]
        recommended_score = EvaluationScore(**state["strategy_scores"][recommended_id])

        alternatives: list[tuple[CleaningStrategy, EvaluationScore]] = [
            (strategies_by_id[sid], EvaluationScore(**state["strategy_scores"][sid]))
            for sid in remaining_ids[1 : 1 + _MAX_ALTERNATIVES_IN_EXPLANATION]
        ]

        explanation, consistency_warnings = self._explain_use_case.execute(
            recommended_strategy, recommended_score, alternatives
        )

        audit_entries.append(
            self._audit_entry(
                "recommendation_explained",
                {"recommended_strategy_id": recommended_id, "rejected_so_far": list(rejected_ids)},
            )
        )
        if consistency_warnings:
            audit_entries.append(
                self._audit_entry(
                    "explanation_consistency_warning",
                    {"recommended_strategy_id": recommended_id, "warnings": consistency_warnings},
                )
            )
        logger.info("DecisionReportingAgent.run complete", extra={"recommended_strategy_id": recommended_id})

        return {
            "recommended_strategy_id": recommended_id,
            "explanation_text": explanation,
            "explanation_consistency_warnings": consistency_warnings,
            "rejected_strategy_ids": list(rejected_ids),
            # Reset so the next pass through human_approval waits for a fresh decision.
            "human_decision": None,
            "current_node": "decision_reporting_agent",
            "audit_log_entries": audit_entries,
        }

    @staticmethod
    def _audit_entry(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "actor": "DecisionReportingAgent",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
