"""Domain entities describing a dataset and its profile.

Pure Python only -- no Pandas, no I/O. Profiling a real dataset (which does
require Pandas/NumPy) happens in the Infrastructure layer
(`infrastructure/data_processing/profiler.py`); this module only defines the
*shape* of the result, per Clean Architecture's dependency-inversion rule
(Phase 2, Section 2): the Domain layer must not depend on any framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetProfile:
    """Structural and quality summary of a dataset at a point in time.

    Attributes:
        row_count: Total number of rows.
        column_count: Total number of columns.
        missing_value_pct: Percentage (0-100) of all cells that are missing.
        duplicate_row_count: Number of fully duplicated rows.
        outlier_count: Total number of detected outlier values across all
            numeric columns (see `infrastructure/data_processing/issue_detector.py`
            for the detection method, IQR-based -- 🟩 ORIGINAL detection logic,
            operating on a 🟦 PAPER-motivated notion of "data quality issue").
        dtype_issue_columns: Mapping of column name -> human-readable
            description of a detected data-type inconsistency (e.g. a numeric
            column stored with mixed string/number values).
        column_names: All column names, in original order.
        numeric_columns: Subset of `column_names` detected as numeric.
        categorical_columns: Subset of `column_names` detected as categorical
            (object/string or low-cardinality numeric treated as categorical).
    """

    row_count: int
    column_count: int
    missing_value_pct: float
    duplicate_row_count: int
    outlier_count: int
    dtype_issue_columns: dict[str, str] = field(default_factory=dict)
    column_names: tuple[str, ...] = field(default_factory=tuple)
    numeric_columns: tuple[str, ...] = field(default_factory=tuple)
    categorical_columns: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.row_count < 0:
            raise ValueError("row_count cannot be negative")
        if self.column_count < 0:
            raise ValueError("column_count cannot be negative")
        if not (0.0 <= self.missing_value_pct <= 100.0):
            raise ValueError("missing_value_pct must be between 0 and 100")
        if self.duplicate_row_count < 0:
            raise ValueError("duplicate_row_count cannot be negative")
        if self.outlier_count < 0:
            raise ValueError("outlier_count cannot be negative")

    @property
    def has_quality_issues(self) -> bool:
        """True if any missing values, duplicates, outliers, or dtype issues exist."""
        return (
            self.missing_value_pct > 0
            or self.duplicate_row_count > 0
            or self.outlier_count > 0
            or bool(self.dtype_issue_columns)
        )


@dataclass(frozen=True)
class Dataset:
    """A reference to an uploaded dataset and, once computed, its profile.

    `path` and `file_format` are the only fields required at upload time;
    `profile` is attached after the Analysis Agent (Phase 5) runs profiling.
    """

    path: str
    file_format: str
    profile: DatasetProfile | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("Dataset.path must not be empty")
        allowed_formats = {"csv", "xlsx", "parquet"}
        if self.file_format.lower() not in allowed_formats:
            raise ValueError(
                f"Unsupported file_format {self.file_format!r}; expected one of {allowed_formats} "
                "(Phase 1, Section 8: In Scope)"
            )
