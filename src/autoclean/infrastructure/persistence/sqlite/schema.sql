-- AutoClean AI+ SQLite schema.
-- Directly implements the ERD from docs/phase_deliverables/Phase2_System_Design.md,
-- Section 7. All primary keys are TEXT (UUIDs) generated in-memory by the Domain
-- layer, per that section's design decision, so IDs remain stable across
-- WorkflowState, these rows, and exported report/script filenames.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS experiments (
    id                      TEXT PRIMARY KEY,
    dataset_name            TEXT NOT NULL,
    dataset_hash            TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    status                  TEXT NOT NULL,
    approved_strategy_id    TEXT,
    completed_at            TEXT
);

CREATE TABLE IF NOT EXISTS dataset_profiles (
    id                      TEXT PRIMARY KEY,
    experiment_id           TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    row_count               INTEGER NOT NULL,
    column_count            INTEGER NOT NULL,
    missing_value_pct       REAL NOT NULL,
    duplicate_count         INTEGER NOT NULL,
    outlier_count           INTEGER NOT NULL,
    dtype_issues_json       TEXT NOT NULL DEFAULT '{}',
    created_at              TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_strategies (
    id                          TEXT PRIMARY KEY,
    experiment_id               TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    strategy_name                TEXT NOT NULL,
    strategy_definition_json     TEXT NOT NULL,
    rank                          INTEGER,
    is_baseline                   INTEGER NOT NULL DEFAULT 0,
    created_at                    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_scores (
    id                              TEXT PRIMARY KEY,
    strategy_id                     TEXT NOT NULL REFERENCES candidate_strategies(id) ON DELETE CASCADE,
    data_quality_score              REAL NOT NULL,
    computational_cost_score        REAL NOT NULL,
    information_preservation_score  REAL NOT NULL,
    statistical_validity_score      REAL NOT NULL,
    fairness_impact_score           REAL NOT NULL,
    downstream_ml_score             REAL NOT NULL,
    weighted_total_score            REAL NOT NULL,
    em_confidence                   REAL NOT NULL DEFAULT 0.0,
    weights_used_json               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id              TEXT PRIMARY KEY,
    experiment_id   TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    strategy_id     TEXT NOT NULL REFERENCES candidate_strategies(id) ON DELETE CASCADE,
    decision        TEXT NOT NULL,
    decided_by      TEXT NOT NULL,
    decided_at      TEXT NOT NULL,
    rationale_text  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS audit_log (
    id                  TEXT PRIMARY KEY,
    experiment_id       TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL,
    event_payload_json  TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id              TEXT PRIMARY KEY,
    experiment_id   TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    report_path     TEXT NOT NULL,
    script_path     TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dataset_profiles_experiment_id ON dataset_profiles(experiment_id);
CREATE INDEX IF NOT EXISTS idx_candidate_strategies_experiment_id ON candidate_strategies(experiment_id);
CREATE INDEX IF NOT EXISTS idx_strategy_scores_strategy_id ON strategy_scores(strategy_id);
CREATE INDEX IF NOT EXISTS idx_decisions_experiment_id ON decisions(experiment_id);
CREATE INDEX IF NOT EXISTS idx_decisions_strategy_id ON decisions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_experiment_id ON audit_log(experiment_id);
CREATE INDEX IF NOT EXISTS idx_reports_experiment_id ON reports(experiment_id);
