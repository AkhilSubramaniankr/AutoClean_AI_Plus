"""TEMPORARY placeholder IMetricsEngine implementation.

*** This is explicitly interim scaffolding, not Phase 6's real deliverable. ***

Phase 5's job is to prove the multi-agent workflow actually runs end-to-end
(including the human-approval interrupt) -- it is NOT the job of this phase
to solve multi-objective evaluation, which is Phase 6's dedicated scope
("Strategy Optimization Engine"). This class exists so `EvaluationAgent` has
something real (if simplistic) to call.

What IS real here: `data_quality_score` and `computational_cost_score` are
computed from actual, measurable properties of the strategy and profile
(number of steps, whether steps address detected issue types, baseline
status) -- not fabricated. What is NOT real: the other four objectives
(information_preservation, statistical_validity, fairness_impact,
downstream_ml) are fixed at a neutral 0.5 placeholder, since computing them
properly requires actually executing the strategy against the data (Phase 8)
and comparing before/after distributions (Phase 6) -- neither of which
exists yet. This is called out loudly, in logs and in the returned score's
provenance, specifically so nobody mistakes this phase's numbers for Phase
6's real ones.
"""

from __future__ import annotations

import logging

import pandas as pd

from autoclean.application.ports.metrics_engine import IMetricsEngine
from autoclean.domain.entities.cleaning_strategy import CleaningOperation, CleaningStrategy
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.evaluation_score import EvaluationScore

logger = logging.getLogger(__name__)

_PLACEHOLDER_SCORE = 0.5

# Operations considered "aggressive" (remove data) vs "conservative" (preserve
# row count) for the simple, interim cost/quality heuristics below.
_ROW_REMOVING_OPERATIONS = frozenset(
    {CleaningOperation.DROP_ROWS_WITH_MISSING, CleaningOperation.IQR_OUTLIER_REMOVAL}
)


class PlaceholderMetricsEngine(IMetricsEngine):
    """Interim IMetricsEngine: real quality/cost heuristics, placeholder rest.

    Replace with the full six-objective, EM-informed engine in Phase 6
    (`infrastructure/metrics/` — quality_metrics.py, cost_metrics.py,
    information_preservation.py, statistical_validity.py, fairness_metrics.py,
    downstream_ml_metrics.py, em_quality_estimator.py).
    """

    def score_all(
        self, strategies: list[CleaningStrategy], df: pd.DataFrame, original_profile: DatasetProfile
    ) -> dict[str, EvaluationScore]:
        """Phase 6 port signature (see application/ports/metrics_engine.py
        for why); `df` is accepted but unused here -- this placeholder never
        needed the raw data, only strategy/profile properties, and there is
        no value in changing that now that it is no longer the default
        engine (see RealMetricsEngine).
        """
        return {strategy.strategy_id: self.score(strategy, original_profile) for strategy in strategies}

    def score(self, strategy: CleaningStrategy, profile: DatasetProfile) -> EvaluationScore:
        data_quality_score = self._estimate_quality(strategy, profile)
        computational_cost_score = self._estimate_cost(strategy)

        score = EvaluationScore(
            data_quality_score=data_quality_score,
            computational_cost_score=computational_cost_score,
            information_preservation_score=_PLACEHOLDER_SCORE,
            statistical_validity_score=_PLACEHOLDER_SCORE,
            fairness_impact_score=_PLACEHOLDER_SCORE,
            downstream_ml_score=_PLACEHOLDER_SCORE,
            em_confidence=0.0,  # EM estimator not implemented until Phase 6
        )
        logger.info(
            "PlaceholderMetricsEngine scored strategy (Phase 6 will replace this)",
            extra={"strategy_id": strategy.strategy_id, "strategy_name": strategy.name},
        )
        return score

    @staticmethod
    def _estimate_quality(strategy: CleaningStrategy, profile: DatasetProfile) -> float:
        """More steps addressing more of the dataset's actual issue surface
        (dtype issues, missing values, outliers, duplicates) scores higher.
        A strategy with zero steps (pure no-op) scores at a fixed low value
        rather than zero, since "no issues existed" is a legitimate reason
        for a no-op strategy to still be reasonably scored.
        """
        real_steps = [step for step in strategy.steps if step.operation != CleaningOperation.NO_OP]
        if not real_steps:
            return 0.3

        issue_surface = max(
            1,
            int(profile.has_quality_issues)
            + len(profile.dtype_issue_columns)
            + int(profile.duplicate_row_count > 0)
            + int(profile.outlier_count > 0),
        )
        coverage = min(1.0, len(real_steps) / issue_surface)
        # Slight bonus for non-baseline strategies actually intervening, since a
        # baseline that merely coerces dtypes/dedupes leaves more addressable
        # issues (missing values, outliers) untouched.
        intervention_bonus = 0.0 if strategy.is_baseline else 0.1
        return round(min(1.0, 0.5 + 0.4 * coverage + intervention_bonus), 4)

    @staticmethod
    def _estimate_cost(strategy: CleaningStrategy) -> float:
        """Fewer steps and no row-removing operations scores higher (cheaper).
        This is a computational/latency PROXY (Phase 1, Section 7), not a
        literal USD cost as in the paper's Table 1 -- consistent with the
        scope decision made in Phase 1/Phase 2 to generalize "cost" away from
        per-API-call billing.
        """
        step_count = max(1, len(strategy.steps))
        row_removing_steps = sum(
            1 for step in strategy.steps if step.operation in _ROW_REMOVING_OPERATIONS
        )
        base_cost_score = max(0.1, 1.0 - 0.1 * (step_count - 1))
        penalty = 0.15 * row_removing_steps
        return round(max(0.1, min(1.0, base_cost_score - penalty)), 4)
