# Changelog

All notable changes to the AutoClean AI+ project are documented in this file, organized by project phase.

## [Phase 9] - Dashboard Development

### Added
- `src/autoclean/presentation/streamlit_app.py`: thin main entry point.
- `src/autoclean/presentation/workflow_session.py`: session-cached graph +
  repository + dependency wiring — required so LangGraph's human-approval
  interrupt survives Streamlit's rerun-per-click execution model.
- `src/autoclean/presentation/pages/`: `1_Upload_and_Profile.py`,
  `2_Compare_Strategies.py`, `3_Review_and_Approve.py`,
  `4_Experiment_History.py`.
- `src/autoclean/presentation/components/`: `strategy_comparison_chart.py`
  (pure function returning a `plotly.graph_objects.Figure`),
  `explanation_panel.py`.
- 25 new tests across 6 new test files in `tests/unit/presentation/`.
- `docs/phase_deliverables/Phase9_Dashboard_Development.md`.
- `make dashboard` convenience target.

### Changed
- Removed `pages/__init__.py` — Streamlit's `pages/` folder is not a normal
  Python package; an `__init__.py` there renders as an unwanted blank page
  in the sidebar navigation.

### Discovered and Documented
- Streamlit's `AppTest` framework cannot simulate `file_uploader`
  interactions (confirmed by inspecting the test element's available
  methods — no `set_value`-style API exists). Resolved at the correct
  testing boundary: `get_workflow_session()` is mocked so each page's own
  button-to-backend-call wiring is tested directly and precisely
  (`MagicMock.assert_called_once_with(...)`), while the real graph
  execution this wiring drives is already proven, independent of any UI,
  by the Phase 5/8 integration tests.

### Fixed
- A real bug caught before shipping: an early draft of Page 1 used
  `ObjectiveWeights.uniform()` when persisting display metadata, instead
  of the actual weights used to rank strategies. Fixed by exposing the
  real `ObjectiveWeights` instance from `WorkflowSession`.

### Verified
- 222 tests passing (25 new), 95.24% coverage, 0 mypy issues across 83
  source files.
- The **real Streamlit server was launched** (`streamlit run`, not just
  `AppTest`) and confirmed responding with HTTP 200 on `/_stcore/health`.
- Page tests use real Phase 4/6 engine output (real profiles, real
  generated strategies, real scores), not fabricated data.

### Notes
- The application is now functionally complete end-to-end, including a
  real UI. Phases 10–12 consolidate, harden, deploy, and document what
  already works — no new core functionality remains to be built.
- Phase 10 (Testing) will not begin until this Phase 9 document and code
  are approved.

## [Phase 8] - Cleaning Execution & Validation

