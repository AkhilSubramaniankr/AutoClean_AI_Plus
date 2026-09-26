"""statistical_validity.py: real statistical-distribution-preservation scoring.

🟩 ORIGINAL. Uses the two-sample Kolmogorov-Smirnov test (scipy.stats.ks_2samp),
a standard, well-established non-parametric test for whether two samples
come from the same distribution -- exactly the question "did cleaning distort
this column's statistical properties?" is asking. The KS statistic itself
(not the p-value) is used as the distance measure: it is bounded in [0, 1]
by construction (the maximum vertical distance between two empirical CDFs),
which maps directly onto a [0, 1] score without further calibration.

Alternative considered: comparing mean/variance only (a simpler, cheaper
check). Rejected as the primary measure -- two distributions can share a
mean and variance while differing considerably in shape (e.g. after
aggressive outlier removal skews a previously symmetric distribution); KS
compares the full empirical distribution, which mean/variance alone cannot
detect.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats

_MIN_SAMPLES_FOR_TEST = 2


def compute_statistical_validity_score(
    original_df: pd.DataFrame, cleaned_df: pd.DataFrame, numeric_columns: tuple[str, ...]
) -> float:
    """Average, across numeric columns, of (1 - KS statistic) comparing the
    column's distribution before vs. after. Columns with too few non-null
    values to run the test (fewer than 2 on either side) are skipped rather
    than penalized -- a column that was entirely missing/constant isn't a
    statistical-validity failure, it's simply not testable.
    """
    per_column_scores = []
    for column in numeric_columns:
        if column not in original_df.columns or column not in cleaned_df.columns:
            continue
        before_values = original_df[column].dropna()
        after_values = cleaned_df[column].dropna()
        if len(before_values) < _MIN_SAMPLES_FOR_TEST or len(after_values) < _MIN_SAMPLES_FOR_TEST:
            continue
        ks_statistic = stats.ks_2samp(before_values, after_values).statistic
        per_column_scores.append(1.0 - float(ks_statistic))

    if not per_column_scores:
        # No numeric columns were testable at all (e.g. a purely categorical
        # dataset) -- neutral score, neither rewarding nor penalizing.
        return 0.5

    return float(max(0.0, min(1.0, sum(per_column_scores) / len(per_column_scores))))
