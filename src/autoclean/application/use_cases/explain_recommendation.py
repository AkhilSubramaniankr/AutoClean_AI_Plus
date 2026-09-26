"""ExplainRecommendationUseCase: generates the human-facing explanation.

Implements FR-7. Depends on `ILLMClient` (a port). This is the ONLY use
case in the entire Application layer permitted to depend on `ILLMClient` --
by construction, no other use case's constructor references it.

PHASE 7 UPDATE: `execute()` now also runs the explanation through
`check_consistency()` (Phase 7, new) and returns any warnings alongside the
explanation text, rather than just the text. This is a return-type
widening, not a port change (ExplainRecommendationUseCase is a concrete use
case, not an ABC) -- but it is flagged here per this project's convention
of documenting any change to an established call shape. DecisionReportingAgent
and its tests were updated accordingly.
"""

from __future__ import annotations

import logging
from typing import Any

from autoclean.application.ports.llm_client import ILLMClient
from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.infrastructure.llm.explanation_consistency_checker import check_consistency

logger = logging.getLogger(__name__)


class ExplainRecommendationUseCase:
    """Builds grounding context from real computed scores, then asks the
    LLM client to describe it in natural language. Never computes or
    modifies any score itself.
    """

    def __init__(self, llm_client: ILLMClient) -> None:
        self._llm_client = llm_client

    def execute(
        self,
        recommended_strategy: CleaningStrategy,
        recommended_score: EvaluationScore,
        alternative_strategies: list[tuple[CleaningStrategy, EvaluationScore]],
    ) -> tuple[str, list[str]]:
        """Returns (explanation_text, consistency_warnings)."""
        context: dict[str, Any] = {
            "recommended_strategy_name": recommended_strategy.name,
            "recommended_strategy_description": recommended_strategy.description,
            "recommended_score": recommended_score.as_dict(),
            "alternatives": [
                {
                    "name": strategy.name,
                    "description": strategy.description,
                    "score": score.as_dict(),
                }
                for strategy, score in alternative_strategies
            ],
        }
        explanation = self._llm_client.explain(context)
        warnings = check_consistency(explanation, context)
        if warnings:
            logger.warning(
                "ExplainRecommendationUseCase: consistency check flagged issues",
                extra={"strategy_id": recommended_strategy.strategy_id, "warning_count": len(warnings)},
            )
        logger.info(
            "ExplainRecommendationUseCase complete",
            extra={"strategy_id": recommended_strategy.strategy_id, "explanation_length": len(explanation)},
        )
        return explanation, warnings
