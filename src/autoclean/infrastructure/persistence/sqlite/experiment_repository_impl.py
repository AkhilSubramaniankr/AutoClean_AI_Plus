"""Concrete IExperimentRepository implementation, backed by SQLite.

Implements the Repository pattern (Phase 2, Section 12) against the schema
created in Phase 4 (`schema.sql`). Uses the standard library `sqlite3`
directly (matching the `db_session.py` connection style established in
Phase 4) rather than the SQLAlchemy ORM also listed in `requirements.txt` --
for a single-user, single-file SQLite database with a small, fixed schema,
hand-written SQL is simpler to audit line-by-line against `schema.sql` than
an ORM mapping layer would be, and avoids introducing ORM session-lifecycle
concerns (unit-of-work, lazy loading) that this project's simple,
short-lived read/write patterns don't need.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from autoclean.application.ports.experiment_repository import IExperimentRepository
from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.decision import Decision, DecisionType
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.entities.experiment import Experiment, ExperimentStatus


class SQLiteExperimentRepository(IExperimentRepository):
    """SQLite-backed IExperimentRepository. Not thread-safe by itself --
    callers should use one instance per SQLite connection, matching Python's
    stdlib `sqlite3` connection threading model.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------

    def save_experiment(self, experiment: Experiment) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO experiments (id, dataset_name, dataset_hash, created_at, status,
                    approved_strategy_id, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    approved_strategy_id = excluded.approved_strategy_id,
                    completed_at = excluded.completed_at
                """,
                (
                    experiment.id,
                    experiment.dataset_name,
                    experiment.dataset_hash,
                    experiment.created_at.isoformat(),
                    experiment.status.value,
                    experiment.approved_strategy_id,
                    experiment.completed_at.isoformat() if experiment.completed_at else None,
                ),
            )
            if experiment.dataset_profile is not None:
                self._save_dataset_profile(experiment.id, experiment.dataset_profile)

    def _save_dataset_profile(self, experiment_id: str, profile: DatasetProfile) -> None:
        self._connection.execute(
            """
            INSERT INTO dataset_profiles (id, experiment_id, row_count, column_count,
                missing_value_pct, duplicate_count, outlier_count, dtype_issues_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                experiment_id,
                profile.row_count,
                profile.column_count,
                profile.missing_value_pct,
                profile.duplicate_row_count,
                profile.outlier_count,
                json.dumps(profile.dtype_issue_columns),
                datetime.now(UTC).isoformat(),
            ),
        )

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        row = self._connection.execute(
            "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
        if row is None:
            return None

        strategies = self._load_candidate_strategies(experiment_id)
        experiment = Experiment(
            id=row["id"],
            dataset_name=row["dataset_name"],
            dataset_hash=row["dataset_hash"],
            status=ExperimentStatus(row["status"]),
            candidate_strategies=strategies,
            approved_strategy_id=row["approved_strategy_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )
        return experiment

    def list_experiments(self) -> list[Experiment]:
        rows = self._connection.execute(
            "SELECT id FROM experiments ORDER BY created_at DESC"
        ).fetchall()
        experiments = []
        for row in rows:
            experiment = self.get_experiment(row["id"])
            if experiment is not None:
                experiments.append(experiment)
        return experiments

    def _load_candidate_strategies(self, experiment_id: str) -> list[CleaningStrategy]:
        rows = self._connection.execute(
            "SELECT strategy_definition_json FROM candidate_strategies WHERE experiment_id = ? "
            "ORDER BY created_at",
            (experiment_id,),
        ).fetchall()
        return [CleaningStrategy.from_dict(json.loads(row["strategy_definition_json"])) for row in rows]

    # ------------------------------------------------------------------
    # Candidate strategies & scores
    # ------------------------------------------------------------------

    def save_candidate_strategies(
        self, experiment_id: str, strategies: list[CleaningStrategy]
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connection:
            for strategy in strategies:
                self._connection.execute(
                    """
                    INSERT INTO candidate_strategies (id, experiment_id, strategy_name,
                        strategy_definition_json, rank, is_baseline, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        strategy.strategy_id,
                        experiment_id,
                        strategy.name,
                        json.dumps(strategy.to_dict()),
                        None,
                        int(strategy.is_baseline),
                        now,
                    ),
                )

    def save_strategy_score(
        self,
        strategy_id: str,
        score: EvaluationScore,
        weighted_total: float,
        weights_used: dict[str, object],
    ) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO strategy_scores (id, strategy_id, data_quality_score,
                    computational_cost_score, information_preservation_score,
                    statistical_validity_score, fairness_impact_score, downstream_ml_score,
                    weighted_total_score, em_confidence, weights_used_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    strategy_id,
                    score.data_quality_score,
                    score.computational_cost_score,
                    score.information_preservation_score,
                    score.statistical_validity_score,
                    score.fairness_impact_score,
                    score.downstream_ml_score,
                    weighted_total,
                    score.em_confidence,
                    json.dumps(weights_used),
                ),
            )

    # ------------------------------------------------------------------
    # Decisions & audit trail
    # ------------------------------------------------------------------

    def save_decision(self, decision: Decision) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO decisions (id, experiment_id, strategy_id, decision, decided_by,
                    decided_at, rationale_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.id,
                    decision.experiment_id,
                    decision.strategy_id,
                    decision.decision_type.value,
                    decision.decided_by,
                    decision.decided_at.isoformat(),
                    decision.rationale,
                ),
            )

    def append_audit_event(self, event: AuditEvent) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO audit_log (id, experiment_id, event_type, event_payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.experiment_id,
                    event.event_type,
                    json.dumps(event.payload),
                    event.timestamp.isoformat(),
                ),
            )

    def get_audit_trail(self, experiment_id: str) -> list[AuditEvent]:
        rows = self._connection.execute(
            "SELECT * FROM audit_log WHERE experiment_id = ? ORDER BY created_at",
            (experiment_id,),
        ).fetchall()
        return [
            AuditEvent(
                id=row["id"],
                experiment_id=row["experiment_id"],
                event_type=row["event_type"],
                actor=json.loads(row["event_payload_json"]).get("actor", "unknown"),
                timestamp=datetime.fromisoformat(row["created_at"]),
                payload=json.loads(row["event_payload_json"]),
            )
            for row in rows
        ]
