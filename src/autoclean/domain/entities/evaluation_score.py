"""Domain entity representing a strategy's score across the six evaluation objectives.

Design decision (Phase 2, Section 6): the six objectives are named fields, not
a generic `Dict[str, float]`, so the six-objective contract (Phase 1, FR-4) is
enforced by the type system -- a missing objective is a type error at
construction time, not a silently missing dict key discovered at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from autoclean.domain.value_objects.objective_weights import ObjectiveWeights


@dataclass(frozen=True)
class EvaluationScore:
    """A CleaningStrategy's score across all six objectives (Phase 1, FR-4).

    All six scores are normalized to [0.0, 1.0], where 1.0 is best, so they
    remain comparable and combinable regardless of each metric's native scale
    (e.g. cost is naturally "lower is better"; this entity stores it already
    inverted so that higher is always better across every field here --
    inversion happens in `infrastructure/metrics/cost_metrics.py`, Phase 6).

    Attributes:
        data_quality_score: 🟦 PAPER-motivated (directly analogous to Q_u(D_j)).
        computational_cost_score: 🟦 PAPER-motivated (directly analogous to
            C_u(D_j), generalized from USD cost to a computational/latency
            proxy per Phase 1, Section 7).
        information_preservation_score: 🟩 ORIGINAL.
        statistical_validity_score: 🟩 ORIGINAL.
        fairness_impact_score: 🟩 ORIGINAL.
        downstream_ml_score: 🟩 ORIGINAL.
        em_confidence: 🟦 PAPER (Eqs. 2-6), confidence estimate from the
            EM-based quality estimator, in [0.0, 1.0]. Defaults to 0.0 when
            EM estimation was not applicable/run for this strategy (Phase 1,
            Risk table: EM fallback path).
    """

    data_quality_score: float
    computational_cost_score: float
    information_preservation_score: float
    statistical_validity_score: float
    fairness_impact_score: float
    downstream_ml_score: float
    em_confidence: float = 0.0

    _OBJECTIVE_FIELDS: ClassVar[tuple[str, ...]] = (
        "data_quality_score",
        "computational_cost_score",
        "information_preservation_score",
        "statistical_validity_score",
        "fairness_impact_score",
        "downstream_ml_score",
    )

    def __post_init__(self) -> None:
        for field_name in self._OBJECTIVE_FIELDS:
            value = getattr(self, field_name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{field_name} must be within [0.0, 1.0], got {value}")
        if not (0.0 <= self.em_confidence <= 1.0):
            raise ValueError(f"em_confidence must be within [0.0, 1.0], got {self.em_confidence}")

    def compute_weighted_total(self, weights: ObjectiveWeights) -> float:
        """Combine the six objective scores into one weighted-sum ranking score.

        This is the deterministic weighted decision matrix from Phase 2,
        Section 12 (conceptually descended from the paper's weighted-gain
        metric Delta_wg, Eq. 7, generalized from a 2-term ratio to a 6-term
        weighted sum -- see Phase 2, Section 14).
        """
        return (
            self.data_quality_score * weights.data_quality
            + self.computational_cost_score * weights.computational_cost
            + self.information_preservation_score * weights.information_preservation
            + self.statistical_validity_score * weights.statistical_validity
            + self.fairness_impact_score * weights.fairness_impact
            + self.downstream_ml_score * weights.downstream_ml
        )

    def as_dict(self) -> dict[str, float]:
        """Return all six objective scores plus em_confidence as a plain dict.

        Used when persisting to the `strategy_scores` SQLite table (Phase 2,
        Section 7) and when building the LLM explanation prompt context
        (Phase 7) -- in both cases the LLM/DB only ever *receives* this
        already-computed dict; it never computes it.
        """
        return {
            "data_quality_score": self.data_quality_score,
            "computational_cost_score": self.computational_cost_score,
            "information_preservation_score": self.information_preservation_score,
            "statistical_validity_score": self.statistical_validity_score,
            "fairness_impact_score": self.fairness_impact_score,
            "downstream_ml_score": self.downstream_ml_score,
            "em_confidence": self.em_confidence,
        }
