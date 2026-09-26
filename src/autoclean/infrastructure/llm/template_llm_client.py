"""TEMPORARY placeholder ILLMClient implementation: deterministic templates,
NOT a real language model call.

*** This is explicitly interim scaffolding, not Phase 7's real deliverable. ***

Phase 5's job is to prove the Decision & Reporting Agent's plumbing works
(it receives real scores, produces *some* explanation string, and the
human-approval interrupt correctly gates progress) -- it is NOT this
phase's job to integrate Ollama, which is Phase 7's dedicated scope
("Explainability & Decision Support").

Every number that appears in the generated text is read directly from
`context` (itself built by `ExplainRecommendationUseCase` from real,
already-computed `EvaluationScore` values) -- so even though the prose is
templated rather than LLM-generated, it contains no fabricated figures.
This is a deliberately weaker but strictly honest stand-in.
"""

from __future__ import annotations

import logging
from typing import Any

from autoclean.application.ports.llm_client import ILLMClient

logger = logging.getLogger(__name__)


class TemplateLLMClient(ILLMClient):
    """Interim ILLMClient: string-templated, not LLM-generated.

    Replace with an Ollama-backed implementation (via `langchain-ollama`'s
    `ChatOllama`) in Phase 7.
    """

    def explain(self, context: dict[str, Any]) -> str:
        name = context["recommended_strategy_name"]
        description = context["recommended_strategy_description"]
        score = context["recommended_score"]
        alternatives = context.get("alternatives", [])

        lines = [
            f"Recommended strategy: {name}",
            description,
            "",
            "Scores (0.0-1.0, higher is better; computed by RealMetricsEngine, "
            "Phase 6 -- fairness/downstream-ML use a heuristically auto-selected "
            "column pending Phase 9's UI for explicit user selection):",
            f"  - Data quality:              {score['data_quality_score']:.2f}",
            f"  - Computational cost:        {score['computational_cost_score']:.2f}",
            f"  - Information preservation:  {score['information_preservation_score']:.2f}",
            f"  - Statistical validity:      {score['statistical_validity_score']:.2f}",
            f"  - Fairness impact:           {score['fairness_impact_score']:.2f}",
            f"  - Downstream ML performance: {score['downstream_ml_score']:.2f}",
        ]

        if alternatives:
            lines.append("")
            lines.append(f"Compared against {len(alternatives)} alternative(s):")
            for alt in alternatives:
                alt_score = alt["score"]
                lines.append(
                    f"  - {alt['name']}: data quality {alt_score['data_quality_score']:.2f}, "
                    f"cost {alt_score['computational_cost_score']:.2f}"
                )

        explanation = "\n".join(lines)
        logger.info(
            "TemplateLLMClient generated explanation (Phase 7 will replace this with Ollama)",
            extra={"strategy_name": name, "explanation_length": len(explanation)},
        )
        return explanation
