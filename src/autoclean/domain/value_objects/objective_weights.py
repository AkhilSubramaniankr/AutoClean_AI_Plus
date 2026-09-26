"""ObjectiveWeights value object: the weights used in the weighted decision matrix.

A value object (not an entity) because two ObjectiveWeights with the same
field values are interchangeable -- there is no identity to track, only value.
Loaded from `config/objective_weights.yaml` (Phase 3) via `from_mapping`;
this module contains no YAML/file I/O itself (that belongs in Infrastructure)
and no framework dependency, per the Domain layer's zero-dependency rule.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ObjectiveWeights:
    """Weights for the six evaluation objectives (Phase 1, FR-4 / FR-5).

    Must sum to 1.0 (within floating-point tolerance) so that
    `EvaluationScore.compute_weighted_total` always returns a value in
    [0.0, 1.0], keeping ranked strategies comparable across experiments run
    with different weight configurations.
    """

    data_quality: float
    computational_cost: float
    information_preservation: float
    statistical_validity: float
    fairness_impact: float
    downstream_ml: float

    _SUM_TOLERANCE = 1e-6

    def __post_init__(self) -> None:
        for name, value in self._as_dict().items():
            if value < 0.0:
                raise ValueError(f"Weight {name!r} must be non-negative, got {value}")
        total = sum(self._as_dict().values())
        if not math.isclose(total, 1.0, abs_tol=self._SUM_TOLERANCE):
            raise ValueError(
                f"ObjectiveWeights must sum to 1.0 (within {self._SUM_TOLERANCE}), got {total}"
            )

    def _as_dict(self) -> dict[str, float]:
        return {
            "data_quality": self.data_quality,
            "computational_cost": self.computational_cost,
            "information_preservation": self.information_preservation,
            "statistical_validity": self.statistical_validity,
            "fairness_impact": self.fairness_impact,
            "downstream_ml": self.downstream_ml,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ObjectiveWeights:
        """Construct from a plain dict, e.g. the parsed `weights:` block of
        `config/objective_weights.yaml`. Raises KeyError if any of the six
        required keys are missing -- deliberately strict, per NFR-1's
        philosophy that the six-objective contract should fail loudly, not
        silently default a forgotten weight to zero.
        """
        required_keys = (
            "data_quality",
            "computational_cost",
            "information_preservation",
            "statistical_validity",
            "fairness_impact",
            "downstream_ml",
        )
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise KeyError(f"ObjectiveWeights mapping is missing required keys: {missing}")
        return cls(**{key: float(data[key]) for key in required_keys})

    @classmethod
    def uniform(cls) -> ObjectiveWeights:
        """Equal weighting across all six objectives (1/6 each). Useful as a
        neutral default in tests and as a documented fallback if
        `config/objective_weights.yaml` fails to load.
        """
        equal_share = 1.0 / 6.0
        return cls(
            data_quality=equal_share,
            computational_cost=equal_share,
            information_preservation=equal_share,
            statistical_validity=equal_share,
            fairness_impact=equal_share,
            downstream_ml=equal_share,
        )
