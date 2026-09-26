"""Unit tests for Domain layer entities (Phase 4).

These tests exercise ONLY the Domain layer: no Pandas, no SQLite, no LLM.
Per Phase 2's Clean Architecture rule, this is meant to be possible with zero
I/O, and these tests double as a regression check on that architectural rule
itself -- if a Domain entity ever gains a framework dependency, these tests
will fail to import cleanly, in addition to any explicit lint rule.
"""

from __future__ import annotations

import pytest

from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)
from autoclean.domain.entities.data_issue import DataIssue, IssueType
from autoclean.domain.entities.dataset import Dataset, DatasetProfile
from autoclean.domain.entities.decision import Decision, DecisionType
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.entities.experiment import Experiment, ExperimentStatus
from autoclean.domain.value_objects.objective_weights import ObjectiveWeights

pytestmark = pytest.mark.unit


class TestDatasetProfile:
    def test_valid_profile_constructs(self) -> None:
        profile = DatasetProfile(
            row_count=100, column_count=5, missing_value_pct=2.5,
            duplicate_row_count=3, outlier_count=1,
        )
        assert profile.has_quality_issues is True

    def test_no_issues_when_all_zero(self) -> None:
        profile = DatasetProfile(
            row_count=100, column_count=5, missing_value_pct=0.0,
            duplicate_row_count=0, outlier_count=0,
        )
        assert profile.has_quality_issues is False

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"row_count": -1},
            {"column_count": -1},
            {"missing_value_pct": 101.0},
            {"missing_value_pct": -1.0},
            {"duplicate_row_count": -1},
            {"outlier_count": -1},
        ],
    )
    def test_invalid_values_raise(self, kwargs: dict) -> None:
        base = {
            "row_count": 10, "column_count": 2, "missing_value_pct": 0.0,
            "duplicate_row_count": 0, "outlier_count": 0,
        }
        base.update(kwargs)
        with pytest.raises(ValueError):
            DatasetProfile(**base)


class TestDataset:
    def test_valid_dataset_constructs(self) -> None:
        dataset = Dataset(path="/tmp/data.csv", file_format="csv")
        assert dataset.profile is None

    def test_unsupported_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported file_format"):
            Dataset(path="/tmp/data.json", file_format="json")

    def test_empty_path_raises(self) -> None:
        with pytest.raises(ValueError):
            Dataset(path="", file_format="csv")


class TestDataIssue:
    def test_valid_issue_constructs(self) -> None:
        issue = DataIssue(
            issue_type=IssueType.MISSING_VALUES, column="age",
            severity=0.5, affected_row_count=5, description="test",
        )
        assert issue.severity == 0.5

    def test_severity_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="severity"):
            DataIssue(
                issue_type=IssueType.MISSING_VALUES, column="age",
                severity=1.5, affected_row_count=5, description="test",
            )

    def test_column_required_except_for_duplicates(self) -> None:
        with pytest.raises(ValueError, match="column is required"):
            DataIssue(
                issue_type=IssueType.OUTLIERS, column=None,
                severity=0.1, affected_row_count=1, description="test",
            )

    def test_duplicate_rows_issue_allows_null_column(self) -> None:
        issue = DataIssue(
            issue_type=IssueType.DUPLICATE_ROWS, column=None,
            severity=0.1, affected_row_count=2, description="test",
        )
        assert issue.column is None


class TestCleaningStrategyRoundTrip:
    def test_to_dict_from_dict_round_trip(self) -> None:
        step = CleaningStep(
            operation=CleaningOperation.MEDIAN_IMPUTATION,
            target_column="age",
            parameters={"foo": "bar"},
        )
        strategy = CleaningStrategy(
            strategy_id="s1", name="Test Strategy", steps=(step,),
            is_baseline=True, description="desc",
        )
        restored = CleaningStrategy.from_dict(strategy.to_dict())
        assert restored == strategy

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError):
            CleaningStrategy(strategy_id="s1", name="", steps=())


