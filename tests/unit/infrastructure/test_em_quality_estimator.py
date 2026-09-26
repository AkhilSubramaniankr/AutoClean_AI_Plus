"""Unit tests for em_quality_estimator.py -- the paper-derived EM algorithm
(Eqs. 2-6), adapted to per-strategy confidence estimation (Phase 6).

These tests are deliberately constructed around KNOWN AGREEMENT PATTERNS
(not random data) so the expected outcome is derivable by hand, not just
"whatever the code happens to produce" -- the single most important
property to verify for an algorithm this academically load-bearing.
"""

from __future__ import annotations

import numpy as np
import pytest

from autoclean.infrastructure.metrics.em_quality_estimator import EMQualityEstimator

pytestmark = pytest.mark.unit


class TestEMQualityEstimator:
    def test_fewer_than_two_strategies_returns_neutral_confidence(self) -> None:
        estimator = EMQualityEstimator()
        result = estimator.estimate({"s1": np.array([1, 0, 1, 1])})
        assert result == {"s1": 0.5}

    def test_empty_input_returns_empty_result(self) -> None:
        estimator = EMQualityEstimator()
        assert estimator.estimate({}) == {}

    def test_two_identical_strategies_get_high_mutual_confidence(self) -> None:
        """If two strategies agree on EVERY row, EM should conclude both are
        highly reliable (their agreement is exactly what confidence measures).
        """
        labels = np.array([1, 0, 1, 1, 0, 1, 0, 0, 1, 1])
        estimator = EMQualityEstimator()
        result = estimator.estimate({"s1": labels.copy(), "s2": labels.copy()})
        assert result["s1"] > 0.9
        assert result["s2"] > 0.9

    def test_a_strategy_that_disagrees_with_the_majority_gets_lower_confidence(self) -> None:
        """Three strategies agree with each other; a fourth is the mirror
        opposite on every row. EM should assign the outlier strategy
        noticeably lower confidence than the three that agree.
        """
        base = np.array([1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1])
        opposite = 1 - base
        estimator = EMQualityEstimator()
        result = estimator.estimate(
            {"agree_1": base.copy(), "agree_2": base.copy(), "agree_3": base.copy(), "outlier": opposite}
        )
        avg_agreeing_confidence = (result["agree_1"] + result["agree_2"] + result["agree_3"]) / 3
        assert result["outlier"] < avg_agreeing_confidence

    def test_confidences_are_within_valid_range(self) -> None:
        rng = np.random.default_rng(1)
        labels = {f"s{i}": rng.integers(0, 2, size=50) for i in range(4)}
        estimator = EMQualityEstimator()
        result = estimator.estimate(labels)
        for confidence in result.values():
            assert 0.0 <= confidence <= 1.0
            assert type(confidence) is float  # noqa: E721

    def test_deterministic_across_repeated_calls(self) -> None:
        rng = np.random.default_rng(2)
        labels = {f"s{i}": rng.integers(0, 2, size=30) for i in range(3)}
        estimator = EMQualityEstimator()
        first = estimator.estimate({k: v.copy() for k, v in labels.items()})
        second = estimator.estimate({k: v.copy() for k, v in labels.items()})
        assert first == second

    def test_respects_configured_max_iterations(self) -> None:
        rng = np.random.default_rng(3)
        labels = {f"s{i}": rng.integers(0, 2, size=20) for i in range(3)}
        # A single iteration should still return a valid (if less converged) result, not crash.
        estimator = EMQualityEstimator(max_iterations=1)
        result = estimator.estimate(labels)
        assert len(result) == 3
        for confidence in result.values():
            assert 0.0 <= confidence <= 1.0