### Added
- `src/autoclean/domain/entities/validation_report.py`: `ValidationReport`
  (named in Phase 2's class diagram, built now) — `schema_consistent`,
  `quality_threshold_met`, `quality_score`, `remaining_issue_count`, and a
  `.passed` property.
- `src/autoclean/application/use_cases/execute_cleaning.py`:
  `ExecuteCleaningUseCase` — applies the approved strategy via
  `StrategyExecutor` (reused from Phase 6) and saves the real cleaned file.
- `src/autoclean/application/use_cases/validate_cleaned_dataset.py`:
  `ValidateCleanedDatasetUseCase` — reuses `quality_metrics.compute_quality_score`
  (the same function used for ranking in Phase 6) for a single consistent
  definition of "quality improvement."
- `src/autoclean/application/use_cases/generate_report.py`:
  `GenerateReportUseCase`.
- `src/autoclean/infrastructure/reporting/report_generator.py`:
  `ReportGenerator` — Jinja2-rendered Markdown executive report.
- `src/autoclean/infrastructure/reporting/script_exporter.py`:
  `ScriptExporter` — a genuinely standalone, dependency-free reproducible
  cleaning script (FR-12).
- 27 new tests across 5 new test files.
- `docs/phase_deliverables/Phase8_Cleaning_Execution_and_Validation.md`.

### Changed
- `execution_node.py`, `validation_node.py`, `reporting_node.py` rewritten
  from Phase 5 stub functions into real, dependency-injected classes
  (`ExecutionNode`, `ValidationNode`, `ReportingNode`), matching the Agent
  pattern already used elsewhere.
- **`graph_builder.build_graph()` signature revised**: now requires
  `execution_node`, `validation_node`, `reporting_node` instances in
  addition to the three agents — flagged explicitly.
- `WorkflowState` gained `validation_report` and `decided_at` fields.
- `scripts/run_workflow_cli.py`: wired to the real nodes; prints real file
  paths (cleaned CSV, report, script) instead of Phase 5's stub messages.
- `tests/integration/test_workflow.py` **rewritten** to use a real
  `FileDatasetRepository` against real temporary files instead of the
  Phase 5 `FakeDatasetRepository`.

### Fixed
- A real bug, found by generating and reading an actual script: `ScriptExporter`'s
  footer template had broken f-string escaping (doubled braces meant for
  `.format()`, in a block never passed through `.format()`) — the first
  generated script would have printed literal `{sys.argv[0]}` instead of a
  real path. Fixed and verified via a subprocess round-trip test comparing
  the script's real output byte-for-byte against `StrategyExecutor`'s
  in-process result.
- A real bug, found by generating and reading an actual report: every
  executive report had a blank Summary section, because the Jinja2 template
  referenced a top-level `validation_notes` variable that was never passed
  (the real notes lived in `validation.notes`). Fixed with a regression test.
- A real test-fixture defect, found while rewriting the integration test
  (before it ran against real logic): the Phase 5 `FakeDatasetRepository`'s
  no-op `save()` and path-ignoring `load()` would have made `ValidationNode`
  silently validate the original data against itself, regardless of what
  was actually cleaned.

### Verified
- 197 tests passing (27 new), 92.56% coverage, 0 mypy issues across 76
  source files.
- A real end-to-end CLI run produces a real cleaned CSV, a fully-populated
  executive report, a runnable reproducible script, and an 8-event audit
  trail — all inspected directly on disk and in SQLite.

### Notes
- As of this phase, nothing in the core LangGraph pipeline is a stub or
  placeholder — every node does real work. Everything remaining is
  additive (UI, more tests, deployment, documentation), not filling in
  missing core logic.
- Phase 9 (Dashboard Development) will not begin until this Phase 8
  document and code are approved.

## [Phase 7] - Explainability & Decision Support

### Added
- `src/autoclean/infrastructure/llm/ollama_llm_client.py`: `OllamaLLMClient`,
  the real `ILLMClient` implementation via `langchain-ollama`'s `ChatOllama`,
  with a grounding-rule system prompt and an injectable `chat_model`
  parameter for testing without a live Ollama server.
- `src/autoclean/infrastructure/llm/fallback_llm_client.py`:
  `FallbackLLMClient` — new Decorator pattern, falls back to a secondary
  `ILLMClient` on any primary failure, visibly disclosing the fallback.
- `src/autoclean/infrastructure/llm/explanation_consistency_checker.py`:
  flags score-like numbers in any explanation that don't match a real
  computed score — the concrete implementation of Phase 1's Risk table
  mitigation on numeric consistency checking.
- 18 new tests across 3 new test files.
- `docs/phase_deliverables/Phase7_Explainability_and_Decision_Support.md`.

### Changed
- `ExplainRecommendationUseCase.execute()` now returns
  `(explanation_text, consistency_warnings)` instead of a bare string —
  flagged explicitly; `DecisionReportingAgent` absorbed the change
  internally, no other caller needed updates.
- `WorkflowState` gained `explanation_consistency_warnings: list[str]`.
- `scripts/run_workflow_cli.py`: now wired to
  `FallbackLLMClient(primary=OllamaLLMClient(), fallback=TemplateLLMClient())`;
  prints consistency warnings to the terminal if any are raised.

### Fixed
- A real false-positive bug, found by running the CLI: the consistency
  checker flagged the literal `"0.0"` in `TemplateLLMClient`'s own
  boilerplate range-descriptor text (`"Scores (0.0-1.0, higher is
  better...)"`) as a possibly-fabricated number. Fixed by excluding
  numbers immediately adjacent to a hyphen joining them to another number,
  with a regression test using the exact triggering text.
- 13 pre-existing mypy issues in Phase 4/6 code, surfaced by a newer
  `pandas-stubs`/mypy combination after a dev-environment reset (bare
  `np.ndarray`/`pd.Series` generics, a stale `type: ignore`, a stricter
  `.loc[]` indexing check) — unrelated to Phase 7's own new code, fixed
  before starting Phase 7 work to avoid building on a cracked foundation.

### Notes
- **Honest limitation**: this development sandbox has no Ollama installed
  and cannot practically run one. `OllamaLLMClient`'s prompt-construction
  logic was verified via an injected fake chat model; a live round-trip to
  an actual Ollama server has NOT been verified by any Claude session on
  this project. The user must verify this themselves (`ollama serve` +
  `ollama pull llama3.1:8b`, then run the CLI and read the real output).
- Every CLI run during this phase's development genuinely exercised the
  `FallbackLLMClient`'s fallback path (since Ollama isn't running in this
  sandbox) — real, verified evidence the fallback mechanism itself works.
