"""Port interface for strategy scoring, implemented by the Infrastructure layer.

Design decision (Phase 2, Section 12, Dependency Inversion): the Evaluation
Agent's use case depends on this ABC, never on a concrete metrics
implementation. This is what keeps the "LLM never computes" architectural
rule enforceable -- an `IMetricsEngine` implementation has no LLM-shaped
parameter anywhere in its signature, by construction.

PHASE 6 REVISION to this port, made explicit here per this project's
transparency convention for architectural deviations (same as the Phase 4
`infrastructure/data_processing/` addendum and the Phase 5 placeholder
flags): the original Phase 5 signature was `score(strategy, profile) ->
EvaluationScore`, scoring one strategy at a time from summary statistics
alone. Phase 6 changes this to `score_all(strategies, df, profile) ->
dict[str, EvaluationScore]` for two structural reasons that only became
apparent once real (non-placeholder) computation was attempted:
  1. The EM confidence estimator (Eqs. 2-6) is fundamentally a BATCH
     algorithm -- it estimates confidence from AGREEMENT ACROSS STRATEGIES
     on the same rows, which is meaningless for a single strategy scored in
     isolation.
  2. Four of the six objectives (information preservation, statistical
     validity, fairness, downstream ML) require the actual cleaned DATA,
     not just a DatasetProfile summary -- Phase 5's per-strategy signature
     never passed the raw DataFrame through at all.
`PlaceholderMetricsEngine` (Phase 5) was updated to implement the new
signature via a trivial per-strategy loop, so it remains available as a
fast test double; it did not need the DataFrame before and still ignores it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.evaluation_score import EvaluationScore


class IMetricsEngine(ABC):
    """Scores a batch of candidate CleaningStrategy objects together."""

    @abstractmethod
    def score_all(
        self, strategies: list[CleaningStrategy], df: pd.DataFrame, original_profile: DatasetProfile
    ) -> dict[str, EvaluationScore]:
        """Compute an EvaluationScore for every strategy in `strategies`,
        keyed by `strategy.strategy_id`.

        Implementations MUST be fully deterministic (NFR-1: the LLM never
        performs deterministic calculations) -- no implementation of this
        method may call an LLM or any other non-deterministic service.
        `df` MUST NOT be mutated (implementations should copy before
        transforming, as `StrategyExecutor` already does).
        """
        raise NotImplementedError
