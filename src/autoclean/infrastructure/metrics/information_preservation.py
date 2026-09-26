"""information_preservation.py: real information-preservation scoring.

🟩 ORIGINAL -- not present in the paper at all (Phase 1, Section 10).

Combines two real, measured signals from actual before/after data:
1. Row retention: what fraction of original rows survived.
2. Value preservation: of the rows that survived, what fraction of numeric
   cell values are unchanged from their original value (a cell changed by
   imputation or clipping counts as "altered"; a cell that was already
   missing and stays missing is NOT counted as newly altered).
"""

from __future__ import annotations

import pandas as pd

_VALUE_CHANGE_PENALTY_WEIGHT = 0.4


def compute_information_preservation_score(original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> float:
    if len(original_df) == 0:
        return 1.0

    row_retention = len(cleaned_df) / len(original_df)

    altered_ratio = _compute_altered_cell_ratio(original_df, cleaned_df)

    score = row_retention - _VALUE_CHANGE_PENALTY_WEIGHT * altered_ratio
    return float(max(0.0, min(1.0, score)))


def _compute_altered_cell_ratio(original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> float:
    """Fraction of numeric cells, among rows that survived, whose value
    differs from the original. A row that was dropped contributes nothing
    here -- its information loss is already captured by row_retention.
    """
    numeric_columns = original_df.select_dtypes(include="number").columns
    if len(numeric_columns) == 0 or len(cleaned_df) == 0:
        return 0.0

    # Only rows that survived can be compared cell-by-cell; StrategyExecutor
    # preserves original row order for surviving rows (no reordering
    # operations exist in the current operation set), so a positional
    # comparison over the first len(cleaned_df) original rows is valid EXCEPT
    # when row-removal operations changed which specific rows survived. To
    # stay correct even then, compare using the original DataFrame's index
    # values that are still present in cleaned_df.
    common_index = original_df.index.intersection(cleaned_df.index)
    if len(common_index) == 0:
        return 0.0

    numeric_column_list = list(numeric_columns)
    original_aligned = original_df.loc[common_index, numeric_column_list]
    cleaned_aligned = cleaned_df.loc[common_index, numeric_column_list]

    both_missing = original_aligned.isna() & cleaned_aligned.isna()
    unchanged = (original_aligned == cleaned_aligned) | both_missing

    total_cells = unchanged.size
    if total_cells == 0:
        return 0.0
    altered_cells = total_cells - int(unchanged.to_numpy().sum())
    return altered_cells / total_cells
