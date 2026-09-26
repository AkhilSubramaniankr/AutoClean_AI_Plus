"""GenerateStrategiesUseCase: Application-layer orchestration around StrategyGenerator.

Implements FR-3. Same "no port needed" reasoning as ProfileDatasetUseCase --
StrategyGenerator has no external I/O to abstract.
"""

from __future__ import annotations

import logging

from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.data_issue import DataIssue
from autoclean.infrastructure.data_processing.strategy_generator import StrategyGenerator

logger = logging.getLogger(__name__)


class GenerateStrategiesUseCase:
    """Generates candidate CleaningStrategy objects from detected issues."""

    def __init__(self, strategy_generator: StrategyGenerator | None = None) -> None:
        self._strategy_generator = strategy_generator or StrategyGenerator()

    def execute(self, issues: list[DataIssue]) -> list[CleaningStrategy]:
        strategies = self._strategy_generator.generate(issues)
        logger.info("GenerateStrategiesUseCase complete", extra={"strategy_count": len(strategies)})
        return strategies
