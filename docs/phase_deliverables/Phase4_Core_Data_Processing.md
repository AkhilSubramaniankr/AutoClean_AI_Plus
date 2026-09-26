# AutoClean AI+: Phase 4 — Core Data Processing

**Project:** AutoClean AI+: A Multi-Agent Explainable Decision Support System for Multi-Objective Data Cleaning Strategy Optimization
**Phase:** 4 of 12 — Core Data Processing
**Status:** Complete — for approval
**Depends on:** Phase 1, 2, 3 (all approved)

This phase implements the **Domain layer entities** and the **deterministic dataset profiling / issue detection / candidate strategy generation engine** that the Analysis Agent (Phase 5) will wrap. All code is 100% deterministic Python (Pandas/NumPy) — no LLM involvement anywhere in this phase, per NFR-1. Agent wrappers, LangGraph wiring, and full repository implementations remain out of scope until Phase 5.

Tagging convention carried forward: 🟦 **[PAPER]**, 🟩 **[ORIGINAL]**.

---

## 1. Scope of This Phase

| In Scope | Out of Scope (later phases) |
|---|---|
| Domain entities: `Dataset`, `DatasetProfile`, `DataIssue`, `CleaningStrategy`, `CleaningStep`, `EvaluationScore`, `Experiment`, `Decision`, `AuditEvent`, `ObjectiveWeights` | Application-layer use cases / port interfaces (Phase 5) |
| Deterministic `DatasetProfiler` (Pandas/NumPy) | LangGraph agent wrappers (Phase 5) |
| Deterministic `IssueDetector` (missing values, duplicates, outliers, dtype inconsistencies — Phase 1 FR-2) | Multi-objective scoring / EM confidence estimation (Phase 6) |
| Deterministic `StrategyGenerator` (Phase 1 FR-3: ≥2 candidate strategies) | LLM explanation generation (Phase 7) |
| SQLite schema DDL + connection bootstrap | Full repository classes implementing Application ports (Phase 5) |
| Unit tests for all of the above (50 tests, 97% coverage on new code) | Integration tests across the full workflow (Phase 10) |

---

## 2. Domain Layer: Entity Implementation

### Theory
Domain entities in Clean Architecture must be framework-free — no Pandas import is permitted anywhere in `src/autoclean/domain/`. This is not stylistic; it is what makes the Domain layer testable with zero I/O and independently reusable if, hypothetically, the Infrastructure layer were replaced entirely (e.g., swapping Pandas for Polars).

### Design Decisions
- All entities are implemented as `@dataclass`, most `frozen=True` (`DatasetProfile`, `Dataset`, `DataIssue`, `CleaningStep`, `CleaningStrategy`, `EvaluationScore`, `Decision`, `AuditEvent`) except `Experiment`, which is deliberately mutable because its `status` and `candidate_strategies` legitimately change as the LangGraph workflow progresses (mirroring the mutability of `WorkflowState` itself, Phase 2 §6).
- Every entity validates its own invariants in `__post_init__` (e.g., `severity` must be in `[0.0, 1.0]`; `ObjectiveWeights` must sum to `1.0`; `Experiment.mark_completed` rejects a strategy ID that was never actually a candidate). This makes invalid states unrepresentable rather than merely undocumented.
- `CleaningStrategy`/`CleaningStep` implement `to_dict()`/`from_dict()` for direct JSON round-tripping into the `strategy_definition_json` SQLite column (Phase 2 §7) — verified by an explicit round-trip unit test.
- `EvaluationScore._OBJECTIVE_FIELDS` is a `ClassVar`, not a dataclass field, keeping the six-objective enumeration internally DRY (used by validation) without polluting `__init__`/`repr`/equality.

