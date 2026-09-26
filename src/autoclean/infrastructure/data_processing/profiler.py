"""Deterministic dataset profiling (Pandas/NumPy). No LLM involvement (NFR-1).

Theory: profiling is the first step of the classic data-cleaning pipeline
(profile -> detect -> select strategy -> execute -> validate), and its output
(row/column counts, missing-value rate, duplicate count, per-column dtype)
is exactly the summary statistic set the paper's own sub-task decomposition
implicitly relies on before routing work to a method 🟦[PAPER-motivated],
even though the paper itself does not specify a profiling algorithm -- that
is original engineering in this project 🟩[ORIGINAL].
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from autoclean.domain.entities.dataset import DatasetProfile

logger = logging.getLogger(__name__)

# A column is treated as categorical if it is non-numeric, OR if it is
# numeric but has very few distinct values relative to row count (e.g. a
# 0/1 flag column encoded as int64). This threshold is a deliberately simple,
# documented heuristic -- not derived from the paper -- and is revisited if
# Phase 6 evaluation reveals it misclassifies a real dataset's columns.
_LOW_CARDINALITY_RATIO_THRESHOLD = 0.05
_LOW_CARDINALITY_ABSOLUTE_MAX = 20


class DatasetProfiler:
    """Computes a `DatasetProfile` from a pandas DataFrame.

    Stateless and side-effect free: `profile()` never mutates the input
    DataFrame. Kept deliberately simple and dependency-light (Pandas/NumPy
    only) so it is trivially unit-testable (NFR-7) without any database or
    LLM dependency.
    """

    def profile(self, df: pd.DataFrame) -> DatasetProfile:
        """Compute structural and quality statistics for `df`.

        Raises:
            ValueError: if `df` has zero columns (an empty-schema dataset
                cannot be meaningfully profiled or cleaned).
        """
        if df.shape[1] == 0:
            raise ValueError("Cannot profile a DataFrame with zero columns")

        row_count, column_count = df.shape
        total_cells = row_count * column_count
        missing_cells = int(df.isna().sum().sum())
        missing_value_pct = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0

        duplicate_row_count = int(df.duplicated(keep="first").sum())

        numeric_columns = tuple(df.select_dtypes(include="number").columns)
        categorical_columns = tuple(
            column
            for column in df.columns
            if column not in numeric_columns or self._is_low_cardinality(df[column], row_count)
        )
        # A column counted as "low cardinality numeric" should be categorical,
        # not both -- remove such columns from numeric_columns.
        numeric_columns = tuple(
            column for column in numeric_columns if column not in categorical_columns
        )

        outlier_count = self._count_outliers(df, numeric_columns)
        dtype_issue_columns = self._detect_dtype_issues(df)

        profile = DatasetProfile(
            row_count=row_count,
            column_count=column_count,
            missing_value_pct=round(missing_value_pct, 4),
            duplicate_row_count=duplicate_row_count,
            outlier_count=outlier_count,
            dtype_issue_columns=dtype_issue_columns,
            column_names=tuple(df.columns),
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
        )
        logger.info(
            "Dataset profiled",
            extra={
                "row_count": row_count,
                "column_count": column_count,
                "missing_value_pct": profile.missing_value_pct,
                "duplicate_row_count": duplicate_row_count,
                "outlier_count": outlier_count,
                "dtype_issue_column_count": len(dtype_issue_columns),
            },
        )
        return profile

    @staticmethod
    def _is_low_cardinality(series: pd.Series[Any], row_count: int) -> bool:
        if row_count == 0:
            return False
        distinct = series.nunique(dropna=True)
        return distinct <= _LOW_CARDINALITY_ABSOLUTE_MAX and (
            distinct / row_count
        ) <= _LOW_CARDINALITY_RATIO_THRESHOLD

    @staticmethod
    def _count_outliers(df: pd.DataFrame, numeric_columns: tuple[str, ...]) -> int:
        """Count outlier values across all numeric columns using the IQR rule
        (Q1 - 1.5*IQR, Q3 + 1.5*IQR). Standard, simple, and interpretable --
        see `docs/phase_deliverables/Phase4_Core_Data_Processing.md` Section 3
        for the alternatives considered (z-score, isolation forest) and why
        IQR was chosen as the profiling-stage default.
        """
        total_outliers = 0
        for column in numeric_columns:
            series = df[column].dropna()
            if series.empty:
                continue
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            total_outliers += int(((series < lower_bound) | (series > upper_bound)).sum())
        return total_outliers

    @staticmethod
    def _detect_dtype_issues(df: pd.DataFrame) -> dict[str, str]:
        """Detect columns whose dtype is `object` but whose non-null values
        are almost entirely numeric-looking strings -- a common sign that a
        column *should* be numeric but got parsed as text (e.g. due to a
        stray non-numeric value, thousands separators, or mixed formatting).
        """
        issues: dict[str, str] = {}
        for column in df.select_dtypes(include=["object", "string"]).columns:
            non_null = df[column].dropna()
            if non_null.empty:
                continue
            numeric_like = pd.to_numeric(non_null, errors="coerce")
            numeric_ratio = numeric_like.notna().mean()
            if 0.5 <= numeric_ratio < 1.0:
                issues[column] = (
                    f"Column appears numeric but is stored as text; "
                    f"{numeric_ratio:.1%} of non-null values parse as numbers"
                )
        return issues
