# AutoClean AI+ — Phase Verification Guide

How to check, for yourself, that each phase actually did what it claims. Two kinds of phases need two different kinds of checking:

- **Document-only phases** (1, 2, 12): there's no code to run — you're checking the deliverable document is complete, internally consistent, and matches the source paper/prior phases.
- **Code phases** (3, 4, 5, 6, 7, 8, 9, 10, 11): you can actually run commands and see pass/fail. This guide gives you the exact commands.

For **every** phase, regardless of type, the same three artifacts should exist and agree with each other — check these first, every time:

1. **The phase document** in `docs/phase_deliverables/PhaseN_*.md` — ends with a "Review Checklist" section. Go through it line by line.
2. **`PROJECT_MEMORY.md`** — should have been *fully rewritten* (not appended) to reflect that phase's completion. Check the "PHASE STATUS LOG" section shows the phase as COMPLETE.
3. **`CHANGELOG.md`** — should have a new `## [Phase N]` entry listing what was added/changed.

If any of these three is missing or stale, the phase isn't actually done, regardless of what else was delivered.

---

## Phase 1 — Research & Requirements

No code. Check the document itself.

**Steps:**
1. Open `docs/phase_deliverables/Phase1_Research_and_Requirements.md`.
2. Confirm all 18 sections are present (Problem Statement → Success Criteria) — use the table of contents implied by the section headers.
3. Spot-check the "Summary of the IEEE Paper" (§5) against the actual PDF: open `A_MultiObjective_Optimization_Framework_for_Data_Cleaning_Using_Large_Language_Models.pdf` yourself and confirm Eq. 1, Eq. 7, Eq. 8, the 4 methods (s1–s4), and the 9 dataset names actually appear in the paper as described. This is the single highest-value check — it's the check for AI-generated summary drift/hallucination.
4. Confirm §9/§10 (Features from Paper vs. Original Contributions) — every row should be traceable:  rows should map to something you can find in the paper;  rows should be things *not* in the paper.
5. Count: 15 Functional Requirements (§11), 11 Non-Functional Requirements (§12). If the phase claims these counts, count them yourself.
6. Confirm the Git commit message at the end is present and describes this phase only.

**Pass criteria:** all 18 sections present, paper summary verified against the actual PDF, FR/NFR counts match, attribution tags present throughout.

---

## Phase 2 — System Design 

No code. Check diagrams render and design is internally consistent.

