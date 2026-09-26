"""cost_metrics.py: real computational-cost scoring.

🟦 PAPER-motivated (analogous to C_u(D_j), generalized per Phase 1 Section 7
from literal USD API cost to a computational/latency proxy), 🟩 ORIGINAL
implementation.

Design decision: cost is estimated from each step's Big-O complexity class
and the dataset's row count, NOT measured wall-clock time. Wall-clock
timing was considered and rejected -- see the module-level rationale below
-- in favor of a deterministic, reproducible, machine-independent estimate,
consistent with the paper's OWN complexity-analysis methodology (its
Section on algorithmic complexity: O(N log N) partitioning, O(NK) EM,
O(MK log MK) greedy, O(MBK) DP -- the paper reasons about cost through
complexity classes, not by benchmarking wall-clock runs).

Alternatives considered:
- Measured wall-clock time (via time.perf_counter() around StrategyExecutor.apply):
  REJECTED. Real, but non-reproducible across machines/load, which would make
  two runs of the same strategy on the same data produce different scores --
  unacceptable for a system whose entire value proposition is auditable,
  reproducible decision support (Phase 1, NFR-9).
- A fixed per-operation-type USD cost table (mirroring the paper's Table 1
  literally): REJECTED as the primary mechanism -- this project doesn't
  route to priced external methods (rule-based/code-gen/PLM/LLM); its
  candidate strategies are freely composed sequences of Pandas operations
  with no natural per-call price. Big-O-based estimation generalizes to any
  composed strategy without needing a price table maintained by hand.
"""

from __future__ import annotations

from autoclean.domain.entities.cleaning_strategy import CleaningOperation, CleaningStrategy

# Per-operation complexity multiplier, expressed as "row-operations per row".
# O(n) operations (imputation, clipping, type coercion) get 1.0; O(n log n)
# operations (deduplication needs a hash/sort pass, outlier removal/clipping
# needs a quantile computation) get a log-scaled multiplier applied by the
# caller based on actual row count, not hard-coded here.
_LINEAR_OPERATIONS = frozenset(
    {
        CleaningOperation.TYPE_COERCION,
        CleaningOperation.MEAN_IMPUTATION,
        CleaningOperation.MEDIAN_IMPUTATION,
        CleaningOperation.MODE_IMPUTATION,
        CleaningOperation.CONSTANT_IMPUTATION,
        CleaningOperation.DROP_ROWS_WITH_MISSING,
        CleaningOperation.NO_OP,
    }
)
_LINEARITHMIC_OPERATIONS = frozenset(
    {
        CleaningOperation.EXACT_DEDUPLICATION,
        CleaningOperation.IQR_OUTLIER_CLIPPING,
        CleaningOperation.IQR_OUTLIER_REMOVAL,
    }
)

# Scale constant converting raw row-operation counts into a comparable score
# range; chosen so a single-step strategy on a ~1,000-row dataset (a
# realistic scale for this project's interactive, single-analyst use case,
# Phase 1 Section 8) lands near the middle of the [0, 1] cost-score range,
# not pinned to either extreme.
_ROW_OPERATIONS_SCALE = 5_000.0


def _estimate_row_operations(strategy: CleaningStrategy, row_count: int) -> float:
    import math

    total = 0.0
    for step in strategy.steps:
        if step.operation in _LINEAR_OPERATIONS:
            total += row_count
        elif step.operation in _LINEARITHMIC_OPERATIONS:
            total += row_count * max(1.0, math.log2(max(2, row_count)))
        else:
            # Unknown future operation: assume the more expensive class
            # rather than silently under-counting cost.
            total += row_count * max(1.0, math.log2(max(2, row_count)))
    return total


def compute_cost_score(strategy: CleaningStrategy, row_count: int) -> float:
    """Score in [0.0, 1.0], higher is cheaper. Deterministic given the
    strategy's step list and row count -- same inputs always produce the
    same score, on any machine.
    """
    if row_count <= 0 or not strategy.steps:
        return 1.0
    row_operations = _estimate_row_operations(strategy, row_count)
    score = 1.0 / (1.0 + row_operations / _ROW_OPERATIONS_SCALE)
    return float(max(0.0, min(1.0, score)))
