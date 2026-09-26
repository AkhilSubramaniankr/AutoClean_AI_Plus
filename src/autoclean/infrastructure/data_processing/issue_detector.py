"""Deterministic per-column/per-dataset issue detection (Pandas/NumPy).

Converts a DataFrame + its DatasetProfile into a list of DataIssue entities
(Phase 1, FR-2). No LLM involvement (NFR-1).
"""

from __future__ import annotations

import logging

import pandas as pd

from autoclean.domain.entities.data_issue import DataIssue, IssueType
from autoclean.domain.entities.dataset import DatasetProfile

logger = logging.getLogger(__name__)


class IssueDetector:
    """Detects concrete `DataIssue` instances from a DataFrame and its profile.

    Design decision: this class takes both the raw DataFrame *and* an
    already-computed `DatasetProfile` (rather than recomputing summary
    statistics itself) so profiling and issue detection stay independently
    testable and so profiling is never accidentally computed twice in one
    workflow run.
    """

    def detect(self, df: pd.DataFrame, profile: DatasetProfile) -> list[DataIssue]:
        issues: list[DataIssue] = []
        issues.extend(self._detect_missing_value_issues(df, profile.row_count))
        issues.extend(self._detect_duplicate_issue(profile))
        issues.extend(self._detect_outlier_issues(df, profile.numeric_columns, profile.row_count))
        issues.extend(self._detect_dtype_issues(profile))

        logger.info(
            "Issue detection complete",
            extra={"issue_count": len(issues), "issue_types": [i.issue_type.value for i in issues]},
        )
        return issues

    @staticmethod
    def _detect_missing_value_issues(df: pd.DataFrame, row_count: int) -> list[DataIssue]:
        if row_count == 0:
            return []
        issues: list[DataIssue] = []
        missing_per_column = df.isna().sum()
        for column, missing_count in missing_per_column.items():
            if missing_count == 0:
                continue
            severity = float(missing_count) / row_count
            issues.append(
                DataIssue(
                    issue_type=IssueType.MISSING_VALUES,
                    column=str(column),
                    severity=round(severity, 4),
                    affected_row_count=int(missing_count),
                    description=(
                        f"Column '{column}' has {int(missing_count)} missing value(s) "
                        f"({severity:.1%} of rows)"
                    ),
                )
            )
        return issues

    @staticmethod
    def _detect_duplicate_issue(profile: DatasetProfile) -> list[DataIssue]:
        if profile.duplicate_row_count == 0 or profile.row_count == 0:
            return []
        severity = profile.duplicate_row_count / profile.row_count
        return [
            DataIssue(
                issue_type=IssueType.DUPLICATE_ROWS,
                column=None,
                severity=round(severity, 4),
                affected_row_count=profile.duplicate_row_count,
                description=(
                    f"{profile.duplicate_row_count} fully duplicated row(s) detected "
                    f"({severity:.1%} of rows)"
                ),
            )
        ]

    @staticmethod
    def _detect_outlier_issues(
        df: pd.DataFrame, numeric_columns: tuple[str, ...], row_count: int
    ) -> list[DataIssue]:
        if row_count == 0:
            return []
        issues: list[DataIssue] = []
        for column in numeric_columns:
            series = df[column].dropna()
            if series.empty:
                continue
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower_bound, upper_bound = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_count = int(outlier_mask.sum())
            if outlier_count == 0:
                continue
            severity = outlier_count / row_count
            issues.append(
                DataIssue(
                    issue_type=IssueType.OUTLIERS,
                    column=str(column),
                    severity=round(severity, 4),
                    affected_row_count=outlier_count,
                    description=(
                        f"Column '{column}' has {outlier_count} outlier value(s) outside "
                        f"[{lower_bound:.4g}, {upper_bound:.4g}] (IQR rule, 1.5x multiplier)"
                    ),
                )
            )
        return issues

    @staticmethod
    def _detect_dtype_issues(profile: DatasetProfile) -> list[DataIssue]:
        issues: list[DataIssue] = []
        for column, description in profile.dtype_issue_columns.items():
            issues.append(
                DataIssue(
                    issue_type=IssueType.INCONSISTENT_DTYPE,
                    column=column,
                    # Dtype issues affect the whole column's usability, so severity
                    # is fixed at 1.0 rather than computed from a row-level count.
                    severity=1.0,
                    affected_row_count=0,
                    description=description,
                )
            )
        return issues
