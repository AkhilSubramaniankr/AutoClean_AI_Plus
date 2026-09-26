"""fairness_metrics.py: real fairness-impact scoring.

🟩 ORIGINAL -- not addressed anywhere in the paper (Phase 1, Section 10).

Measures whether a cleaning strategy affects rows unevenly across subgroups
of a "sensitive" categorical column, using a disparate-impact-style
dispersion measure: the gap between the best- and worst-treated subgroup's
row-retention rate. A strategy that drops 40% of one subgroup's rows and 2%
of another's has a real, measurable fairness problem; a strategy that drops
rows (or leaves them untouched) evenly across subgroups does not.

IMPORTANT LIMITATION, stated plainly: choosing WHICH column is "sensitive"
is not something this project's user-facing UI can do yet (Streamlit is
Phase 9). Pending that, the sensitive column is auto-selected via a
documented heuristic (the categorical column with the lowest cardinality
>= 2), or may be supplied explicitly by a caller who already knows which
column matters for their dataset. This is a real, working fairness check on
a SINGLE proxy column, not a comprehensive fairness audit across every
possible protected attribute -- exactly the scope Phase 1's Assumption #5
already committed to ("fairness impact is evaluated with respect to
user-specified sensitive/protected columns... does not infer protected
attributes that are not present").
"""

from __future__ import annotations

import pandas as pd


def select_default_sensitive_column(
    df: pd.DataFrame, categorical_columns: tuple[str, ...]
) -> str | None:
    """Heuristic fallback: the categorical column with the smallest number
    of distinct values (at least 2, since a single-valued column can't show
    disparate impact by definition). Returns None if no such column exists.
    """
    candidates = [
        (column, df[column].nunique(dropna=True))
        for column in categorical_columns
        if column in df.columns and df[column].nunique(dropna=True) >= 2
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda pair: pair[1])[0]


def compute_fairness_score(
    original_df: pd.DataFrame, cleaned_df: pd.DataFrame, sensitive_column: str | None
) -> float:
    """Score in [0.0, 1.0]: 1.0 means every subgroup retained rows at
    exactly the same rate; lower means some subgroup lost disproportionately
    more rows than another. Returns a neutral 0.5 (not 1.0 -- an untestable
    strategy shouldn't look "perfectly fair" by default) if no sensitive
    column is available or the column has no rows in the original data.
    """
    if sensitive_column is None or sensitive_column not in original_df.columns:
        return 0.5

    group_sizes_before = original_df.groupby(sensitive_column, dropna=False).size()
    if group_sizes_before.empty or (group_sizes_before == 0).all():
        return 0.5

    if sensitive_column in cleaned_df.columns:
        group_sizes_after = cleaned_df.groupby(sensitive_column, dropna=False).size()
    else:
        # The sensitive column itself was altered/removed by the strategy
        # (e.g. a dtype-coercion or drop targeting it) -- fall back to
        # counting surviving rows by original index membership per group.
        surviving_index = cleaned_df.index
        group_sizes_after = original_df.loc[original_df.index.isin(surviving_index)].groupby(
            sensitive_column, dropna=False
        ).size()

    retention_rates = []
    for group, before_count in group_sizes_before.items():
        if before_count == 0:
            continue
        after_count = group_sizes_after.get(group, 0)
        retention_rates.append(float(after_count) / float(before_count))

    if len(retention_rates) < 2:
        return 0.5

    disparity = max(retention_rates) - min(retention_rates)
    return float(max(0.0, min(1.0, 1.0 - disparity)))
