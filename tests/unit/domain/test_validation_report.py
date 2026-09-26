"""Unit tests for the ValidationReport domain entity (Phase 8)."""

from __future__ import annotations

import pytest

from autoclean.domain.entities.validation_report import ValidationReport

pytestmark = pytest.mark.unit


def _report(**overrides) -> ValidationReport:
    defaults = dict(
        schema_consistent=True, quality_threshold_met=True, quality_score=0.8,
        quality_threshold=0.5, row_count_before=10, row_count_after=8,
        remaining_issue_count=1, notes="test",
    )
    defaults.update(overrides)
    return ValidationReport(**defaults)


class TestValidationReport:
    def test_passed_true_when_both_checks_pass(self) -> None:
        assert _report(schema_consistent=True, quality_threshold_met=True).passed is True

    def test_passed_false_if_schema_inconsistent_even_with_good_quality(self) -> None:
        assert _report(schema_consistent=False, quality_threshold_met=True).passed is False

    def test_passed_false_if_quality_threshold_not_met_even_with_consistent_schema(self) -> None:
        assert _report(schema_consistent=True, quality_threshold_met=False).passed is False

    def test_invalid_quality_score_raises(self) -> None:
        with pytest.raises(ValueError, match="quality_score"):
            _report(quality_score=1.5)

    def test_negative_row_count_raises(self) -> None:
        with pytest.raises(ValueError, match="row counts"):
            _report(row_count_before=-1)

    def test_negative_remaining_issue_count_raises(self) -> None:
        with pytest.raises(ValueError, match="remaining_issue_count"):
            _report(remaining_issue_count=-1)
