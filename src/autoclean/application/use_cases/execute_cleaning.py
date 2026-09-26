"""ExecuteCleaningUseCase: applies the human-approved strategy for real and
saves the result (Phase 1, FR-10).

Implements FR-10. Depends on `IDatasetRepository` (a port, for saving) and
`StrategyExecutor` (the same concrete Phase 6 class `RealMetricsEngine`
already uses to score candidates -- see its module docstring: "Phase 8's
ExecuteCleaningUseCase will build on THIS SAME executor"). Reusing one
executor for both scoring (Phase 6) and real execution (Phase 8) keeps
"what a strategy's steps actually do" defined in exactly one place, exactly
as planned when StrategyExecutor was first written.
"""

from __future__ import annotations

import logging

import pandas as pd

from autoclean.application.ports.dataset_repository import IDatasetRepository
from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.infrastructure.data_processing.strategy_executor import StrategyExecutor

logger = logging.getLogger(__name__)


class ExecuteCleaningUseCase:
    """Executes an approved CleaningStrategy against real data and persists
    the cleaned result to disk.
    """

    def __init__(
        self,
        dataset_repository: IDatasetRepository,
        strategy_executor: StrategyExecutor | None = None,
    ) -> None:
        self._dataset_repository = dataset_repository
        self._strategy_executor = strategy_executor or StrategyExecutor()

    def execute(
        self, df: pd.DataFrame, strategy: CleaningStrategy, output_path: str
    ) -> tuple[pd.DataFrame, str]:
        """Returns (cleaned_dataframe, path_actually_written)."""
        cleaned_df = self._strategy_executor.apply(df, strategy)
        saved_path = self._dataset_repository.save(cleaned_df, output_path)
        logger.info(
            "ExecuteCleaningUseCase complete",
            extra={
                "strategy_id": strategy.strategy_id,
                "rows_before": len(df),
                "rows_after": len(cleaned_df),
                "output_path": saved_path,
            },
        )
        return cleaned_df, saved_path