- `TemplateLLMClient` is no longer the default but remains live, load-bearing
  code (the fallback target), not dead code.
- The dev-environment reset that occurred before this phase is documented
  at the top of `PROJECT_MEMORY.md` — always keep the latest delivered zip
  as the actual source of truth for this repository.
- Phase 8 (Cleaning Execution & Validation) will not begin until this
  Phase 7 document and code are approved.

## [Phase 6] - Strategy Optimization Engine

### Added
- `src/autoclean/infrastructure/data_processing/strategy_executor.py`:
  `StrategyExecutor`, deterministically applies a `CleaningStrategy`'s steps
  to real data (impute, clip, remove, dedupe, coerce dtype).
- `src/autoclean/infrastructure/metrics/`: 6 real metric modules
  (`quality_metrics.py`, `cost_metrics.py`, `information_preservation.py`,
  `statistical_validity.py`, `fairness_metrics.py`, `downstream_ml_metrics.py`),
  `em_quality_estimator.py` (paper Eqs. 2–6, adapted to per-strategy
  confidence via strategies-as-methods / rows-as-samples), and
  `real_metrics_engine.py` (`RealMetricsEngine`, the batch orchestrator).
- `src/autoclean/infrastructure/objective_weights_loader.py`:
  `load_objective_weights()`, with graceful fallback to uniform weights on
  a missing/malformed config file.
- 66 new tests across 7 new test files covering every new module
  individually plus the full `RealMetricsEngine` orchestration.
- `docs/phase_deliverables/Phase6_Strategy_Optimization_Engine.md`.

### Changed
- **`IMetricsEngine` port revised** from `score(strategy, profile)` to
  `score_all(strategies, df, profile) -> dict[str, EvaluationScore]` —
  flagged explicitly (same transparency convention as Phase 4's
  `infrastructure/data_processing/` addendum). Structurally necessary: the
  EM estimator needs the whole batch of strategies at once, and 4 of 6
  objectives need the actual data, not just a profile summary.
  `PlaceholderMetricsEngine` updated trivially (loop wrapper); its own
  per-strategy `score()` method is unchanged and still used directly by
  some tests.
- `EvaluateStrategiesUseCase.execute()` now also takes the raw `DataFrame`.
- `EvaluationAgent` now also depends on `IDatasetRepository` (reloads the
  dataset from `dataset_path`).
- `config/objective_weights.yaml` finalized with real, documented
  justification (was placeholder since Phase 3).
- `scripts/run_workflow_cli.py`: wired to `RealMetricsEngine`, loads
  weights via the new YAML loader, and now persists every strategy's score
  to SQLite (see Fixed, below).
