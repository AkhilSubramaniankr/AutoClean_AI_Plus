"""EvaluateStrategiesUseCase: scores and ranks candidate strategies.

Implements FR-4/FR-5. Depends on `IMetricsEngine` (a port -- see Phase 2,
Section 12, Dependency Inversion) rather than a concrete metrics
implementation, and on `ObjectiveWeights` (Domain value object) for the
weighted decision matrix. This use case has NO parameter of any LLM-client
type anywhere in its constructor or method signatures -- the architectural
enforcement of NFR-1 for the Evaluation Agent traces directly to this class.

PHASE 6 UPDATE: `execute()` now also takes the raw DataFrame, not just the
DatasetProfile, and delegates to `IMetricsEngine.score_all()` (see that
port's module docstring for why the interface changed from per-strategy to
batch scoring in Phase 6).
"""

from __future__ import annotations

import logging

import pandas as pd

from autoclean.application.ports.metrics_engine import IMetricsEngine
from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.value_objects.objective_weights import ObjectiveWeights

logger = logging.getLogger(__name__)


class EvaluateStrategiesUseCase:
    """Scores every candidate strategy and ranks them by weighted total."""

    def __init__(self, metrics_engine: IMetricsEngine, weights: ObjectiveWeights) -> None:
        self._metrics_engine = metrics_engine
        self._weights = weights

    def execute(
        self, strategies: list[CleaningStrategy], df: pd.DataFrame, profile: DatasetProfile
    ) -> tuple[dict[str, EvaluationScore], list[str]]:
        """Returns (scores keyed by strategy_id, strategy_ids ranked best-first)."""
        scores = self._metrics_engine.score_all(strategies, df, profile)
        weighted_totals = {
            strategy_id: score.compute_weighted_total(self._weights) for strategy_id, score in scores.items()
        }

        ranked_ids = sorted(weighted_totals, key=lambda sid: weighted_totals[sid], reverse=True)

        logger.info(
            "EvaluateStrategiesUseCase complete",
            extra={"strategy_count": len(strategies), "top_ranked": ranked_ids[0] if ranked_ids else None},
        )
        return scores, ranked_ids
