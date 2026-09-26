"""Unit tests for SQLiteExperimentRepository (Phase 5), against a real,
temporary on-disk SQLite database (not mocked) -- since the whole point of
this class is correct SQL against the actual Phase 4 schema, a mock would
test nothing meaningful here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.decision import Decision, DecisionType
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.entities.experiment import Experiment
from autoclean.infrastructure.persistence.sqlite.db_session import initialize_database
from autoclean.infrastructure.persistence.sqlite.experiment_repository_impl import (
    SQLiteExperimentRepository,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def repository(tmp_path: Path) -> SQLiteExperimentRepository:
    connection = initialize_database(tmp_path / "test.db")
    return SQLiteExperimentRepository(connection)


def _sample_strategy(strategy_id: str = "s1") -> CleaningStrategy:
    return CleaningStrategy(
        strategy_id=strategy_id,
        name="Test Strategy",
        steps=(CleaningStep(operation=CleaningOperation.MEDIAN_IMPUTATION, target_column="age"),),
    )


class TestExperimentRoundTrip:
    def test_save_and_get_experiment(self, repository: SQLiteExperimentRepository) -> None:
        experiment = Experiment(id="e1", dataset_name="data.csv", dataset_hash="hash1")
        repository.save_experiment(experiment)

        loaded = repository.get_experiment("e1")
        assert loaded is not None
        assert loaded.dataset_name == "data.csv"
        assert loaded.status == experiment.status

    def test_get_nonexistent_experiment_returns_none(self, repository: SQLiteExperimentRepository) -> None:
        assert repository.get_experiment("does-not-exist") is None

    def test_save_experiment_with_profile_persists_profile(
        self, repository: SQLiteExperimentRepository
    ) -> None:
        experiment = Experiment(
            id="e1", dataset_name="data.csv", dataset_hash="hash1",
            dataset_profile=DatasetProfile(
                row_count=10, column_count=3, missing_value_pct=5.0,
                duplicate_row_count=1, outlier_count=0,
            ),
        )
        repository.save_experiment(experiment)
        row = repository._connection.execute(
            "SELECT * FROM dataset_profiles WHERE experiment_id = ?", ("e1",)
        ).fetchone()
        assert row is not None
        assert row["row_count"] == 10

    def test_list_experiments_returns_all(self, repository: SQLiteExperimentRepository) -> None:
        repository.save_experiment(Experiment(id="e1", dataset_name="a.csv", dataset_hash="h1"))
        repository.save_experiment(Experiment(id="e2", dataset_name="b.csv", dataset_hash="h2"))
        experiments = repository.list_experiments()
        assert {e.id for e in experiments} == {"e1", "e2"}


class TestCandidateStrategiesRoundTrip:
    def test_save_and_load_strategies_round_trip(self, repository: SQLiteExperimentRepository) -> None:
        repository.save_experiment(Experiment(id="e1", dataset_name="a.csv", dataset_hash="h1"))
        strategy = _sample_strategy()
        repository.save_candidate_strategies("e1", [strategy])

        loaded = repository.get_experiment("e1")
        assert loaded is not None
        assert len(loaded.candidate_strategies) == 1
        assert loaded.candidate_strategies[0] == strategy


class TestStrategyScorePersistence:
    def test_save_strategy_score(self, repository: SQLiteExperimentRepository) -> None:
        repository.save_experiment(Experiment(id="e1", dataset_name="a.csv", dataset_hash="h1"))
        repository.save_candidate_strategies("e1", [_sample_strategy()])

        score = EvaluationScore(
            data_quality_score=0.8, computational_cost_score=0.7,
            information_preservation_score=0.5, statistical_validity_score=0.5,
            fairness_impact_score=0.5, downstream_ml_score=0.5,
        )
        repository.save_strategy_score("s1", score, weighted_total=0.6, weights_used={"data_quality": 1.0})

        row = repository._connection.execute(
            "SELECT * FROM strategy_scores WHERE strategy_id = ?", ("s1",)
        ).fetchone()
        assert row is not None
        assert row["data_quality_score"] == 0.8
        assert row["weighted_total_score"] == 0.6


class TestDecisionsAndAuditTrail:
    def test_save_decision_and_audit_event(self, repository: SQLiteExperimentRepository) -> None:
        repository.save_experiment(Experiment(id="e1", dataset_name="a.csv", dataset_hash="h1"))
        repository.save_candidate_strategies("e1", [_sample_strategy()])

        decision = Decision(
            id=str(uuid.uuid4()), experiment_id="e1", strategy_id="s1",
            decision_type=DecisionType.APPROVED, decided_by="analyst",
            decided_at=datetime.now(UTC),
        )
        repository.save_decision(decision)

        event = AuditEvent(
            id=str(uuid.uuid4()), experiment_id="e1", event_type="test_event", actor="tester",
        )
        repository.append_audit_event(event)

        trail = repository.get_audit_trail("e1")
        assert len(trail) == 1
        assert trail[0].event_type == "test_event"

    def test_audit_trail_ordered_chronologically(self, repository: SQLiteExperimentRepository) -> None:
        repository.save_experiment(Experiment(id="e1", dataset_name="a.csv", dataset_hash="h1"))
        for i in range(3):
            repository.append_audit_event(
                AuditEvent(id=str(uuid.uuid4()), experiment_id="e1", event_type=f"event_{i}", actor="tester")
            )
        trail = repository.get_audit_trail("e1")
        assert [event.event_type for event in trail] == ["event_0", "event_1", "event_2"]
