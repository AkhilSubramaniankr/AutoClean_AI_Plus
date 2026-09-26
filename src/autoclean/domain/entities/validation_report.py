"""Domain entity representing the outcome of validating a cleaned dataset
(Phase 2, Section 6 class diagram named this entity; not implemented until
Phase 8, since there was nothing real to validate before the execution
logic existed).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationReport:
    """Result of comparing a cleaned dataset against its original.

    Attributes:
        schema_consistent: True if cleaning did not change the set of
            columns -- every CleaningOperation in this project's vocabulary
            (Phase 4/6) only touches rows or values, never adds/removes
            columns, so this should always be True; a False here would
            indicate a genuine defect worth investigating, not a normal
            outcome.
        quality_threshold_met: True if the real quality-improvement score
            (reusing `quality_metrics.compute_quality_score`, the SAME
            function the Evaluation Agent uses to rank candidates in the
            first place -- one definition of "quality improvement," used
            consistently everywhere) meets or exceeds `quality_threshold`.
        quality_score: The actual computed quality score (Phase 6's
            quality_metrics.compute_quality_score), included so a human can
            see the real number the pass/fail judgment was based on.
        quality_threshold: The threshold that was checked against.
        row_count_before: Original row count.
        row_count_after: Cleaned row count.
        remaining_issue_count: Number of DataIssue instances still detected
            in the cleaned data (re-run through the same IssueDetector used
            during analysis) -- 0 does not necessarily mean "perfect," since
            some strategies deliberately trade off some issues against
            others (Phase 4's Conservative/Aggressive design).
        notes: Human-readable summary combining the above into one sentence,
            surfaced directly in the executive report (Phase 8) without
            needing an LLM to phrase it.
    """

    schema_consistent: bool
    quality_threshold_met: bool
    quality_score: float
    quality_threshold: float
    row_count_before: int
    row_count_after: int
    remaining_issue_count: int
    notes: str

    def __post_init__(self) -> None:
        if not (0.0 <= self.quality_score <= 1.0):
            raise ValueError(f"quality_score must be within [0.0, 1.0], got {self.quality_score}")
        if self.row_count_before < 0 or self.row_count_after < 0:
            raise ValueError("row counts cannot be negative")
        if self.remaining_issue_count < 0:
            raise ValueError("remaining_issue_count cannot be negative")

    @property
    def passed(self) -> bool:
        """Overall pass/fail: both structural and quality checks must hold."""
        return self.schema_consistent and self.quality_threshold_met
