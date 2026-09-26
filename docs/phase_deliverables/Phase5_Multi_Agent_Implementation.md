# AutoClean AI+: Phase 5 — Multi-Agent Implementation

**Project:** AutoClean AI+
**Phase:** 5 of 12 — Multi-Agent Implementation
**Status:** Complete — for approval
**Depends on:** Phases 1–4 (all approved)

This phase wires the Phase 4 deterministic engine into an actual, running LangGraph multi-agent workflow: three agents, a shared `WorkflowState`, and a working human-approval interrupt. Tagging convention carried forward: 🟦 **[PAPER]**, 🟩 **[ORIGINAL]**.

---

## 1. Scope and the Placeholder Strategy

Phase 5's job is narrow and specific: **prove the multi-agent architecture actually runs**, including the one behavior the whole project's originality claim rests on — the workflow genuinely pausing for a human decision, not just claiming to. It is explicitly *not* this phase's job to solve multi-objective evaluation (Phase 6) or produce real LLM explanations (Phase 7).

To make the graph runnable without front-running those phases, two deliberately temporary components were introduced:

| Component | What's real | What's placeholder | Replaced in |
|---|---|---|---|
| `PlaceholderMetricsEngine` | `data_quality_score`/`computational_cost_score` computed from real strategy/profile properties (step count, issue coverage, row-removal penalty) | Other 4 objectives fixed at neutral `0.5` | Phase 6 |
| `TemplateLLMClient` | Every number in the output is read from the real `EvaluationScore` | Prose is string-templated, not LLM-generated | Phase 7 |
| `execution_node`/`validation_node`/`reporting_node` | Graph shape and traversal are real | No actual data transformation, validation logic, or report generation | Phase 8 |

Both `PlaceholderMetricsEngine` and `TemplateLLMClient` implement the real `IMetricsEngine`/`ILLMClient` ports (Adapter pattern) — this is not a hack bolted on top of the architecture, it's the architecture doing exactly what it was designed for: Phase 6/7 will swap these implementations without touching any use case or agent code.

### Design Decision / Alternatives / Justification
**Alternative rejected:** build a "fake" graph with mocked nodes just to prove LangGraph wiring compiles, then discard it. Rejected because it would prove nothing about the real failure modes (state merging across the interrupt boundary, checkpoint serialization of Domain dataclasses, the rejection loop actually advancing to a *different* strategy) — exactly the risks worth catching now, before Phase 6/7 add real complexity on top.
**Alternative rejected:** skip the interrupt for now and add it in a later phase. Rejected — the interrupt is the single most load-bearing architectural claim in this entire project (Phase 1 §10, Phase 2 §1); deferring it would mean six more phases get built on an unverified foundation.

---

## 2. What Was Implemented

### Application Layer (ports + use cases)
- **Ports** (`application/ports/`): `IMetricsEngine`, `ILLMClient`, `IExperimentRepository`, `IDatasetRepository` — all ABCs, zero concrete dependencies.
- **Use cases** (`application/use_cases/`): `ProfileDatasetUseCase`, `GenerateStrategiesUseCase` (thin wrappers with no port dependency — the Phase 4 engine has no I/O to abstract), `EvaluateStrategiesUseCase` (depends on `IMetricsEngine` + `ObjectiveWeights`), `ExplainRecommendationUseCase` (the *only* use case depending on `ILLMClient`), `ApproveStrategyUseCase` (depends on `IExperimentRepository`, persists every decision + an audit event).

### Infrastructure Layer
- `SQLiteExperimentRepository` — full `IExperimentRepository` implementation against the Phase 4 schema: experiments, candidate strategies, scores, decisions, and audit trail, all with round-trip tests against a real (temporary) SQLite file.
- `FileDatasetRepository` — real CSV/XLSX/Parquet load/save via Pandas.
- `PlaceholderMetricsEngine`, `TemplateLLMClient` — see §1.

### Agents (`agents/`)
Three thin LangGraph node wrappers — `AnalysisAgent`, `EvaluationAgent`, `DecisionReportingAgent` — each translating `WorkflowState` ↔ use case calls only, no business logic of their own. `EvaluationAgent`'s constructor was inspected at runtime (`inspect.signature`) to confirm zero LLM-typed parameters anywhere in its dependency chain — the "LLM never computes" rule is enforced by the type signature itself, not a comment.

### Orchestration (`orchestration/`)
- `workflow_state.py` — the shared `TypedDict`, matching Phase 2 §6 exactly (scores stored as plain dicts via `EvaluationScore.as_dict()`, chosen deliberately for clean LangGraph checkpoint serialization over storing dataclass instances directly).
- `graph_builder.py` — builds and compiles the 7-node graph with `interrupt_before=["human_approval"]` and a `MemorySaver`/pluggable checkpointer, exposed as a single `build_graph()` Facade.
- `nodes/` — `human_approval_node` (the interrupt point; its own code does almost nothing, the pause is a compile-time setting) and three explicitly-stubbed Phase-8 nodes.