- `template_llm_client.py`: updated boilerplate text that had gone stale
  after Phase 6 made 4 of 6 objectives real (previously said "placeholder
  values pending Phase 6").

### Fixed
- A real bug, found by actually running `scripts/run_workflow_cli.py`:
  `numpy.float64` values in `EvaluationScore` fields crashed LangGraph's
  msgpack-based checkpoint serializer. Fixed with explicit `float()` casts
  at every metric function's return point, plus a defensive cast layer in
  `RealMetricsEngine`, plus a `type(value) is float` regression test in
  every new metrics test file.
- A real bug, found by directly querying the database after a CLI run:
  `strategy_scores` was never populated in SQLite — `RealMetricsEngine`
  computed real scores, but nothing called `repository.save_strategy_score()`.
  Fixed in `run_workflow_cli.py`.

### Verified
- 152 tests passing (up from 89), 91.62% coverage, 0 mypy issues across 67
  source files.
- Directional correctness (not just "it ran"): Conservative scores higher
  on information preservation than Aggressive; EM confidence is higher for
  strategies that agree with each other than for a deliberate outlier
  (hand-constructed agreement pattern); a synthetic, near-separable
  classification task scores well above chance on the downstream-ML objective.
- A real CLI run persists 3 real, differentiated strategy scores to SQLite,
  confirmed via direct SQL query.

### Notes
- Fairness and downstream-ML objectives require a "sensitive"/"target"
  column; both auto-select via a documented heuristic pending Phase 9's UI
  for explicit user selection, and both fall back to a neutral `0.5` (not a
  fabricated number) when there isn't enough data to test meaningfully.
- The paper's Eq. 8 (DP refinement) remains undecided/not built — still an
  open item, unchanged this phase.
- Phase 7 (Explainability & Decision Support) will not begin until this
  Phase 6 document and code are approved.

## [Phase 5] - Multi-Agent Implementation

### Added
- `src/autoclean/application/ports/`: `IMetricsEngine`, `ILLMClient`,
  `IExperimentRepository`, `IDatasetRepository` (ABCs).
- `src/autoclean/application/use_cases/`: `ProfileDatasetUseCase`,
  `GenerateStrategiesUseCase`, `EvaluateStrategiesUseCase`,
  `ExplainRecommendationUseCase`, `ApproveStrategyUseCase`.
- `src/autoclean/infrastructure/persistence/sqlite/experiment_repository_impl.py`:
  `SQLiteExperimentRepository`, a full `IExperimentRepository` implementation.
- `src/autoclean/infrastructure/persistence/file_dataset_repository.py`:
  `FileDatasetRepository` (real csv/xlsx/parquet I/O).
- `src/autoclean/infrastructure/metrics/placeholder_metrics_engine.py` and
  `src/autoclean/infrastructure/llm/template_llm_client.py`: explicitly
  **temporary** `IMetricsEngine`/`ILLMClient` implementations, honestly
  labeled, to be replaced in Phase 6/7 respectively.
- `src/autoclean/agents/`: `AnalysisAgent`, `EvaluationAgent`,
  `DecisionReportingAgent`.
- `src/autoclean/orchestration/workflow_state.py`, `graph_builder.py`, and
  `nodes/` (`human_approval_node.py` — the real interrupt point;
  `execution_node.py`, `validation_node.py`, `reporting_node.py` — Phase 8
  stubs).
- `scripts/run_workflow_cli.py`: interactive, real, end-to-end demo entry point.
- `tests/fakes.py` and 6 new test files (unit + integration): 34 new tests.
- `docs/phase_deliverables/Phase5_Multi_Agent_Implementation.md`.

### Fixed
- A real bug, found by actually running `scripts/run_workflow_cli.py` and
  inspecting the resulting database: only human-decision audit events were
  reaching SQLite; each agent/node's own audit entries were staying in
  `WorkflowState` and never being persisted. Fixed with
  `_persist_new_audit_entries()` in the CLI script.
- 2 pre-existing mypy issues in `src/autoclean/infrastructure/logging_config.py`
  (Phase 3), found while running mypy across the full `src/` tree for the
  first time.

### Verified
- The LangGraph workflow genuinely pauses before human approval (checked via
  `graph.get_state(config).next`), not just claimed to.
- Rejecting a recommendation advances to a genuinely different next-ranked
  strategy (checked via assertion); rejecting every candidate ends the graph
  gracefully with a clear `error` field, not a crash.
- `EvaluationAgent`'s full dependency chain has zero LLM-typed parameters,
  confirmed via `inspect.signature()`.
- 89 tests passing, 91.31% coverage, 0 mypy issues across 57 source files.

### Notes
- `PlaceholderMetricsEngine` and `TemplateLLMClient` are deliberately
  temporary; both implement real ports, so Phase 6/7 will swap them without
  touching any use case or agent code.
- `execution_node`/`validation_node`/`reporting_node` do not yet perform any
  real data transformation, validation, or report generation — that is
  Phase 8 scope.
- Phase 6 (Strategy Optimization Engine) will not begin until this Phase 5
  document and code are approved.

## [Revision] LLM Provider Changed: Anthropic → Ollama

Applied after Phase 4 approval, amending a Phase 3 decision.

### Changed
- `src/autoclean/config/settings.py`: `llm_provider` default changed from
  `"anthropic"` to `"ollama"`; `llm_model` default changed from
  `"claude-sonnet-4-6"` to `"llama3.1:8b"`; added `llm_base_url` (default
  `http://localhost:11434`); `llm_api_key` is now optional/unused by the
  default provider; `llm_timeout_seconds` default raised from 30 to 60
  (local inference is typically slower than a hosted API).
- `requirements.txt`: replaced `anthropic~=0.34.0` with
  `langchain-ollama~=0.2.0`, so the future `ILLMClientImpl` (Phase 7) can use
  `ChatOllama` directly with the `langchain-core` message types already used
  for LangGraph orchestration.
- `docker-compose.yml`: revised from a single-service to a two-service
  deployment (`autoclean-app` + `ollama`), with a new `ollama-models` named
  volume. This is a scope revision to the Phase 2 Deployment Diagram,
  explicitly flagged in `Phase3_Environment_Setup.md` Section 6a.
- `.env.example`: removed the API-key setup step; documented
  `AUTOCLEAN_LLM_BASE_URL` and the `ollama pull llama3.1:8b` prerequisite.
- `scripts/verify_environment.py`: swapped the `anthropic` dependency check
  for `langchain_ollama`; added a new **non-fatal** Ollama-reachability
  check (warning, not a hard failure, since the LLM is not required until
  Phase 7's Decision & Reporting Agent exists).
- `README.md`: updated setup instructions accordingly.
- `docs/phase_deliverables/Phase3_Environment_Setup.md`: added a Revision Log
  and a new Section 6a documenting the theory, design decision, alternatives
  considered, and justification for this change, while leaving the original
  Section 6 (Anthropic decision) intact for audit-trail purposes.
- `PROJECT_MEMORY.md` fully rewritten to reflect the revised default
  provider throughout.

### Rationale
User requested avoiding a paid hosted LLM API for this academic project.
Ollama (self-hosted, free, no per-token billing) was substituted as the
default behind the existing `ILLMClient` Adapter-pattern port (Phase 2
§12) -- a change the port was specifically designed to absorb cheaply. No
agent code was affected, since the Decision & Reporting Agent (the only
component that would call `ILLMClient`) has not yet been implemented
(remains Phase 7 work).

### Notes
- All 50 existing Phase 4 unit tests re-verified passing after this change
  (none exercised the LLM client, which doesn't exist yet).

## [Phase 4] - Core Data Processing

### Added
- Domain layer entities (`src/autoclean/domain/`): `Dataset`, `DatasetProfile`,
  `DataIssue`, `IssueType`, `CleaningStrategy`, `CleaningStep`,
  `CleaningOperation`, `EvaluationScore`, `Experiment`, `ExperimentStatus`,
  `Decision`, `DecisionType`, `AuditEvent`, and the `ObjectiveWeights` value
  object -- all pure Python `dataclasses`, self-validating in `__post_init__`,
  zero framework dependencies.
- `src/autoclean/infrastructure/data_processing/` (new package; see "Changed"
  below): `DatasetProfiler` (IQR-based outlier detection, dtype-inconsistency
  heuristic, numeric/categorical column partitioning), `IssueDetector`
  (Phase 1 FR-2: missing values, duplicate rows, outliers, inconsistent
  dtypes), `StrategyGenerator` (Phase 1 FR-3: Baseline / Conservative /
  Aggressive candidate strategies, at least 2 guaranteed).
- `src/autoclean/infrastructure/persistence/sqlite/schema.sql`: full DDL for
  all 7 tables from the Phase 2 ERD, idempotent (`CREATE TABLE IF NOT
  EXISTS`), foreign keys + cascading deletes enabled.
- `src/autoclean/infrastructure/persistence/sqlite/db_session.py`: connection
  bootstrap (`get_connection`, `apply_schema`, `initialize_database`) using
  the standard library `sqlite3` module.
- `tests/conftest.py`: shared Pytest fixtures (`messy_dataframe`,
  `clean_dataframe`).
- 50 unit tests across `tests/unit/domain/test_entities.py` and
  `tests/unit/infrastructure/{test_profiler,test_issue_detector,
  test_strategy_generator,test_db_session}.py`. 97.3% line coverage on all
  Phase 4 code, verified against the 80% threshold set in `pyproject.toml`
  (Phase 3); `mypy` reports zero issues across all 18 new source files.
- `docs/phase_deliverables/Phase4_Core_Data_Processing.md`: full phase
  documentation (theory, design decisions, alternatives, justification for
  entity design, IQR outlier detection, three-tier strategy generation, and
  the SQLite schema implementation), a Phase 4 PAPER-vs-ORIGINAL mapping
  table, and a review checklist.

### Changed
- **Design addendum to Phase 2's folder structure**: added
  `src/autoclean/infrastructure/data_processing/`, not present in the
  originally approved Phase 2 folder structure. Domain must stay
  framework-free (no Pandas), and `infrastructure/metrics/` was explicitly
  scoped in Phase 2 to the Evaluation Agent's six objectives, not issue
  *detection* -- so a dedicated package was added rather than overloading
  either existing location. Flagged explicitly for user approval (see
  Phase4_Core_Data_Processing.md Section 6 and PROJECT_MEMORY.md Open Items).
- Fixed two `DeprecationWarning`s (`datetime.utcnow()` → timezone-aware
  `datetime.now(UTC)`) and one Pandas future-deprecation warning
  (`select_dtypes(include="object")` → `include=["object", "string"]`)
  identified while running the new test suite.
- `PROJECT_MEMORY.md` fully rewritten (not appended) to reflect the complete
  current project state through Phase 4, including per-file implementation
  status across all four Clean Architecture layers.

### Decisions Recorded
- Full SQLAlchemy-based Repository-pattern classes implementing the
  Application layer's port interfaces are deliberately deferred to Phase 5,
  since those port ABCs don't exist until Phase 5; Phase 4 stops at raw
  `sqlite3` connection bootstrap + schema application.
- Outlier detection uses the IQR rule (not z-score or Isolation Forest) at
  the profiling stage, chosen for distribution-agnostic robustness and
  human-checkable, report-ready bounds.
- Candidate strategy generation uses a small, fixed, named set (Baseline /
  Conservative / Aggressive) rather than combinatorial enumeration, to keep
  the Streamlit comparison view (Phase 9) human-reviewable.

### Notes
- No agent, LangGraph, evaluation-scoring, or LLM logic was implemented in
  this phase, per the project specification's phase-gating rule.
- Phase 5 (Multi-Agent Implementation) will not begin until this Phase 4
  document and code are approved.

## [Phase 3] - Environment Setup

### Added
- Full `src/autoclean/` package structure scaffolded per the Phase 2 folder design,
  with every package documented via an `__init__.py` docstring stating its purpose
  and the phase that will populate it.
- `src/autoclean/config/settings.py`: `pydantic-settings`-based configuration schema
  (paths, database, LLM client, EM parameters, Streamlit limits), externalizing all
  configuration per NFR-6.
- `src/autoclean/config/objective_weights.yaml`: placeholder six-objective weight
  configuration (not yet empirically/theoretically justified; deferred to Phase 6).
- `src/autoclean/infrastructure/logging_config.py`: structured JSON logging via the
  standard library `logging` module, per NFR-4.
- `scripts/verify_environment.py`: environment verification script (Python version,
  dependency importability, settings load, logging configuration, required
  directories) -- the only executable logic in this phase, deliberately scoped to
  verification only, no business logic.
- `requirements.txt` / `requirements-dev.txt`: pinned runtime and development
  dependencies (pip-based dependency management, chosen over Poetry/pip-tools).
- `pyproject.toml`: project metadata and tool configuration only (Black, Ruff,
  mypy strict mode, Pytest, coverage threshold 80%).
- `Dockerfile` (multi-stage: builder + slim non-root runtime, healthcheck) and
  `docker-compose.yml` (named volumes for `data/` and `logs/`), `.dockerignore`.
- `.env.example`, `.gitignore`, `.pre-commit-config.yaml`, `Makefile`, `README.md`.
- `docs/phase_deliverables/Phase3_Environment_Setup.md`: full phase documentation
  covering dependency strategy, Python version/layout, configuration management,
  logging strategy, the LLM provider decision, Docker strategy, code quality
  tooling, and a Phase 3 PAPER-vs-ORIGINAL mapping table.

### Changed
- `PROJECT_MEMORY.md` fully rewritten (not appended) to reflect the complete
  current project state through Phase 3, including per-layer implementation
  status (scaffolded vs. implemented) and an updated open-items list.

### Decisions Recorded
- Resolved Phase 2's open LLM-provider item: **Anthropic Claude** (via the
  `anthropic` SDK, default model `claude-sonnet-4-6`) is the default
  `ILLMClient` implementation, kept swappable via the existing Adapter-pattern
  port so this is a default, not a lock-in.
- Dependency management: `requirements.txt` + `requirements-dev.txt` (pip),
  not Poetry or pip-tools, for onboarding simplicity at this project's scale;
  pip-tools noted as a possible Phase 11 upgrade for fully pinned lockfiles.
- `src/` package layout adopted over a flat layout, to avoid accidental
  working-directory imports masking real packaging issues later.

### Notes
- No agent, evaluation, or cleaning business logic was implemented in this
  phase, per the project specification's phase-gating rule.
- Phase 4 (Core Data Processing) will not begin until this Phase 3 document
  and scaffold are approved.

## [Phase 2] - System Design

### Added
- `Phase2_System_Design.md`: complete system design document, covering:
  - Overall architecture (4-layer Clean Architecture + LangGraph orchestration layer)
  - Clean Architecture layer breakdown and responsibilities table
  - Concrete folder structure mapped to architecture and to Phase 1 functional requirements
  - LangGraph workflow: 7 nodes, 1 human-approval interrupt, 2 loop-back edges
  - Agent communication model (blackboard pattern via shared `WorkflowState` only)
  - Full shared `WorkflowState` schema, including nested entity structures
  - Normalized 6-table SQLite schema (ERD) for audit trail and experiment history
  - UML class diagram, sequence diagram, component diagram, deployment diagram (Mermaid)
  - 9 named design patterns with justification (Repository, DI, Strategy, Factory,
    Adapter, Template Method, State, Facade, Interrupt/Checkpoint)
  - Full technology justification table (chosen vs. alternatives, with reasons)
  - Design-level PAPER vs. ORIGINAL attribution, extending the Phase 1 tables
  - Review checklist for approval before Phase 3

### Changed
- `PROJECT_MEMORY.md` fully rewritten (not just appended) to reflect the complete
  current project state through Phase 2: architecture, agent responsibilities,
  folder structure, database schema, design patterns, technology stack, and an
  explicit "open items deferred to later phases" list.

### Decisions Recorded
- The IEEE paper's hybrid greedy+DP optimization algorithm (Eq. 8) will NOT be the
  primary strategy-ranking mechanism in AutoClean AI+; a weighted decision matrix
  (descended from the paper's weighted-gain metric, Eq. 7) is used instead, because
  the action space (a handful of whole strategies for one dataset) does not require
  combinatorial budget-constrained assignment across many sub-tasks. Eq. 8 is
  deferred to Phase 6 as an optional future feature rather than dropped silently.

### Notes
- No source code was written in this phase, per the project specification.
- Phase 3 (Environment Setup) will not begin until this Phase 2 document is approved.

## [Phase 1] - Research & Requirements

### Added
- `Phase1_Research_and_Requirements.md`: complete research and requirements document,
  covering:
  - Problem statement, research motivation, background theory, and literature review
  - Full technical summary of the IEEE source paper (problem formulation, EM algorithm,
    hybrid greedy+DP optimization, complexity analysis, experimental setup/results, and
    the paper's own stated limitations and future work)
  - Research gap explicitly grounded in the paper's stated future-work call for
    explainability and human-in-the-loop approaches
  - Project objectives, in-scope/out-of-scope boundaries
  - Feature attribution tables: features implemented from the IEEE paper vs. original
    contributions introduced in AutoClean AI+
  - 15 functional requirements, 11 non-functional requirements
  - Stakeholders, 6 use cases, assumptions, constraints, risks (with mitigations), and
    success criteria
- Updated `PROJECT_MEMORY.md` with a Phase Status Log and a persistent reference of key
  facts/equations from the IEEE paper, to keep later phases consistent.
- This `CHANGELOG.md` file, established to track progress phase by phase going forward.

### Notes
- No source code was written in this phase, per the project specification.
- Phase 2 (System Design) will not begin until this Phase 1 document is approved.

## [Phase 10] - Final Release & Audit Verification
- Added openpyxl dependency for Excel parsing.
- Fixed continuous target handling in downstream ML metrics.
- Verified Ollama llama3.2 integration and reproduction parity.

