"""Unit tests for infrastructure.persistence.sqlite.db_session.

Uses a temporary on-disk SQLite file per test (via Pytest's `tmp_path`
fixture) rather than a shared or production database, keeping these tests
isolated and side-effect free.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autoclean.infrastructure.persistence.sqlite.db_session import (
    apply_schema,
    get_connection,
    initialize_database,
)

pytestmark = pytest.mark.unit

EXPECTED_TABLES = {
    "experiments",
    "dataset_profiles",
    "candidate_strategies",
    "strategy_scores",
    "decisions",
    "audit_log",
    "reports",
}


class TestDbSession:
    def test_initialize_database_creates_all_expected_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        connection = initialize_database(db_path)
        try:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {row["name"] for row in rows}
            assert EXPECTED_TABLES.issubset(table_names)
        finally:
            connection.close()

    def test_apply_schema_is_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        connection = get_connection(db_path)
        try:
            apply_schema(connection)
            apply_schema(connection)  # must not raise on second application
        finally:
            connection.close()

    def test_foreign_keys_enforced(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        connection = initialize_database(db_path)
        try:
            with pytest.raises(Exception):  # sqlite3.IntegrityError
                connection.execute(
                    "INSERT INTO dataset_profiles "
                    "(id, experiment_id, row_count, column_count, missing_value_pct, "
                    "duplicate_count, outlier_count, created_at) "
                    "VALUES ('p1', 'nonexistent-experiment', 10, 2, 0.0, 0, 0, '2026-01-01')"
                )
                connection.commit()
        finally:
            connection.close()

    def test_creates_parent_directory_if_missing(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nested" / "dir" / "test.db"
        connection = initialize_database(db_path)
        try:
            assert db_path.parent.exists()
        finally:
            connection.close()
