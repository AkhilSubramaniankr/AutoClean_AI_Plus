"""ValidateCleanedDatasetUseCase: validates the executed strategy's real
output (Phase 1, FR-10 continued / "validate the cleaned dataset").

Implements FR-10's validation half. Depends on the same `DatasetProfiler`
and `IssueDetector` used throughout this project (Phase 4), and reuses
`quality_metrics.compute_quality_score` -- the SAME function the Evaluation
Agent uses to rank candidates in Phase 6 -- so "quality improvement" means
exactly one thing everywhere in this codebase, not a slightly different
definition for ranking vs. for validating.
"""

from __future__ import annotations

import logging

import pandas as pd

from autoclean.domain.entities.validation_report import ValidationReport
from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
from autoclean.infrastructure.metrics.quality_metrics import compute_quality_score

logger = logging.getLogger(__name__)

_DEFAULT_QUALITY_THRESHOLD = 0.5  # "0.5" = "did not make things worse" (see quality_metrics.py's own scale)


class ValidateCleanedDatasetUseCase:
    """Re-profiles the cleaned dataset and checks it against real, computed criteria."""

    def __init__(
        self,
        profiler: DatasetProfiler | None = None,
        issue_detector: IssueDetector | None = None,
    ) -> None:
        self._profiler = profiler or DatasetProfiler()
        self._issue_detector = issue_detector or IssueDetector()

    def execute(
        self,
        original_df: pd.DataFrame,
        cleaned_df: pd.DataFrame,
        quality_threshold: float = _DEFAULT_QUALITY_THRESHOLD,
    ) -> ValidationReport:
        schema_consistent = set(original_df.columns) == set(cleaned_df.columns)

        original_profile = self._profiler.profile(original_df)
        cleaned_profile = (
            self._profiler.profile(cleaned_df) if len(cleaned_df.columns) > 0 else original_profile
        )
        quality_score = compute_quality_score(original_profile, cleaned_profile)
        quality_threshold_met = quality_score >= quality_threshold

        remaining_issues = (
            self._issue_detector.detect(cleaned_df, cleaned_profile) if schema_consistent else []
        )

        notes = self._build_notes(schema_consistent, quality_score, quality_threshold, len(remaining_issues))

        report = ValidationReport(
            schema_consistent=schema_consistent,
            quality_threshold_met=quality_threshold_met,
            quality_score=quality_score,
            quality_threshold=quality_threshold,
            row_count_before=len(original_df),
            row_count_after=len(cleaned_df),
            remaining_issue_count=len(remaining_issues),
            notes=notes,
        )
        logger.info(
            "ValidateCleanedDatasetUseCase complete",
            extra={"passed": report.passed, "quality_score": quality_score, "remaining_issues": len(remaining_issues)},
        )
        return report

    @staticmethod
    def _build_notes(
        schema_consistent: bool, quality_score: float, quality_threshold: float, remaining_issue_count: int
    ) -> str:
        if not schema_consistent:
            return "Schema changed unexpectedly during cleaning -- this indicates a defect, not a normal outcome."
        verdict = "met" if quality_score >= quality_threshold else "NOT met"
        return (
            f"Quality score {quality_score:.2f} vs. threshold {quality_threshold:.2f} ({verdict}). "
            f"{remaining_issue_count} issue(s) remain in the cleaned data."
        )
