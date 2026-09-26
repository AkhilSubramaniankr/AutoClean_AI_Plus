"""Deterministic candidate cleaning strategy generation (Phase 1, FR-3).

Given a list of detected DataIssue instances, produces multiple candidate
CleaningStrategy objects: always a low-cost "baseline" strategy 🟦[PAPER-
motivated -- analogous to the paper's low-cost baseline assignment before its
greedy-upgrade pass] plus one or more "upgraded" strategies that actually
address the detected issues 🟩[ORIGINAL strategy-composition logic; the paper
never composes multi-step whole-dataset strategies, only per-sub-task method
routing].
"""

from __future__ import annotations

import logging
import uuid

from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)
from autoclean.domain.entities.data_issue import DataIssue, IssueType

logger = logging.getLogger(__name__)


class StrategyGenerator:
    """Generates candidate `CleaningStrategy` objects from detected issues.

    Design decision: this is a Factory-pattern component (Phase 2, Section 12
    names `GenerateStrategiesUseCase` as the Factory; this class is the
    concrete, deterministic logic that use case will call in Phase 5). It is
    intentionally rule-based rather than search-based (e.g. no combinatorial
    exploration of every possible step ordering) -- see
    `docs/phase_deliverables/Phase4_Core_Data_Processing.md` Section 4 for
    the alternatives considered and why a small, fixed set of named
    strategies was chosen over combinatorial generation for a
    single-analyst, interactively-reviewed tool.
    """

    def generate(self, issues: list[DataIssue]) -> list[CleaningStrategy]:
        """Generate candidate strategies. Always returns at least 2 strategies
        (Phase 1, FR-3), even when `issues` is empty (baseline + a documented
        no-op "alternative" is still 2 comparable candidates in that edge case).
        """
        strategies: list[CleaningStrategy] = [self._build_baseline_strategy(issues)]

        conservative = self._build_conservative_strategy(issues)
        if conservative is not None:
            strategies.append(conservative)

        aggressive = self._build_aggressive_strategy(issues)
        if aggressive is not None:
            strategies.append(aggressive)

        if len(strategies) < 2:
            # Only reachable when `issues` is empty and both conservative/
            # aggressive builders therefore returned None. Still satisfy FR-3
            # by offering an explicit, documented second no-op candidate.
            strategies.append(self._build_explicit_no_op_strategy())

        logger.info(
            "Candidate strategies generated",
            extra={"strategy_count": len(strategies), "issue_count": len(issues)},
        )
        return strategies

    # ------------------------------------------------------------------
    # Strategy builders
    # ------------------------------------------------------------------

    @staticmethod
    def _new_id() -> str:
        return str(uuid.uuid4())

    def _build_baseline_strategy(self, issues: list[DataIssue]) -> CleaningStrategy:
        """The minimal-intervention strategy: only fixes dtype issues (a
        prerequisite for any numeric analysis at all) and drops exact
        duplicate rows, but does NOT impute missing values or touch outliers.
        Cheapest strategy in the candidate set -- analogous in spirit to the
        paper's low-cost baseline before its greedy-upgrade pass 🟦.
        """
        steps: list[CleaningStep] = []
        for issue in issues:
            if issue.issue_type == IssueType.INCONSISTENT_DTYPE and issue.column:
                steps.append(
                    CleaningStep(operation=CleaningOperation.TYPE_COERCION, target_column=issue.column)
                )
            elif issue.issue_type == IssueType.DUPLICATE_ROWS:
                steps.append(CleaningStep(operation=CleaningOperation.EXACT_DEDUPLICATION))

        if not steps:
            steps.append(CleaningStep(operation=CleaningOperation.NO_OP))

        return CleaningStrategy(
            strategy_id=self._new_id(),
            name="Baseline (minimal intervention)",
            steps=tuple(steps),
            is_baseline=True,
            description=(
                "Fixes data-type inconsistencies and removes exact duplicate rows only. "
                "Does not impute missing values or treat outliers -- the lowest-cost "
                "candidate, comparable to the paper's low-cost baseline assignment."
            ),
        )

    def _build_conservative_strategy(self, issues: list[DataIssue]) -> CleaningStrategy | None:
        """Addresses missing values (median/mode imputation, which preserves
        row count and is statistically conservative) and outliers via
        clipping (which preserves row count, unlike removal). No strategy is
        built if there is nothing beyond what the baseline already covers.
        """
        steps: list[CleaningStep] = []
        for issue in issues:
            if issue.issue_type == IssueType.INCONSISTENT_DTYPE and issue.column:
                steps.append(
                    CleaningStep(operation=CleaningOperation.TYPE_COERCION, target_column=issue.column)
                )
            elif issue.issue_type == IssueType.DUPLICATE_ROWS:
                steps.append(CleaningStep(operation=CleaningOperation.EXACT_DEDUPLICATION))
            elif issue.issue_type == IssueType.MISSING_VALUES and issue.column:
                steps.append(
                    CleaningStep(
                        operation=CleaningOperation.MEDIAN_IMPUTATION, target_column=issue.column
                    )
                )
            elif issue.issue_type == IssueType.OUTLIERS and issue.column:
                steps.append(
                    CleaningStep(
                        operation=CleaningOperation.IQR_OUTLIER_CLIPPING,
                        target_column=issue.column,
                        parameters={"iqr_multiplier": 1.5},
                    )
                )

        if not steps:
            return None

        return CleaningStrategy(
            strategy_id=self._new_id(),
            name="Conservative (impute + clip)",
            steps=tuple(steps),
            is_baseline=False,
            description=(
                "Imputes missing values with the column median/mode and clips outliers to "
                "the IQR bounds. Preserves row count and total information volume, at the "
                "cost of introducing some imputed/clipped values."
            ),
        )

    def _build_aggressive_strategy(self, issues: list[DataIssue]) -> CleaningStrategy | None:
        """Removes problematic rows/values outright: drops rows with missing
        values and removes (rather than clips) outlier rows. Maximizes the
        purity of remaining data at the cost of reduced row count --
        deliberately positioned as the higher-information-loss, higher-
        statistical-purity alternative for the Evaluation Agent (Phase 6) to
        score against the conservative strategy on the information-
        preservation and statistical-validity objectives.
        """
        steps: list[CleaningStep] = []
        has_missing_or_outliers = False
        for issue in issues:
            if issue.issue_type == IssueType.INCONSISTENT_DTYPE and issue.column:
                steps.append(
                    CleaningStep(operation=CleaningOperation.TYPE_COERCION, target_column=issue.column)
                )
            elif issue.issue_type == IssueType.DUPLICATE_ROWS:
                steps.append(CleaningStep(operation=CleaningOperation.EXACT_DEDUPLICATION))
            elif issue.issue_type == IssueType.MISSING_VALUES and issue.column:
                steps.append(
                    CleaningStep(
                        operation=CleaningOperation.DROP_ROWS_WITH_MISSING,
                        target_column=issue.column,
                    )
                )
                has_missing_or_outliers = True
            elif issue.issue_type == IssueType.OUTLIERS and issue.column:
                steps.append(
                    CleaningStep(
                        operation=CleaningOperation.IQR_OUTLIER_REMOVAL,
                        target_column=issue.column,
                        parameters={"iqr_multiplier": 1.5},
                    )
                )
                has_missing_or_outliers = True

        if not has_missing_or_outliers:
            # No meaningful difference from the conservative/baseline strategy
            # would result; don't generate a redundant third candidate.
            return None

        return CleaningStrategy(
            strategy_id=self._new_id(),
            name="Aggressive (drop + remove)",
            steps=tuple(steps),
            is_baseline=False,
            description=(
                "Drops rows with missing values and removes outlier rows entirely. "
                "Maximizes remaining-data purity at the cost of reduced row count / "
                "information preservation."
            ),
        )

    def _build_explicit_no_op_strategy(self) -> CleaningStrategy:
        return CleaningStrategy(
            strategy_id=self._new_id(),
            name="No-op (no issues detected)",
            steps=(CleaningStep(operation=CleaningOperation.NO_OP),),
            is_baseline=False,
            description="No data-quality issues were detected; this strategy makes no changes.",
        )
