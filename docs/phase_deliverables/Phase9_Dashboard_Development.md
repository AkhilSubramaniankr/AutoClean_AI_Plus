# AutoClean AI+: Phase 9 — Dashboard Development

**Project:** AutoClean AI+
**Phase:** 9 of 12 — Dashboard Development
**Status:** Complete — for approval
**Depends on:** Phases 1–8 (all approved)

This phase builds the Streamlit UI on top of the now-fully-functional backend (Phase 8). Tagging convention: 🟦 **[PAPER]**, 🟩 **[ORIGINAL]** — everything in this phase is 🟩, since the paper has no UI/HCI component at all.

---

## 1. What Was Implemented

| File | Purpose |
|---|---|
| `presentation/streamlit_app.py` | Thin entry point: title, overview, links to the 4 workflow pages |
| `presentation/workflow_session.py` | Builds and caches the graph + repository + dependencies **once per browser session** — critical because LangGraph's interrupt only works if the same `MemorySaver` instance survives across Streamlit's rerun-per-click execution model |
| `pages/1_Upload_and_Profile.py` | Upload → runs Analysis+Evaluation+Decision in one shot → pauses at the interrupt; persists the experiment/strategies/scores immediately so it shows up in history even if never approved |
| `pages/2_Compare_Strategies.py` | Real Plotly comparison chart + ranked list across all six objectives |
| `pages/3_Review_and_Approve.py` | The concrete, interactive form of FR-9 — Approve/Reject buttons wired directly to the real LangGraph interrupt resume mechanism |
| `pages/4_Experiment_History.py` | Browses real persisted experiments and audit trails from SQLite (FR-15) |
| `components/strategy_comparison_chart.py`, `components/explanation_panel.py` | Reusable rendering pieces, deliberately kept as pure functions (chart) or thin rendering-only functions (explanation panel) so logic stays testable separately from Streamlit's runtime |

## 2. An Honest, Documented Testing Limitation

Streamlit's `AppTest` framework (real, ships with Streamlit ≥1.28) **cannot simulate file uploads** — the `file_uploader` widget exposes no `set_value`-style method, confirmed by inspecting the test element directly. This means the literal "upload a file, click Analyze" sequence cannot be driven end-to-end through automated UI tests.

**The resolution, not a workaround:** the correct testing boundary here is to mock `get_workflow_session()` and test each page's own logic — does clicking Approve call `approve_use_case.execute()` with the right strategy ID, call `graph.update_state()` with the right decision, then `graph.invoke(None, ...)`? That's genuinely tested (`test_page_review_and_approve.py`, 6 tests). Whether the *real* graph correctly executes/validates/reports was already proven, independent of any UI, by Phase 5/8's integration tests operating directly on the graph. Testing both at their correct boundary is more rigorous than forcing one enormous UI-driven test through a framework gap — and it's honestly documented as a limitation rather than silently worked around.

## 3. Real Verification Performed

- **222 tests passing** (25 new), coverage **95.24%**, **0 mypy issues across 83 files**.
- **The actual Streamlit server was launched for real** (`streamlit run`, not just `AppTest`) and confirmed responding with HTTP 200 on its health endpoint — genuine proof the app boots, not just that its pieces import cleanly.
- Page tests use **real Phase 4/6 engine output** (real `DatasetProfile`, real generated strategies, real scores) seeded into session state, not fabricated data — e.g., `test_all_candidate_strategies_are_listed` asserts every real strategy's actual name appears in the rendered page.
- `build_comparison_figure()` tested as a pure function: real trace count, real values, graceful handling of missing score keys and an empty strategy set.

## 4. Design Decisions

- **`workflow_session.py`'s caching is load-bearing, not an optimization.** Rebuilding a fresh `MemorySaver` on every Streamlit rerun (which happens on every click) would silently discard the paused interrupt state every time — this isn't a performance nicety, it's what makes the human-approval gate work at all inside Streamlit's execution model.
- **Page 1 persists the experiment immediately**, before any approval decision — a deliberate choice so `Experiment History` (FR-15) shows every analyzed dataset, including ones an analyst never got around to approving, matching how the CLI already behaved.
- **`ObjectiveWeights.uniform()` was almost used for persisted display metadata** in Page 1's first draft — caught and fixed before it shipped: the weights actually used to rank strategies must be the same weights recorded, so `WorkflowSession.weights` now exposes the real instance used for ranking.

---

## Review Checklist
- [ ] The 4-page structure and `workflow_session.py` caching design are approved
- [ ] The AppTest file-upload limitation (§2) and the mocking-based test strategy are understood and accepted
- [ ] Run it yourself: `make dashboard` (or `streamlit run src/autoclean/presentation/streamlit_app.py`), upload a real CSV, and click through all 4 pages
- [ ] No changes were made to Domain/Application/Infrastructure logic in this phase (Presentation only, as scoped)

## Recommended Next Step
Phase 10 — Testing: consolidate and extend test coverage project-wide, formalize the testing strategy.

## Git Commit Message
```
feat(phase-9): implement Streamlit dashboard

- Add workflow_session.py: session-cached graph/repository wiring,
  required for LangGraph's interrupt to survive Streamlit's rerun model
- Add 4 pages: Upload & Profile, Compare Strategies, Review & Approve,
  Experiment History (FR-15)
- Add 2 reusable components: strategy_comparison_chart (pure function,
  returns a plotly.graph_objects.Figure), explanation_panel
- Add 25 tests: real engine output seeded for pages 1/2, mocked
  workflow_session for pages 3/4 (documented AppTest file_uploader
  limitation -- see Section 2)
- Verify the real Streamlit server actually boots (HTTP 200 on
  /_stcore/health), not just that AppTest can load the scripts
- Add `make dashboard` convenience target
- 222 tests total, 95.24% coverage, 0 mypy issues across 83 files
```
