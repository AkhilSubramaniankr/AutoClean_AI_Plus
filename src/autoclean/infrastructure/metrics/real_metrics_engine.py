"""RealMetricsEngine: the Phase 6 replacement for Phase 5's
PlaceholderMetricsEngine, implementing all six objectives (Phase 1, FR-4)
with real computation against actual cleaned data, plus the paper's EM
confidence estimator (Eqs. 2-6).

Orchestration note (Phase 6 port revision -- see application/ports/metrics_engine.py
module docstring for the full rationale): unlike a per-strategy `score()`
call, this engine scores an entire BATCH of strategies at once via
`score_all()`, because (a) the EM estimator structurally requires multiple
strategies' labels over the same rows simultaneously, and (b) it lets the
engine profile/execute each strategy exactly once and reuse the original
DataFrame's profile across all six per-strategy metric computations, rather
than repeating that work per strategy.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from autoclean.application.ports.metrics_engine import IMetricsEngine
from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
from autoclean.infrastructure.data_processing.strategy_executor import StrategyExecutor
from autoclean.infrastructure.metrics import (
    cost_metrics,
    downstream_ml_metrics,
    fairness_metrics,
    information_preservation,
    quality_metrics,
    statistical_validity,
)
from autoclean.infrastructure.metrics.em_quality_estimator import EMQualityEstimator

logger = logging.getLogger(__name__)

_ROW_CHANGE_TOLERANCE = 1e-9


class RealMetricsEngine(IMetricsEngine):
    """Real, six-objective, EM-informed strategy evaluator.

    `sensitive_column` and `target_column` are optional overrides for the
    fairness and downstream-ML objectives respectively; when omitted, each
    is auto-selected via a documented heuristic (see fairness_metrics.py and
    downstream_ml_metrics.py) -- a stand-in for Phase 9's eventual UI-driven
    selection, not a substitute for it.
    """

    def __init__(
        self,
        sensitive_column: str | None = None,
        target_column: str | None = None,
        em_max_iterations: int = 50,
        em_convergence_tolerance: float = 1e-4,
    ) -> None:
        self._sensitive_column_override = sensitive_column
        self._target_column_override = target_column
        self._profiler = DatasetProfiler()
        self._issue_detector = IssueDetector()
        self._executor = StrategyExecutor()
        self._em_estimator = EMQualityEstimator(em_max_iterations, em_convergence_tolerance)

    def score_all(
        self, strategies: list[CleaningStrategy], df: pd.DataFrame, original_profile: DatasetProfile
    ) -> dict[str, EvaluationScore]:
        cleaned_by_strategy: dict[str, pd.DataFrame] = {
            strategy.strategy_id: self._executor.apply(df, strategy) for strategy in strategies
        }

        sensitive_column = self._sensitive_column_override or fairness_metrics.select_default_sensitive_column(
            df, original_profile.categorical_columns
        )
        target_column = self._target_column_override or downstream_ml_metrics.select_default_target_column(
            df, original_profile.categorical_columns, exclude=sensitive_column
        )

        row_clean_labels = {
            strategy_id: self._compute_row_clean_labels(df, cleaned_df)
            for strategy_id, cleaned_df in cleaned_by_strategy.items()
        }
        em_confidences = self._em_estimator.estimate(row_clean_labels)

        scores: dict[str, EvaluationScore] = {}
        for strategy in strategies:
            cleaned_df = cleaned_by_strategy[strategy.strategy_id]
            cleaned_profile = self._profiler.profile(cleaned_df) if len(cleaned_df.columns) > 0 else original_profile

            scores[strategy.strategy_id] = EvaluationScore(
                data_quality_score=float(
                    quality_metrics.compute_quality_score(original_profile, cleaned_profile)
                ),
                computational_cost_score=float(
                    cost_metrics.compute_cost_score(strategy, original_profile.row_count)
                ),
                information_preservation_score=float(
                    information_preservation.compute_information_preservation_score(df, cleaned_df)
                ),
                statistical_validity_score=float(
                    statistical_validity.compute_statistical_validity_score(
                        df, cleaned_df, original_profile.numeric_columns
                    )
                ),
                fairness_impact_score=float(
                    fairness_metrics.compute_fairness_score(df, cleaned_df, sensitive_column)
                ),
                downstream_ml_score=float(
                    downstream_ml_metrics.compute_downstream_ml_score(
                        cleaned_df, target_column, original_profile.numeric_columns
                    )
                ),
                em_confidence=float(em_confidences.get(strategy.strategy_id, 0.5)),
            )

        logger.info(
            "RealMetricsEngine.score_all complete",
            extra={
                "strategy_count": len(strategies),
                "sensitive_column": sensitive_column,
                "target_column": target_column,
            },
        )
        return scores

    @staticmethod
    def _compute_row_clean_labels(original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> np.ndarray[Any, Any]:
        """1 = row survived AND every numeric cell is unchanged ("judged
        clean" by this strategy); 0 = row was removed OR at least one
        numeric cell was altered (imputed/clipped/coerced). Indexed to
        align with `original_df`'s row order, which is what the EM
        estimator requires (same rows, same order, across every strategy).
        """
        numeric_columns = list(original_df.select_dtypes(include="number").columns)
        labels = np.zeros(len(original_df), dtype=int)

        survived_mask = original_df.index.isin(cleaned_df.index)
        if len(numeric_columns) == 0:
            labels[survived_mask.to_numpy() if hasattr(survived_mask, "to_numpy") else survived_mask] = 1
            return labels

        common_index = original_df.index[survived_mask]
        if len(common_index) > 0:
            original_aligned = original_df.loc[common_index, numeric_columns]
            cleaned_aligned = cleaned_df.loc[common_index, numeric_columns]
            both_missing = original_aligned.isna() & cleaned_aligned.isna()
            unchanged_per_cell = (original_aligned == cleaned_aligned) | both_missing
            unchanged_per_row = unchanged_per_cell.all(axis=1)
            positions = original_df.index.get_indexer(common_index)
            labels[positions] = unchanged_per_row.to_numpy().astype(int)

        return labels