### Alternatives Considered
- **Pydantic `BaseModel` instead of `dataclass`** for entities: rejected — Pydantic is already used for `Settings` (Phase 3, an Infrastructure/config concern); using it for Domain entities too would implicitly couple the Domain layer's validation behavior to Pydantic's runtime, when stdlib `dataclasses` + manual `__post_init__` validation gives the same invariant-enforcement with zero framework dependency, keeping the Domain layer honestly dependency-free rather than "framework-free except for the one everywhere."
- **`TypedDict` for entities**: rejected — no runtime validation at all, which would silently reopen the "invalid states are representable" problem these dataclasses are specifically designed to close.
- **A generic `Dict[str, float]` for `EvaluationScore`** (instead of six named fields): rejected in Phase 2 already (§6) and reaffirmed here at implementation time — the six-objective contract must be a type error to violate, not a silent missing key.

### Justification
Every validation rule implemented here traces to a specific Phase 1 requirement or Phase 2 design decision (cited in each module's docstring), so an academic reviewer can check any single `__post_init__` rule against the requirements document that motivated it.

---

## 3. Dataset Profiling

### Theory
Profiling (row/column counts, missing-value rate, duplicate count, per-column dtype and cardinality) is the prerequisite input to issue detection. Outlier detection specifically uses the **IQR rule**: a value is flagged if it falls outside `[Q1 - 1.5×IQR, Q3 + 1.5×IQR]`, where `IQR = Q3 - Q1`. This is the same interquartile-spread-based approach used ubiquitously in exploratory data analysis (e.g., box-plot whiskers), chosen for its simplicity, distribution-agnostic robustness (unlike z-score, which assumes approximate normality), and direct interpretability in the executive report (Phase 8).

### Design Decisions
- `DatasetProfiler.profile()` is stateless and never mutates its input `DataFrame` — verified implicitly by every test using the same fixture across `profile()` and `detect()` calls without re-copying.
- Column categorization (numeric vs. categorical) uses a documented heuristic: a numeric column with ≤20 distinct values *and* a distinct-value ratio ≤5% is reclassified as categorical (e.g., a binary flag column encoded as `int64`). This heuristic is intentionally simple and explicitly flagged in the code as revisitable if Phase 6 evaluation reveals misclassification on a real dataset.
- Dtype-inconsistency detection flags an `object`/`string` column as "should probably be numeric" when 50–99% (exclusive of 100%, which would just be a numeric column stored as text uniformly and is arguably a formatting choice, not an inconsistency) of its non-null values parse as numbers via `pd.to_numeric(errors="coerce")`.

### Alternatives Considered
- **Z-score outlier detection** (`|z| > 3`): rejected as the profiling-stage default — assumes approximate normality, which is not guaranteed for arbitrary uploaded datasets (Phase 1 Assumption: datasets are user-uploaded, distribution unknown); IQR makes no such assumption.
- **Isolation Forest / other ML-based outlier detection** (Scikit-learn): rejected for the profiling stage specifically — more powerful for multivariate outliers, but slower, less interpretable in a report ("this value is outside the IQR bounds" is immediately explainable to a non-technical stakeholder; "this row has an anomaly score of -0.31" is not), and disproportionate for a profiling step whose job is a fast first-pass summary, not final strategy execution. Scikit-learn-based, more sophisticated outlier/anomaly detection remains available as a *candidate strategy operation* in later phases if warranted, distinct from the profiling-stage default.
- **Fixed missing-value/outlier thresholds instead of computed statistics**: rejected — hard-coded thresholds (e.g., "flag any column with >10% missing") would not adapt across datasets of very different characteristics, undermining the profiler's reusability across arbitrary uploads (Phase 1 §8 In Scope).

### Justification
IQR-based detection is standard, distribution-agnostic, fast (`O(n log n)` per column via quantile computation), and — critically for this project's explainability mandate (Phase 1 §10 originality) — produces a human-checkable bound (`[lower, upper]`) that appears verbatim in each `DataIssue.description`, giving the Decision & Reporting Agent (Phase 7) concrete, non-fabricated numbers to reference in its explanation.

---

## 4. Issue Detection and Candidate Strategy Generation

### Theory
Issue detection converts profiling statistics into a list of discrete, actionable `DataIssue` objects — one issue type per Phase 1 FR-2 category (missing values, duplicates, outliers, dtype inconsistency). Strategy generation then converts that issue list into multiple whole-dataset `CleaningStrategy` candidates for the Evaluation Agent (Phase 6) to score, satisfying FR-3 ("at least two candidate cleaning strategies per detected issue profile").

### Design Decisions
`StrategyGenerator` always produces a fixed, named set of **up to three** strategies:
1. **Baseline** (always generated): fixes only dtype issues and removes exact duplicates. Never imputes or touches outliers. Cheapest, lowest-intervention option — the closest analogue to the paper's own low-cost baseline before its greedy-upgrade pass 🟦[PAPER-motivated].
2. **Conservative** (generated if there's anything beyond dtype/duplicates to address): imputes missing values (median/mode) and clips outliers to IQR bounds. Preserves row count and total information volume.
3. **Aggressive** (generated only if missing values or outliers are present): drops rows with missing values and removes (rather than clips) outlier rows. Maximizes remaining-data purity at the cost of row count.

If issues are empty, both Conservative and Aggressive collapse to `None` (nothing to add beyond baseline), and an explicit, documented "No-op" strategy is generated as the second FR-3-mandated candidate rather than silently returning only one strategy.

### Alternatives Considered
- **Combinatorial strategy generation** (enumerate every subset/ordering of applicable operations): rejected — for a dataset with even a handful of flagged columns, this explodes combinatorially and produces dozens of near-duplicate strategies that would overwhelm a human reviewer in the Streamlit comparison view (Phase 9), directly working against this project's explainability goal (a human should be able to meaningfully compare 2–3 named strategies, not choose among 40 combinatorially-generated variants).
- **A single "best guess" strategy with no alternatives**: rejected outright — violates FR-3 and eliminates the multi-objective *comparison* that is this project's entire premise (Phase 1 §1 Problem Statement).
- **User-defined custom strategies at generation time**: deferred, not rejected — a reasonable future extension (a user manually composing their own `CleaningStrategy` via the Streamlit UI in Phase 9), but out of scope for the deterministic generation logic implemented in this phase.

### Justification
Three clearly named, individually explainable strategies (Baseline / Conservative / Aggressive) give the Evaluation Agent (Phase 6) genuinely different points in the quality/cost/information-preservation trade-off space to score against each other — which is the actual point of a multi-objective comparison — while staying small enough that Phase 7's explanation and Phase 9's dashboard can present all candidates to a human reviewer without overload.

---

## 5. SQLite Schema Implementation

### Design Decisions
`schema.sql` implements the Phase 2 §7 ERD verbatim: 7 tables (`experiments`, `dataset_profiles`, `candidate_strategies`, `strategy_scores`, `decisions`, `audit_log`, `reports`), all `CREATE TABLE IF NOT EXISTS` (idempotent — safe to apply on every app startup), with foreign keys enabled (`PRAGMA foreign_keys = ON`) and `ON DELETE CASCADE` so deleting an experiment cleanly removes its dependent rows without orphaning data.

`db_session.py` deliberately stops at connection bootstrap + schema application using the **standard library `sqlite3`** module directly, *not* the SQLAlchemy ORM already listed in `requirements.txt` (Phase 3). Full repository classes (which would use SQLAlchemy models implementing the `IExperimentRepository` etc. ports) are explicitly deferred to Phase 5, because those port interfaces don't exist yet — the Phase 2 folder structure scoped `application/ports/` to "populated starting Phase 5," and building repository *implementations* of ports that don't exist yet would invert the intended build order.

### Alternatives Considered
- **Building full SQLAlchemy ORM models and repositories now**: rejected for this phase specifically — would require either (a) inventing port interfaces ahead of their planned phase, undermining the phase-gated build order the user has explicitly requested, or (b) building repositories with no interface to implement against, which isn't genuine Repository-pattern implementation, just early, ungrounded code.
- **Skipping schema implementation entirely until Phase 5**: rejected — Phase 3's `PROJECT_MEMORY.md` open items explicitly flagged "Actual SQLite schema.sql... targeted for Phase 4," and schema/connection bootstrap has no dependency on Application-layer ports, so there's no architectural reason to delay it.

### Justification
This is the narrowest possible persistence-layer slice that is both immediately useful (verified via 4 passing tests, including a real foreign-key-violation check) and does not front-run Phase 5's Repository-pattern work — schema and raw connection management are a data-processing concern; turning that into full Repository objects implementing typed ports is an application-orchestration concern, which is Phase 5's job.

---

## 6. Design Addendum to Phase 2: `infrastructure/data_processing/`

Phase 2's folder structure (§3) did not name a specific home for profiling/issue-detection/strategy-generation logic. Since the Domain layer must stay Pandas-free (§2 above) and `infrastructure/metrics/` was explicitly scoped in Phase 2 to the *Evaluation Agent's* six objectives (not issue *detection*), a new package — `src/autoclean/infrastructure/data_processing/` — was added in this phase to hold `profiler.py`, `issue_detector.py`, and `strategy_generator.py`.

This is flagged explicitly, the same way Phase 2 flagged its own deferral of the paper's Eq. 8 DP-refinement algorithm, so that a deviation from the originally-approved folder structure is visible and reviewable rather than silently introduced. `PROJECT_MEMORY.md` is updated accordingly (§10 below).

---

## 7. Testing Summary (NFR-7)

| Test file | Tests | What it covers |
|---|---|---|
| `tests/unit/domain/test_entities.py` | 28 | Every entity's validation rules, edge cases, and (for `CleaningStrategy`) JSON round-tripping |
| `tests/unit/infrastructure/test_profiler.py` | 5 | Clean vs. messy data, zero-column edge case, numeric/categorical partitioning, missing-value percentage math |
| `tests/unit/infrastructure/test_issue_detector.py` | 6 | All four issue types detected correctly, dataset-wide vs. per-column issues, zero-row edge case |
| `tests/unit/infrastructure/test_strategy_generator.py` | 7 | FR-3 compliance (≥2 strategies) on both messy and clean data, exactly one baseline, unique IDs, correct operations per strategy tier |
| `tests/unit/infrastructure/test_db_session.py` | 4 | Schema creates all 7 tables, idempotent re-application, foreign-key enforcement, parent-directory auto-creation |
| **Total** | **50** | **97.3% line coverage** on all Phase 4 code (`domain/`, `infrastructure/data_processing/`, `infrastructure/persistence/`), verified against the `pyproject.toml` 80% threshold set in Phase 3 |

All 50 tests pass with zero warnings (two `DeprecationWarning`s from `datetime.utcnow()` and one Pandas future-deprecation warning were identified during test runs and fixed in the implementation, not suppressed). `mypy` (strict-adjacent settings from Phase 3's `pyproject.toml`) reports zero issues across all 18 new source files.

---

## 8. IEEE Paper Features vs. Original Contributions — Phase 4 Mapping

| Implementation Artifact | 🟦 PAPER-derived | 🟩 ORIGINAL |
|---|---|---|
| `DatasetProfile` / profiling as the first pipeline stage | Conceptually the prerequisite to the paper's sub-task decomposition (a dataset must be characterized before work can be routed) | The specific profiling algorithm (Pandas-based summary statistics, IQR outlier counting, dtype-inconsistency heuristic) is entirely 🟩 — not specified in the paper |
| `DataIssue` as a discrete, typed unit of "what's wrong" | Loosely analogous to the paper's sub-task `T_j` concept (a unit of work to route) | The four fixed issue categories and their severity scoring are 🟩 |
| `StrategyGenerator`'s Baseline strategy | Directly analogous to the paper's low-cost baseline assignment before the greedy-upgrade pass | The specific "fix dtype + dedupe only" baseline definition is 🟩 |
| `StrategyGenerator`'s Conservative/Aggressive strategies | — | Entirely 🟩 — the paper never composes multi-step whole-dataset strategies; it routes individual sub-tasks to one of four fixed methods |
| SQLite schema (`schema.sql`) | — | Entirely 🟩 — no persistence/audit concern exists in the paper |
| `EvaluationScore` entity (six named fields) | Two of six fields (`data_quality_score`, `computational_cost_score`) are 🟦-motivated | Four of six fields are 🟩 (already noted in Phase 2 §14, now concretely implemented) |

---

## Review Checklist

- [ ] Domain entity design (dataclasses, validation-in-`__post_init__`, `Experiment` as the sole mutable entity) is approved
- [ ] IQR-based outlier detection (chosen over z-score/Isolation Forest for the profiling stage) is approved
- [ ] The three-tier strategy generation scheme (Baseline / Conservative / Aggressive) is approved as satisfying FR-3
- [ ] The `infrastructure/data_processing/` addendum to the Phase 2 folder structure (§6 above) is explicitly acknowledged and approved
- [ ] SQLite schema (7 tables, matching the Phase 2 ERD exactly) is approved
- [ ] The decision to defer full Repository-pattern implementations to Phase 5 (since ports don't exist yet) is approved
- [ ] Test coverage (50 tests, 97.3% on new code, mypy clean) is confirmed sufficient for this phase's scope
- [ ] No agent, LangGraph, evaluation-scoring, or LLM logic has been implemented in this phase (confirmed)

---

## Summary of Completed Work

Phase 4 has implemented and tested the Domain layer (9 entities/value objects, all validating their own invariants) and a deterministic, Pandas/NumPy-based data-processing engine (`DatasetProfiler`, `IssueDetector`, `StrategyGenerator`) satisfying Phase 1's FR-2 and FR-3, plus the SQLite schema and connection bootstrap matching Phase 2's ERD exactly. All code is covered by 50 passing unit tests (97.3% coverage on new code, zero mypy issues, zero warnings). One deliberate, explicitly flagged addendum to the Phase 2 folder structure was introduced (`infrastructure/data_processing/`) to give profiling/detection/generation logic a proper home without violating the Domain layer's zero-framework-dependency rule or overloading the `infrastructure/metrics/` package that Phase 2 scoped specifically to the Evaluation Agent's six objectives.

## Remaining Work
Phases 5–12, beginning with Phase 5 (Multi-Agent Implementation), pending your approval of this document.

## Recommended Next Step
Review the checklist above — particularly the `infrastructure/data_processing/` addendum (§6) and the three-tier strategy generation scheme (§4) — then approve or request revisions. Once approved, Phase 5 will implement the Application-layer use cases and port interfaces, the three LangGraph agent wrappers (Analysis, Evaluation, Decision & Reporting), the `WorkflowState` schema, and `graph_builder.py`, wiring the deterministic engine built in this phase into the actual multi-agent workflow designed in Phase 2.

## Git Commit Message
```
feat(phase-4): implement domain entities and deterministic data processing

- Implement Domain layer: Dataset, DatasetProfile, DataIssue, CleaningStrategy,
  CleaningStep, EvaluationScore, Experiment, Decision, AuditEvent entities,
  and the ObjectiveWeights value object -- all pure Python, self-validating
  in __post_init__, zero framework dependencies
- Add infrastructure/data_processing/ (design addendum to Phase 2 folder
  structure, explicitly flagged): DatasetProfiler (IQR-based outlier
  detection, dtype-inconsistency heuristic), IssueDetector (FR-2: missing
  values, duplicates, outliers, dtype issues), StrategyGenerator (FR-3:
  Baseline/Conservative/Aggressive candidate strategies, >=2 guaranteed)
- Implement SQLite schema.sql (matches Phase 2 ERD exactly, 7 tables,
  foreign keys + cascading deletes) and db_session.py connection bootstrap;
  full Repository-pattern implementations deferred to Phase 5 pending
  Application-layer port interfaces
- Add 50 unit tests across domain entities, profiler, issue detector,
  strategy generator, and db_session (97.3% coverage on new code, mypy
  clean, zero warnings)
- No agent, LangGraph, evaluation-scoring, or LLM logic in this phase
```
