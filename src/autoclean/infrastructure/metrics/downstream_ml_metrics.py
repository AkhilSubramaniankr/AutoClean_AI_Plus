"""downstream_ml_metrics.py: real downstream-ML-impact scoring.

🟩 ORIGINAL -- not addressed anywhere in the paper (Phase 1, Section 10).

Trains a small, fixed, deterministic benchmark model (a shallow DecisionTree
classifier or regressor -- fast, deterministic given a fixed random_state,
and interpretable enough to defend in an academic review, unlike an
ensemble) on the CLEANED data and reports its held-out accuracy or normalized R^2 score.
This is a real, measured model score, not a fabricated number -- see Phase 1's
explicit rule against fabricating evaluation metrics or benchmark values.

IMPORTANT LIMITATIONS, stated plainly (mirroring fairness_metrics.py's own
honesty about its single-column limitation):
1. Choosing the target column requires either (a) the caller supplying one
   explicitly, or (b) a documented heuristic fallback (the column with the
   smallest cardinality >= 2, excluding the sensitive column if set) -- pending
   Phase 9's UI for explicit user selection. A wrongly-guessed target column
   produces a real but not-necessarily-meaningful number; this is disclosed via
   logging, not hidden.
2. If there isn't enough surviving data to train/test after a strategy's
   row removal (e.g. too few rows, or fewer than 2 distinct target values), this
   module returns a neutral 0.5 rather than crashing or fabricating a score
   -- an untestable strategy is scored as "unknown," not "good" or "bad."
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.utils.multiclass import type_of_target

logger = logging.getLogger(__name__)

_RANDOM_STATE = 42
_TEST_SIZE = 0.3
_MAX_TREE_DEPTH = 5
_MIN_ROWS_TO_TRAIN = 10
_MIN_CLASSES = 2


def select_default_target_column(
    df: pd.DataFrame,
    categorical_columns: tuple[str, ...] | list[str] = (),
    exclude: str | None = None,
) -> str | None:
    """Selects a default target column. Prioritizes candidate categorical columns first.
    If none are available, falls back to the lowest-cardinality numeric column with >= 2 distinct values.
    """
    # 1. Search across categorical/discrete columns candidate list
    candidates = [
        (column, df[column].nunique(dropna=True))
        for column in categorical_columns
        if column in df.columns and column != exclude and df[column].nunique(dropna=True) >= _MIN_CLASSES
    ]
    if candidates:
        return min(candidates, key=lambda pair: pair[1])[0]

    # 2. Fallback: Search across all valid columns with distinct values >= 2
    fallback_candidates = [
        (col, df[col].nunique(dropna=True))
        for col in df.columns
        if col != exclude and df[col].nunique(dropna=True) >= _MIN_CLASSES
    ]
    if fallback_candidates:
        return min(fallback_candidates, key=lambda pair: pair[1])[0]

    return None


def compute_downstream_ml_score(
    cleaned_df: pd.DataFrame, target_column: str | None, numeric_feature_columns: tuple[str, ...]
) -> float:
    if target_column is None or target_column not in cleaned_df.columns:
        return 0.5

    feature_columns = [
        col for col in numeric_feature_columns if col in cleaned_df.columns and col != target_column
    ]
    if not feature_columns:
        return 0.5

    usable = cleaned_df[[*feature_columns, target_column]].dropna()
    if len(usable) < _MIN_ROWS_TO_TRAIN or usable[target_column].nunique() < _MIN_CLASSES:
        logger.warning(
            "downstream_ml_metrics: insufficient data to train/evaluate; returning neutral score",
            extra={"usable_rows": len(usable), "target_column": target_column},
        )
        return 0.5

    features = usable[feature_columns]
    target = usable[target_column]

    target_kind = type_of_target(target)
    is_continuous = target_kind in ("continuous", "continuous-multioutput")

    try:
        if is_continuous:
            # Simple random split for continuous target regression
            x_train, x_test, y_train, y_test = train_test_split(
                features, target, test_size=_TEST_SIZE, random_state=_RANDOM_STATE
            )
        else:
            # Stratified split for categorical/discrete targets
            x_train, x_test, y_train, y_test = train_test_split(
                features, target, test_size=_TEST_SIZE, random_state=_RANDOM_STATE, stratify=target
            )
    except ValueError:
        logger.warning("downstream_ml_metrics: train/test split failed; returning neutral score")
        return 0.5

    if is_continuous:
        regressor = DecisionTreeRegressor(max_depth=_MAX_TREE_DEPTH, random_state=_RANDOM_STATE)
        regressor.fit(x_train, y_train)
        r2_score = float(regressor.score(x_test, y_test))
        # Map R^2 from [-inf, 1.0] range into a normalized bounded range [0.0, 1.0]
        score = max(0.0, min(1.0, (r2_score + 1.0) / 2.0 if r2_score < 0 else r2_score))
    else:
        classifier = DecisionTreeClassifier(max_depth=_MAX_TREE_DEPTH, random_state=_RANDOM_STATE)
        classifier.fit(x_train, y_train)
        score = float(classifier.score(x_test, y_test))

    logger.info(
        "downstream_ml_metrics: benchmark model evaluated",
        extra={
            "target_column": target_column,
            "is_continuous": is_continuous,
            "score": score,
            "test_rows": len(x_test),
        },
    )
    return max(0.0, min(1.0, score))