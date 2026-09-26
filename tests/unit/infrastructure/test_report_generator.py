"""Unit tests for ReportGenerator and GenerateReportUseCase (Phase 8).

Includes a regression test for the real bug found while running the CLI:
the template originally referenced a top-level `validation_notes` variable
that was never actually passed, leaving the Summary section blank.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autoclean.application.use_cases.generate_report import GenerateReportUseCase
from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.entities.validation_report import ValidationReport
from autoclean.infrastructure.reporting.report_generator import ReportGenerator

pytestmark = pytest.mark.unit


def _sample_context() -> dict:
    profile = DatasetProfile(row_count=10, column_count=3, missing_value_pct=5.0, duplicate_row_count=1, outlier_count=1)
    score = EvaluationScore(
        data_quality_score=0.81, computational_cost_score=0.98, information_preservation_score=0.70,
        statistical_validity_score=0.89, fairness_impact_score=0.5, downstream_ml_score=0.5, em_confidence=1.0,
    )
    strategy = CleaningStrategy(
        strategy_id="s1", name="Conservative", description="Imputes and clips.",
        steps=(CleaningStep(operation=CleaningOperation.MEDIAN_IMPUTATION, target_column="age"),),
    )
    validation = ValidationReport(
        schema_consistent=True, quality_threshold_met=True, quality_score=0.81, quality_threshold=0.5,
        row_count_before=10, row_count_after=8, remaining_issue_count=2,
        notes="Quality score 0.81 vs. threshold 0.50 (met). 2 issue(s) remain.",
    )
    return {
        "experiment_id": "exp-1", "dataset_name": "test.csv", "generated_at": "2026-01-01T00:00:00",
        "original_profile": profile, "cleaned_profile": profile, "strategy": strategy, "score": score,
        "alternatives": [], "explanation_text": "This is the explanation.", "consistency_warnings": [],
        "decided_by": "tester", "decided_at": "2026-01-01T00:00:00", "validation": validation,
    }


class TestReportGenerator:
    def test_generates_a_real_file(self, tmp_path: Path) -> None:
        path = ReportGenerator().generate(_sample_context(), str(tmp_path / "report.md"))
        assert Path(path).exists()

    def test_summary_section_is_not_blank(self, tmp_path: Path) -> None:
        """Regression test: found as a real bug where the Summary section
        rendered empty because the template referenced a variable
        (`validation_notes`) that was never passed in context.
        """
        path = ReportGenerator().generate(_sample_context(), str(tmp_path / "report.md"))
        text = Path(path).read_text()
        summary_section = text.split("## Summary")[1].split("## Dataset Profile")[0].strip()
        assert summary_section != ""
        assert "Quality score" in summary_section

    def test_report_contains_real_scores_not_placeholders(self, tmp_path: Path) -> None:
        path = ReportGenerator().generate(_sample_context(), str(tmp_path / "report.md"))
        text = Path(path).read_text()
        assert "0.81" in text
        assert "0.98" in text

    def test_report_includes_strategy_name_and_steps(self, tmp_path: Path) -> None:
        path = ReportGenerator().generate(_sample_context(), str(tmp_path / "report.md"))
        text = Path(path).read_text()
        assert "Conservative" in text
        assert "median_imputation" in text

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested_path = str(tmp_path / "nested" / "dir" / "report.md")
        path = ReportGenerator().generate(_sample_context(), nested_path)
        assert Path(path).exists()


class TestGenerateReportUseCase:
    def test_execute_produces_both_report_and_script(self, tmp_path: Path) -> None:
        context = _sample_context()
        report_path, script_path = GenerateReportUseCase().execute(
            context, context["strategy"], str(tmp_path / "report.md"), str(tmp_path / "script.py")
        )
        assert Path(report_path).exists()
        assert Path(script_path).exists()
