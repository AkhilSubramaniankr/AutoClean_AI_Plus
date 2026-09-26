# AutoClean AI+: Phase 7 — Explainability & Decision Support

**Project:** AutoClean AI+
**Phase:** 7 of 12 — Explainability & Decision Support
**Status:** Complete — for approval
**Depends on:** Phases 1–6 (all approved)

This phase replaces Phase 5's `TemplateLLMClient` with a real Ollama-backed adapter, and adds the anti-fabrication safeguard named as an open risk-mitigation item since Phase 1. Tagging convention:  **[PAPER]**,  **[ORIGINAL]**.

---

## 1. What Was Implemented

| Module | Purpose |
|---|---|
| `ollama_llm_client.py` | Real `ILLMClient` via `langchain-ollama`'s `ChatOllama`. Real grounding-rule system prompt: "use only the numeric scores given, do not invent statistics." Constructor accepts an injectable `chat_model` for testing without a live server. |
| `fallback_llm_client.py` | **New Decorator pattern.** Wraps a primary + fallback `ILLMClient`; on any primary failure, falls back to the deterministic template and visibly discloses that it did so. |
| `explanation_consistency_checker.py` | Extracts score-like numbers from any explanation and flags any that don't match a real computed score within tolerance — the concrete answer to Phase 1's Risk table item on numeric consistency checking. |

`ExplainRecommendationUseCase.execute()` now returns `(explanation_text, consistency_warnings)` instead of just a string — flagged explicitly, per this project's convention for any changed call shape. `DecisionReportingAgent` absorbed this change internally; every existing caller/test that only reads `state["explanation_text"]` needed zero changes.

Default wiring (`scripts/run_workflow_cli.py`): `FallbackLLMClient(primary=OllamaLLMClient(), fallback=TemplateLLMClient())`.

## 2. An Honest Limitation: What I Could and Couldn't Verify Here

**This sandboxed development environment has no Ollama installed**, and installing a full local LLM runtime plus pulling a multi-gigabyte model isn't practical here. So:

- **What I verified**: `OllamaLLMClient`'s prompt construction and grounding logic, using an injected fake chat model (`tests/unit/infrastructure/test_ollama_llm_client.py`) — confirmed the system prompt's grounding rules are sent, confirmed real scores (not fabricated ones) reach the user message, confirmed graceful handling when there are no alternatives.
- **What I did NOT verify**: an actual live round-trip to a real Ollama server producing real generated prose. I did, however, get a genuine, honest test of the **fallback mechanism** for free — since Ollama truly isn't running here, every CLI run this phase exercised the real failure path (`FallbackLLMClient` catching a real `ConnectionError`-class failure and falling back), which is itself valuable evidence the fallback works, just not evidence the primary path does.
- **What you need to do**: on a machine with `ollama serve` running and `llama3.1:8b` pulled, run `scripts/run_workflow_cli.py` and read the actual generated explanation. See the Review Checklist below.

## 3. A Real Bug Found by Actually Running This

Running the CLI against the messy test dataset produced a **false-positive consistency warning**: the checker flagged the literal `0.0` from the boilerplate text `"Scores (0.0-1.0, higher is better...)"` as an unmatched, possibly-fabricated number — because `0.0` genuinely doesn't match any real score, even though it's plainly a range label, not a claim. Fixed by excluding any matched number immediately adjacent to a hyphen joining it to another number (`_is_part_of_a_range_descriptor`), with a dedicated regression test (`test_range_descriptor_is_not_flagged_as_fabrication`) using the exact text that triggered it.

## 4. IEEE Paper Features vs. Original Contributions — Phase 7 Mapping

| Artifact |  PAPER |  ORIGINAL |
|---|---|---|
| Ollama-backed explanation generation | — | Entirely  — no explanation-generation concept in the paper |
| `explanation_consistency_checker.py` | — | Entirely  — directly answers the paper's own stated future-work gap on trust/interpretability (Phase 1 §5.7), which this project committed to addressing from the start |
| `FallbackLLMClient` (Decorator pattern) | — | Entirely  — operational resilience concern, no paper analogue |

---

## Review Checklist
- [ ] The `ExplainRecommendationUseCase` return-shape change (§1) is approved
- [ ] The consistency checker's scope and tolerance (§1, module docstring) are approved as "good enough for now," understanding its stated false-positive/false-negative limits
- [ ] **Action item for you**: run `ollama serve` + `ollama pull llama3.1:8b` and verify a real explanation on your own machine — I cannot do this from here (§2)
- [ ] The bug found and fixed (§3) is acknowledged
- [ ] No real cleaning execution/validation/reporting logic was implemented (still Phase 8 stubs, unchanged)

## Recommended Next Step
Phase 8 — Cleaning Execution & Validation: replace the `execution_node`/`validation_node`/`reporting_node` stubs with real logic, building on `StrategyExecutor` (already built in Phase 6).

## Git Commit Message
```
feat(phase-7): implement real LLM explanation with anti-fabrication check

- Add OllamaLLMClient: real ILLMClient via langchain-ollama's ChatOllama,
  with an injectable chat_model for testing without a live server
- Add FallbackLLMClient (new Decorator pattern): falls back to
  TemplateLLMClient on any primary failure, visibly discloses fallback
- Add explanation_consistency_checker.py: flags score-like numbers in any
  explanation that don't match a real computed score (Phase 1 Risk
  mitigation item)
- Update ExplainRecommendationUseCase to return (text, warnings); update
  DecisionReportingAgent and WorkflowState accordingly
- Fix a false-positive consistency-check bug found by running the CLI:
  "0.0-1.0" range-descriptor text was flagged as a fabricated number
- Fix 13 pre-existing mypy issues surfaced by a newer pandas-stubs version
  in a restored sandbox (bare ndarray/Series generics, stale type:ignore,
  stricter .loc[] indexing) -- pre-existing Phase 4/6 code, not Phase 7 scope
- 18 new tests (170 total), 91.59% coverage, 0 mypy issues across 70 files
- Honest limitation: no live Ollama round-trip verified in this sandbox;
  prompt construction verified via injected fake chat model instead
```
