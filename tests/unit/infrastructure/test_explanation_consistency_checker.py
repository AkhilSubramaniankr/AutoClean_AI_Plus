"""Unit tests for explanation_consistency_checker.py (Phase 7).

Includes an explicit regression test for the range-descriptor false
positive found while running scripts/run_workflow_cli.py: the literal text
"(0.0-1.0, higher is better)" must NOT be flagged as a fabricated score.
"""

from __future__ import annotations

import pytest

from autoclean.infrastructure.llm.explanation_consistency_checker import check_consistency

pytestmark = pytest.mark.unit

_SAMPLE_CONTEXT = {
    "recommended_score": {
        "data_quality_score": 0.81,
        "computational_cost_score": 0.98,
        "information_preservation_score": 0.70,
        "statistical_validity_score": 0.89,
        "fairness_impact_score": 0.5,
        "downstream_ml_score": 0.5,
        "em_confidence": 1.0,
    },
    "alternatives": [
        {"score": {"data_quality_score": 0.62, "computational_cost_score": 0.99}},
    ],
}


class TestCheckConsistency:
    def test_explanation_using_only_real_numbers_has_no_warnings(self) -> None:
        text = "This strategy has data quality 0.81 and cost 0.98, compared to 0.62 for the baseline."
        assert check_consistency(text, _SAMPLE_CONTEXT) == []

    def test_fabricated_number_is_flagged(self) -> None:
        text = "This strategy has data quality 0.81 but was also tested at 0.42 accuracy."
        warnings = check_consistency(text, _SAMPLE_CONTEXT)
        assert len(warnings) == 1
        assert "0.42" in warnings[0]

    def test_range_descriptor_is_not_flagged_as_fabrication(self) -> None:
        """Regression test: found as a real false positive while running
        the CLI. "(0.0-1.0, higher is better)" is a range LABEL, not a claim.
        """
        text = (
            "Scores (0.0-1.0, higher is better; computed by RealMetricsEngine): "
            "data quality 0.81, cost 0.98."
        )
        assert check_consistency(text, _SAMPLE_CONTEXT) == []

    def test_number_within_rounding_tolerance_is_not_flagged(self) -> None:
        # Real value is 0.81; text rounds slightly differently but within tolerance.
        text = "Data quality is approximately 0.815."
        assert check_consistency(text, _SAMPLE_CONTEXT) == []

    def test_value_of_exactly_one_point_zero_is_recognized(self) -> None:
        text = "The confidence in this recommendation is 1.0, the maximum possible."
        assert check_consistency(text, _SAMPLE_CONTEXT) == []

    def test_no_real_scores_in_context_returns_a_warning(self) -> None:
        warnings = check_consistency("Some text with 0.5 in it.", {"recommended_score": {}, "alternatives": []})
        assert len(warnings) == 1
        assert "No real scores" in warnings[0]

    def test_never_raises_on_malformed_context(self) -> None:
        # Missing keys entirely -- must degrade gracefully, not crash.
        result = check_consistency("Some explanation text.", {})
        assert isinstance(result, list)

    def test_text_with_no_numbers_at_all_has_no_warnings(self) -> None:
        text = "This strategy is a good choice because it handles missing data well."
        assert check_consistency(text, _SAMPLE_CONTEXT) == []
