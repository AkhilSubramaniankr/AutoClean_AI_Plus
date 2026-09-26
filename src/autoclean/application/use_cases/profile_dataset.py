"""ProfileDatasetUseCase: Application-layer orchestration around DatasetProfiler.

Implements FR-1/FR-2. Depends on the Phase 4 deterministic
`DatasetProfiler` directly (not behind a port) -- the profiler has no
external I/O or side effects of its own to abstract away (Phase 2, Section
12 reserves the Repository/Adapter patterns for actual I/O boundaries:
databases, LLMs, file systems), so introducing a port here would add
indirection without a corresponding testability or swappability benefit.
"""

from __future__ import annotations

import logging

import pandas as pd

from autoclean.domain.entities.data_issue import DataIssue
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler

logger = logging.getLogger(__name__)


class ProfileDatasetUseCase:
    """Profiles a DataFrame and detects its data-quality issues."""

    def __init__(
        self,
        profiler: DatasetProfiler | None = None,
        issue_detector: IssueDetector | None = None,
    ) -> None:
        self._profiler = profiler or DatasetProfiler()
        self._issue_detector = issue_detector or IssueDetector()

    def execute(self, df: pd.DataFrame) -> tuple[DatasetProfile, list[DataIssue]]:
        profile = self._profiler.profile(df)
        issues = self._issue_detector.detect(df, profile)
        logger.info(
            "ProfileDatasetUseCase complete",
            extra={"row_count": profile.row_count, "issue_count": len(issues)},
        )
        return profile, issues
