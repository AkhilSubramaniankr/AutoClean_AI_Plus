"""SQLite connection/session bootstrap.

Deliberately minimal for Phase 4: applies `schema.sql` idempotently
(`CREATE TABLE IF NOT EXISTS`) and exposes a raw `sqlite3` connection
factory. Full repository classes implementing the `IExperimentRepository` /
etc. port interfaces (Phase 2, Section 12, Repository pattern) are deferred
to Phase 5, once the Application-layer ports those repositories implement
are themselves defined (per the Phase 2 folder structure, `application/ports/`
is populated starting Phase 5). This module intentionally stops at "can we
open a connection and apply the schema," which is squarely Phase 4 scope
(Core Data Processing's persistence foundation), not Phase 5's Repository
pattern implementation.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(database_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection to `database_path`, creating parent
    directories if needed. Row factory is set to `sqlite3.Row` so query
    results are accessible by column name, which Phase 5's repository
    implementations will rely on.
    """
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def apply_schema(connection: sqlite3.Connection, schema_path: Path = _SCHEMA_PATH) -> None:
    """Apply `schema.sql` to `connection`. Idempotent: every statement in
    schema.sql uses `CREATE TABLE/INDEX IF NOT EXISTS`, so this is safe to
    call on every application startup.
    """
    schema_sql = schema_path.read_text(encoding="utf-8")
    with connection:
        connection.executescript(schema_sql)
    logger.info("SQLite schema applied", extra={"schema_path": str(schema_path)})


def initialize_database(database_path: Path) -> sqlite3.Connection:
    """Convenience entry point: open a connection and ensure the schema exists."""
    connection = get_connection(database_path)
    apply_schema(connection)
    return connection
