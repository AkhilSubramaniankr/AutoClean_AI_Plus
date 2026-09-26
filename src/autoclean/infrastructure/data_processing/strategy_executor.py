"""StrategyExecutor: deterministically applies a CleaningStrategy's steps to
a DataFrame, producing the cleaned result.

DESIGN ADDENDUM (Phase 6, same transparency convention as the Phase 4
`infrastructure/data_processing/` addendum and the Phase 5 placeholder
flags): this class did not exist before Phase 6. It's added here because
computing HONEST values for information_preservation, statistical_validity,
downstream_ml, and the EM confidence estimator (Eqs. 2-6) is impossible
without actually applying each candidate strategy and comparing real
before/after data -- there is no way to fake these four objectives from
profile summary statistics alone (Phase 5's placeholder approach) without
either leaving them at a neutral constant (as Phase 5 did, explicitly) or
fabricating numbers (forbidden by NFR-1 and the project's anti-fabrication
rule).

Phase 8 ("Cleaning Execution & Validation") will build `ExecuteCleaningUseCase`
on top of THIS SAME executor, adding audit persistence, output file writing,
and reproducible script export -- Phase 6 only needs the transformation
itself, in-memory, to score candidates; Phase 8 needs the full
execute-and-persist workflow for the one strategy a human actually approved.
Reusing one executor for both keeps "what a strategy's steps actually do"
defined in exactly one place.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)

logger = logging.getLogger(__name__)

_DEFAULT_IQR_MULTIPLIER = 1.5


class StrategyExecutor:
    """Applies a CleaningStrategy's steps to a DataFrame, in order, returning
    a new DataFrame. Never mutates the input.
    """

    def apply(self, df: pd.DataFrame, strategy: CleaningStrategy) -> pd.DataFrame:
        result = df.copy(deep=True)
        for step in strategy.steps:
            result = self._apply_step(result, step)
        logger.info(
            "StrategyExecutor applied strategy",
            extra={
                "strategy_id": strategy.strategy_id,
                "rows_before": len(df),
                "rows_after": len(result),
            },
        )
        return result

    def _apply_step(self, df: pd.DataFrame, step: CleaningStep) -> pd.DataFrame:
        operation = step.operation
        column = step.target_column

        if operation == CleaningOperation.NO_OP:
            return df

        if operation == CleaningOperation.TYPE_COERCION:
            df = df.copy()
            df[column] = pd.to_numeric(df[column], errors="coerce")
            return df

        if operation == CleaningOperation.EXACT_DEDUPLICATION:
            # Deliberately NOT resetting the index: downstream metrics
            # (information_preservation.py) align original vs. cleaned rows
            # by index to know exactly which original rows survived. Row
            # order among survivors is otherwise unaffected.
            return df.drop_duplicates(keep="first")

        if operation == CleaningOperation.DROP_ROWS_WITH_MISSING:
            return df.dropna(subset=[column])

        if operation == CleaningOperation.MEAN_IMPUTATION:
            df = df.copy()
            if pd.api.types.is_numeric_dtype(df[column]):
                mean_val = df[column].mean()
                df[column] = df[column].fillna(mean_val)
            else:
                # Fallback to mode imputation for non-numeric columns
                mode_values = df[column].mode(dropna=True)
                fill_val = mode_values.iloc[0] if not mode_values.empty else "Missing"
                df[column] = df[column].fillna(fill_val)
            return df

        if operation == CleaningOperation.MEDIAN_IMPUTATION:
            df = df.copy()
            if pd.api.types.is_numeric_dtype(df[column]):
                median_val = df[column].median()
                df[column] = df[column].fillna(median_val)
            else:
                # Fallback to mode imputation for non-numeric columns
                mode_values = df[column].mode(dropna=True)
                fill_val = mode_values.iloc[0] if not mode_values.empty else "Missing"
                df[column] = df[column].fillna(fill_val)
            return df

        if operation == CleaningOperation.MODE_IMPUTATION:
            df = df.copy()
            mode_values = df[column].mode(dropna=True)
            fill_value = mode_values.iloc[0] if not mode_values.empty else df[column]
            df[column] = df[column].fillna(fill_value)
            return df

        if operation == CleaningOperation.CONSTANT_IMPUTATION:
            df = df.copy()
            fill_value = step.parameters.get("fill_value", 0)
            df[column] = df[column].fillna(fill_value)
            return df

        if operation == CleaningOperation.IQR_OUTLIER_CLIPPING:
            df = df.copy()
            if not pd.api.types.is_numeric_dtype(df[column]):
                return df
            lower, upper = self._iqr_bounds(df[column], step.parameters)
            if lower is not None and upper is not None:
                df[column] = df[column].clip(lower=lower, upper=upper)
            return df

        if operation == CleaningOperation.IQR_OUTLIER_REMOVAL:
            if not pd.api.types.is_numeric_dtype(df[column]):
                return df
            lower, upper = self._iqr_bounds(df[column], step.parameters)
            if lower is None or upper is None:
                return df
            mask = df[column].between(lower, upper) | df[column].isna()
            return df[mask]

        raise ValueError(f"StrategyExecutor: unhandled operation {operation!r}")

    @staticmethod
    def _iqr_bounds(series: pd.Series[Any], parameters: dict[str, Any]) -> tuple[float | None, float | None]:
        if not pd.api.types.is_numeric_dtype(series):
            return None, None
            
        non_null = series.dropna()
        if non_null.empty:
            return None, None
        q1, q3 = non_null.quantile(0.25), non_null.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return None, None
        multiplier = parameters.get("iqr_multiplier", _DEFAULT_IQR_MULTIPLIER)
        return q1 - multiplier * iqr, q3 + multiplier * iqr