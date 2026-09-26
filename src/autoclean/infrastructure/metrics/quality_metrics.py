"""quality_metrics.py: real data-quality-improvement scoring.

🟦 PAPER-motivated concept (analogous to Q_u(D_j)), 🟩 ORIGINAL implementation
-- the paper never specifies how to numerically score "quality," only that
methods have a quality value; this is this project's own formula.

Replaces Phase 5's PlaceholderMetricsEngine quality heuristic, which
estimated quality from strategy/profile properties alone (step count vs.
issue surface) without ever looking at what the strategy actually produced.
This module re-profiles the ACTUAL cleaned data and scores the real
reduction in issue severity.
"""

from __future__ import annotations

from autoclean.domain.entities.dataset import DatasetProfile

_DTYPE_ISSUE_PENALTY = 10.0


def _issue_severity_score(profile: DatasetProfile) -> float:
    """A single scalar summarizing "how much is wrong" with a profile,
    combining missing-value rate, duplicate rate, outlier rate (all already
    percentages/ratios computed by DatasetProfiler in Phase 4), and a fixed
    penalty per dtype-inconsistent column. Not itself an objective score --
    just an intermediate "badness" scalar compared before vs. after.
    """
    if profile.row_count == 0:
        return 0.0
    duplicate_pct = (profile.duplicate_row_count / profile.row_count) * 100.0
    outlier_pct = (profile.outlier_count / profile.row_count) * 100.0
    dtype_penalty = len(profile.dtype_issue_columns) * _DTYPE_ISSUE_PENALTY
    return profile.missing_value_pct + duplicate_pct + outlier_pct + dtype_penalty


def compute_quality_score(before: DatasetProfile, after: DatasetProfile) -> float:
    """Score in [0.0, 1.0]: 0.5 means "no change", 1.0 means "issue severity
    fully eliminated", <0.5 means the strategy made things WORSE (this can
    legitimately happen -- e.g. clipping outliers can occasionally introduce
    new duplicate values at the clip boundary, which is exactly the kind of
    honest trade-off this scoring is meant to surface, not hide).
    """
    before_severity = _issue_severity_score(before)
    after_severity = _issue_severity_score(after)

    if before_severity == 0.0:
        # Nothing was wrong to begin with; a strategy that keeps it that way
        # deserves full credit, not a division-by-zero or an arbitrary default.
        return 1.0 if after_severity == 0.0 else 0.0

    improvement_ratio = (before_severity - after_severity) / before_severity
    score = 0.5 + 0.5 * improvement_ratio
    return float(max(0.0, min(1.0, score)))