class TestObjectiveWeights:
    def test_weights_must_sum_to_one(self) -> None:
        with pytest.raises(ValueError, match="sum to 1.0"):
            ObjectiveWeights(
                data_quality=0.5, computational_cost=0.5,
                information_preservation=0.5, statistical_validity=0.0,
                fairness_impact=0.0, downstream_ml=0.0,
            )

    def test_uniform_weights_sum_to_one(self) -> None:
        weights = ObjectiveWeights.uniform()
        total = (
            weights.data_quality + weights.computational_cost
            + weights.information_preservation + weights.statistical_validity
            + weights.fairness_impact + weights.downstream_ml
        )
        assert total == pytest.approx(1.0)

    def test_from_mapping_missing_key_raises(self) -> None:
        with pytest.raises(KeyError):
            ObjectiveWeights.from_mapping({"data_quality": 1.0})

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            ObjectiveWeights(
                data_quality=-0.1, computational_cost=0.3,
                information_preservation=0.2, statistical_validity=0.2,
                fairness_impact=0.2, downstream_ml=0.2,
            )


class TestEvaluationScore:
    def test_weighted_total_computation(self) -> None:
        score = EvaluationScore(
            data_quality_score=1.0, computational_cost_score=1.0,
            information_preservation_score=1.0, statistical_validity_score=1.0,
            fairness_impact_score=1.0, downstream_ml_score=1.0,
        )
        weights = ObjectiveWeights.uniform()
        assert score.compute_weighted_total(weights) == pytest.approx(1.0)

    def test_out_of_range_score_raises(self) -> None:
        with pytest.raises(ValueError):
            EvaluationScore(
                data_quality_score=1.5, computational_cost_score=0.5,
                information_preservation_score=0.5, statistical_validity_score=0.5,
                fairness_impact_score=0.5, downstream_ml_score=0.5,
            )

    def test_as_dict_contains_all_fields(self) -> None:
        score = EvaluationScore(
            data_quality_score=0.1, computational_cost_score=0.2,
            information_preservation_score=0.3, statistical_validity_score=0.4,
            fairness_impact_score=0.5, downstream_ml_score=0.6, em_confidence=0.7,
        )
        result = score.as_dict()
        assert set(result.keys()) == {
            "data_quality_score", "computational_cost_score",
            "information_preservation_score", "statistical_validity_score",
            "fairness_impact_score", "downstream_ml_score", "em_confidence",
        }


class TestExperiment:
    def _sample_strategy(self, strategy_id: str = "s1") -> CleaningStrategy:
        return CleaningStrategy(
            strategy_id=strategy_id, name="Test",
            steps=(CleaningStep(operation=CleaningOperation.NO_OP),),
        )

    def test_mark_completed_with_known_strategy(self) -> None:
        strategy = self._sample_strategy()
        experiment = Experiment(
            id="e1", dataset_name="data.csv", dataset_hash="h1",
            candidate_strategies=[strategy],
        )
        experiment.mark_completed(strategy.strategy_id)
        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.approved_strategy_id == strategy.strategy_id
        assert experiment.completed_at is not None

    def test_mark_completed_with_unknown_strategy_raises(self) -> None:
        experiment = Experiment(
            id="e1", dataset_name="data.csv", dataset_hash="h1",
            candidate_strategies=[self._sample_strategy("s1")],
        )
        with pytest.raises(ValueError, match="not among"):
            experiment.mark_completed("unknown-id")


class TestDecision:
    def test_valid_decision_constructs(self) -> None:
        decision = Decision(
            id="d1", experiment_id="e1", strategy_id="s1",
            decision_type=DecisionType.APPROVED, decided_by="analyst",
            decided_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
        assert decision.decision_type == DecisionType.APPROVED

    def test_empty_required_field_raises(self) -> None:
        with pytest.raises(ValueError):
            Decision(
                id="", experiment_id="e1", strategy_id="s1",
                decision_type=DecisionType.APPROVED, decided_by="analyst",
                decided_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            )