### Demo / Verification Tooling
`scripts/run_workflow_cli.py` — a real, interactive terminal entry point: loads a dataset, runs the graph to the interrupt, prompts for approve/reject in a loop, and persists the complete run (including every agent/node's audit events, not just the human decisions) to a real SQLite database.

---

## 3. Verification Performed (not just claimed)

| Check | Result |
|---|---|
| Full test suite (unit + integration) | **84 → 89 tests, all passing** (grew during the session as gaps were found and closed) |
| Coverage | **91.31%**, above the 80% threshold |
| mypy, full `src/` tree | **0 issues across 57 files** (found and fixed 2 pre-existing Phase 3 typing gaps in `logging_config.py` along the way) |
| Graph actually pauses before human approval | Verified via `graph.get_state(config).next == ("human_approval",)` |
| Rejection loop picks a genuinely different strategy | Verified via direct assertion (not just "no exception raised") |
| Reject-all-strategies edge case | Verified it ends with a clear `error` field, not a crash or hang |
| `EvaluationAgent` has no LLM dependency | Verified via `inspect.signature()`, not just code review |
| Real CLI run against a real messy CSV | Run twice; second run's output led to discovering and fixing a real bug (see §4) |
| SQLite audit trail is queryable and complete | Inspected directly via `sqlite3` after a real CLI run — 11 events, correctly ordered, correctly typed |

## 4. A Real Bug Found and Fixed During This Phase

The first CLI run revealed that only human-decision events were reaching the SQLite `audit_log` table — every agent/node's own audit entries (accumulated in `WorkflowState["audit_log_entries"]`) were staying in memory and never being persisted. This wasn't a hypothetical risk caught by inspection; it was found by actually running the tool and looking at the resulting database. Fixed by adding `_persist_new_audit_entries()` to the CLI script, which copies any new in-state audit entries into the repository after every `graph.invoke()` call. Re-verified: a full reject-then-approve run now persists all 11 events (profiling, scoring, both recommendations, both decisions, both approval-resumes, and the three stub nodes) in correct chronological order.

---

## 5. IEEE Paper Features vs. Original Contributions — Phase 5 Mapping

| Artifact | 🟦 PAPER-derived | 🟩 ORIGINAL |
|---|---|---|
| Blackboard-style `WorkflowState` communication | — | Entirely 🟩 — no orchestration concept in the paper |
| Human-approval interrupt, verified pausing | — | Entirely 🟩 — direct answer to the paper's own stated future-work gap |
| `PlaceholderMetricsEngine`'s quality heuristic (issue-coverage-based) | Loosely 🟦-motivated (more addressed issue surface ≈ higher paper-style `Q_u`) | The specific heuristic is 🟩 |
| Rejection loop re-presenting the next-ranked alternative | — | Entirely 🟩 |

---

## Review Checklist
- [ ] The placeholder strategy (§1) — what's real vs. temporary in `PlaceholderMetricsEngine`/`TemplateLLMClient` — is understood and approved
- [ ] All ports/use cases/agents/orchestration code is approved
- [ ] Verification results (§3) are sufficient to trust the interrupt mechanism going into Phase 6/7
- [ ] The audit-trail bug found and fixed (§4) is acknowledged
- [ ] No real evaluation, LLM, or cleaning-execution logic was implemented in this phase (confirmed — all deferred per the placeholder strategy)

## Recommended Next Step
Phase 6 — Strategy Optimization Engine: replace `PlaceholderMetricsEngine` with the real six-objective evaluator and the EM-based confidence estimator (Eqs. 2–6), and resolve the deferred Eq. 8 decision.

## Git Commit Message
```
feat(phase-5): implement multi-agent LangGraph workflow

- Add Application layer: 4 ports (IMetricsEngine, ILLMClient,
  IExperimentRepository, IDatasetRepository) and 5 use cases
- Add SQLiteExperimentRepository (full Repository pattern implementation)
  and FileDatasetRepository
- Add PlaceholderMetricsEngine and TemplateLLMClient: explicitly temporary,
  honestly-labeled interim implementations (real quality/cost heuristics
  and real score-grounded templating; replaced in Phase 6/7)
- Add AnalysisAgent, EvaluationAgent, DecisionReportingAgent (thin LangGraph
  node wrappers, no business logic of their own)
- Add WorkflowState, graph_builder (7-node graph, human-approval interrupt,
  rejection loop-back, verified via MemorySaver checkpointing)
- Add execution_node/validation_node/reporting_node (Phase 8 stubs)
- Add scripts/run_workflow_cli.py, an interactive end-to-end demo
- Add 34 new tests (unit + integration); fix a real audit-trail persistence
  gap found while running the CLI; fix 2 pre-existing Phase 3 mypy issues
- 91.31% coverage, 0 mypy issues across 57 files, all tests passing
```