**Steps:**
1. Open `docs/phase_deliverables/Phase2_System_Design.md` in a Markdown viewer that renders Mermaid (GitHub, VS Code with the Mermaid extension, or paste blocks into https://mermaid.live).
2. Confirm all 6 diagrams actually render without syntax errors: architecture diagram, layer diagram, workflow state diagram, class diagram, sequence diagram, component diagram, deployment diagram, ERD (8 total — check I didn't miscount above either).
3. Cross-check the **folder structure** (§3) against what was actually scaffolded in Phase 3/4 — open the repo and diff by eye.
4. Cross-check the **database schema** (§7 ERD) against the actual `schema.sql` file created in Phase 4 (`src/autoclean/infrastructure/persistence/sqlite/schema.sql`) — table names and columns should match exactly.
5. Read §14 (Paper vs. Original mapping) and confirm you understand and agree with the Eq. 8 deferral decision — this is a substantive scope call, not boilerplate.

**Pass criteria:** every diagram renders, folder structure and DB schema match what was later actually built, Eq. 8 deferral decision is understood and accepted.

---

## Phase 3 — Environment Setup

Code phase. You can run every one of these commands yourself right now.

**Steps (run from the project root, `autoclean-ai-plus/`):**

```bash
# 1. Create and activate a fresh virtual environment (tests it from a clean slate)
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies -- should complete with no errors
pip install -r requirements.txt -r requirements-dev.txt

# 3. Copy env file
cp .env.example .env

# 4. Run the environment verification script
python scripts/verify_environment.py
```

**Expected output:** `[OK]` for Python version, Dependencies, Settings, Logging, Directories. `[WARN]` (not `[FAILED]`) for Ollama reachability if you haven't started Ollama yet — that's expected and fine at this stage. Final line: `Environment verification passed. Ready for Phase 4.`

5. Confirm code-quality tooling actually runs:
```bash
make lint        # Ruff -- should report 0 errors
make typecheck    # mypy -- should report "Success: no issues found"
```
6. Confirm Docker actually builds (this is the real test of Phase 3 — a document can claim a Dockerfile works; only building it proves it):
```bash
make docker-build
```
Should complete without error and produce an image `autoclean-ai-plus:0.1.0`.

7. If you have Ollama installed: `ollama pull llama3.1:8b`, `ollama serve`, then re-run `python scripts/verify_environment.py` — the Ollama check should now say `[OK]`.

**Pass criteria:** `verify_environment.py` exits 0, `make lint`/`make typecheck` are clean, `make docker-build` succeeds.

---

## Phase 4 — Core Data Processing 

Code phase with real business logic. This is the first phase where "run the tests" is the actual verification, not a formality.

**Steps:**

```bash
# 1. Run the full unit test suite
PYTHONPATH=src pytest tests/unit -v
```
**Expected:** 50 passed, 0 failed, 0 errors, 0 warnings.

```bash
# 2. Check coverage meets the 80% threshold set in pyproject.toml
PYTHONPATH=src pytest tests/unit --cov=autoclean --cov-report=term-missing
```
**Expected:** overall coverage ≥80% (should show ~85%); the specific new-code packages (`domain`, `infrastructure/data_processing`, `infrastructure/persistence`) should show ~97%.

```bash
# 3. Run mypy against the new code specifically
PYTHONPATH=src mypy src/autoclean/domain src/autoclean/infrastructure/data_processing src/autoclean/infrastructure/persistence
```
**Expected:** `Success: no issues found in 18 source files`.

4. **Manually exercise the pipeline** with your own messy CSV (the most important check — proves it works on data you choose, not just the built-in test fixtures):
```bash
PYTHONPATH=src python3 -c "
import pandas as pd
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.strategy_generator import StrategyGenerator

df = pd.read_csv('your_own_file.csv')   # <- point this at a real CSV of yours
profile = DatasetProfiler().profile(df)
print(profile)
issues = IssueDetector().detect(df, profile)
for i in issues: print(i)
strategies = StrategyGenerator().generate(issues)
for s in strategies: print(s.name, '-', len(s.steps), 'steps')
"
```
Read the output and sanity-check it against what you know is actually wrong with that CSV (e.g., if you know column X has missing values, does a `MISSING_VALUES` issue show up for column X?).

5. Check the SQLite schema actually creates a working database:
```bash
PYTHONPATH=src python3 -c "
from pathlib import Path
from autoclean.infrastructure.persistence.sqlite.db_session import initialize_database
conn = initialize_database(Path('/tmp/test_autoclean.db'))
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print([t[0] for t in tables])
"
```
**Expected:** a list of 7 table names (`experiments`, `dataset_profiles`, `candidate_strategies`, `strategy_scores`, `decisions`, `audit_log`, `reports`).

**Pass criteria:** all 50 tests pass, coverage ≥80%, mypy clean, the pipeline produces sensible output on a real CSV you supply, the schema creates all 7 tables.

---

## Post-Phase-4 Revision — Ollama Switch 

Not a numbered phase, but check it the same way:

```bash
PYTHONPATH=src python3 -c "
from autoclean.config.settings import get_settings
s = get_settings()
assert s.llm_provider == 'ollama'
assert s.llm_model == 'llama3.1:8b'
print('OK:', s.llm_provider, s.llm_model, s.llm_base_url)
"
grep -c anthropic requirements.txt   # should print 0
```
If you've installed Ollama: `curl http://localhost:11434/api/tags` should return JSON (not a connection error).

---

## Phase 5 — Multi-Agent Implementation (not yet delivered)

When this phase arrives, verification will center on the LangGraph workflow actually running end-to-end, not just importing. Concretely, expect to:

1. Read the phase doc's Review Checklist (same pattern as every prior phase).
2. Run a new set of unit tests covering: the three agent wrapper classes, `WorkflowState` construction/validation, and the Application-layer use cases + port interfaces.
3. Run an **integration-style smoke test** invoking `graph_builder.run_workflow()` on a small dataset end-to-end up to the human-approval interrupt, and confirm the graph actually pauses there (not that it silently completes without waiting for approval — this is the single most important behavior to check, since it's the entire point of Phase 5's human-in-the-loop guarantee).
4. Confirm the Evaluation Agent's constructor genuinely has no `ILLMClient` parameter — e.g., `inspect.signature(EvaluationAgent.__init__)` and manually confirm no LLM-typed parameter exists. This checks the architectural rule isn't just a docstring promise.
5. Confirm `PROJECT_MEMORY.md`/`CHANGELOG.md` updated, per the standard three-artifact check.

---

## Phase 6 — Strategy Optimization Engine

1. Run unit tests for each of the six metric modules (`quality_metrics.py`, `cost_metrics.py`, `information_preservation.py`, `statistical_validity.py`, `fairness_metrics.py`, `downstream_ml_metrics.py`) and the EM estimator (`em_quality_estimator.py`) — each should have known-input/known-output test cases you can verify by hand for at least one simple case.
2. Confirm `objective_weights.yaml`'s placeholder values have been replaced with justified ones — read the phase doc's justification for each weight and decide if you agree.
3. Run the weighted decision matrix on the Phase 4 candidate strategies for a real dataset and confirm the ranking it produces matches your own intuition (e.g., does "Conservative" genuinely score higher on information preservation than "Aggressive," as the strategy design in Phase 4 implies it should?).
4. If the EM confidence estimator is implemented, verify it on a case with a known answer (e.g., synthetic data where you know the "true" quality) to confirm it converges to something sensible, not just that it runs without crashing.
5. Confirm the phase doc explicitly states whether Eq. 8 (DP refinement) was built as the optional feature flagged in Phase 2, or left documented-only — this was an open item since Phase 2, don't let it go unresolved silently.

---

## Phase 7 — Explainability & Decision Support 

```bash
# 1. Full test suite -- expect 170 passed
PYTHONPATH=src pytest -v

# 2. mypy -- expect 0 issues across 70 files
PYTHONPATH=src mypy --ignore-missing-imports src/autoclean
```

**The one thing no Claude session has been able to verify — you must do this yourself:**
This project's dev sandbox has no Ollama installed, so the real LLM path has only ever been tested via an injected fake. Verify the real thing:
```bash
ollama serve &          # if not already running
ollama pull llama3.1:8b # if not already pulled

PYTHONPATH=src python scripts/run_workflow_cli.py your_data.csv
```
Read the explanation printed. If it worked, it should NOT contain the line starting with `[Note: the local LLM was unavailable...]` — if you see that note, `OllamaLLMClient` failed and it silently fell back; check `ollama serve` is actually reachable at `http://localhost:11434`.

**Check the explanation is actually grounded, not fabricated** — read it and compare every number in it against the scores printed just above it. They should match exactly (or be absent — the LLM is instructed not to introduce new numbers).

**Test the consistency checker catches an actual fabrication** (not just passes clean text):
```bash
PYTHONPATH=src python3 -c "
import sys; sys.path.insert(0, 'src')
from autoclean.infrastructure.llm.explanation_consistency_checker import check_consistency
context = {'recommended_score': {'data_quality_score': 0.81}, 'alternatives': []}
warnings = check_consistency('This strategy scores 0.81 on quality and 0.42 on made-up accuracy.', context)
assert len(warnings) == 1 and '0.42' in warnings[0]
print('PASS: a genuinely fabricated number is caught')
"
```

**Confirm rejection still works with the new return shape:**
```bash
PYTHONPATH=src pytest tests/integration/test_workflow.py -v
```

**Pass criteria:** 170 tests pass, mypy clean, a real Ollama-generated explanation appears (no fallback notice) once you have Ollama running, the consistency checker catches a genuinely fabricated number, rejection/loop-back still works.

---

## Phase 8 — Cleaning Execution & Validation 

```bash
# 1. Full test suite -- expect 197 passed
PYTHONPATH=src pytest -v

# 2. mypy -- expect 0 issues across 76 files
PYTHONPATH=src mypy --ignore-missing-imports src/autoclean
```

**Run it and inspect every real artifact it produces:**
```bash
PYTHONPATH=src python scripts/run_workflow_cli.py your_data.csv
```
Approve the recommendation, then check all three outputs it prints paths for:
```bash
cat data/cleaned/*.csv          # the actual cleaned data
cat data/reports/*.md           # the executive report -- every section should be populated, not blank
python3 data/scripts/*_reproduce.py your_data.csv /tmp/check.csv  # run the standalone script yourself
diff <(sort data/cleaned/*.csv) <(sort /tmp/check.csv)  # should be identical (or empty diff)
```

**Confirm the audit trail is complete** (should show 8 distinct event types for one completed run):
```bash
sqlite3 data/autoclean.db "SELECT event_type, created_at FROM audit_log ORDER BY created_at;"
```

**Confirm validation actually fails on a bad case** (a validator that never fails isn't validating anything):
```bash
PYTHONPATH=src python3 -c "
import sys; sys.path.insert(0, 'src')
import pandas as pd
from autoclean.application.use_cases.validate_cleaned_dataset import ValidateCleanedDatasetUseCase
original = pd.DataFrame({'a': [1,2,3], 'b': [4,5,6]})
broken = original.drop(columns=['b'])  # simulate a strategy that corrupted the schema
report = ValidateCleanedDatasetUseCase().execute(original, broken)
assert report.passed is False and report.schema_consistent is False
print('PASS: validation correctly fails on a corrupted schema')
"
```

**Pass criteria:** 197 tests pass, mypy clean, the report has no blank sections, the generated script's output matches the app's cleaned CSV exactly, the audit trail shows all 8 event types, validation correctly fails on a deliberately broken case.

---

## Phase 9 — Dashboard Development 

```bash
# 1. Full test suite -- expect 222 passed
PYTHONPATH=src pytest -v

# 2. mypy -- expect 0 issues across 83 files
PYTHONPATH=src mypy --ignore-missing-imports src/autoclean
```

**Run the real app and click through it yourself:**
```bash
make dashboard   # or: streamlit run src/autoclean/presentation/streamlit_app.py
```
1. Upload a real CSV on page 1, click **Analyze Dataset**, confirm the profile metrics and detected issues look right for that specific file.
2. On page 2, confirm the Plotly chart's bars actually differ across strategies (not all identical) — real scores, not placeholders.
3. On page 3, confirm you cannot see a cleaned-file download until you click Approve — try refreshing or navigating away and back; the interrupt should still be holding.
4. Click **Reject** once and confirm a *different* strategy is recommended next, with its own explanation.
5. Approve, then actually download all three files (cleaned CSV, report, script) and open them — same checks as the Phase 8 guide.
6. On page 4, confirm your just-completed experiment appears with a real audit trail.

**Note:** if you're testing programmatically with Streamlit's `AppTest`, be aware it cannot simulate file uploads — this is a confirmed framework limitation, not a bug in this project (see `Phase9_Dashboard_Development.md` §2). Don't spend time trying to automate the upload step; seed `session_state` directly instead, the way this project's own test suite does. Also: `AppTest.from_file()` resolves its path argument relative to your current working directory, not the test file's location — always run `pytest` from the project root (`autoclean-ai-plus/`), never from a parent directory, or these tests will fail to even load the page and produce confusing failures elsewhere.

**Pass criteria:** 222 tests pass, mypy clean, the real server responds (try `curl http://localhost:8501/_stcore/health` while it's running — expect `ok`), all 4 pages work end-to-end with a real file.

---


## Quick Reference: Commands You'll Reuse Every Phase

```bash
# Full test suite + coverage
PYTHONPATH=src pytest tests/unit --cov=autoclean --cov-report=term-missing

# Linting and type checking
make lint
make typecheck

# Environment sanity check
python scripts/verify_environment.py

# Docker build + up
make docker-build && make docker-up
```
