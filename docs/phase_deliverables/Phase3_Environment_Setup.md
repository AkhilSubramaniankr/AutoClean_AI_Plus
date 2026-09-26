# AutoClean AI+: Phase 3 — Environment Setup

**Project:** AutoClean AI+: A Multi-Agent Explainable Decision Support System for Multi-Objective Data Cleaning Strategy Optimization
**Phase:** 3 of 12 — Environment Setup
**Status:** Complete — for approval
**Depends on:** Phase 1 (approved), Phase 2 (approved)

This phase scaffolds the project exactly as specified in Phase 2 §3 (Folder Structure) and stands up dependency management, configuration, logging, containerization, and developer tooling. **No agent logic, evaluation logic, or cleaning logic has been implemented** — every file created in this phase is infrastructure/scaffolding (package markers with docstrings, configuration schemas, Docker/CI-adjacent tooling), consistent with "Phase 3 – Environment Setup" as distinct from "Phase 4 – Core Data Processing" and "Phase 5 – Multi-Agent Implementation" in the project specification's phase list.

Tagging convention carried forward: 🟦 **[PAPER]**, 🟩 **[ORIGINAL]**. Most of this phase is infrastructure with no direct paper/original content distinction — tags are applied only where a choice was shaped by a paper-derived requirement (e.g., the LLM-isolation setting).

---

## Revision Log

**Revision 1 (post-Phase-4 approval, applied retroactively to this document's Section 6):** the LLM provider decision below was changed from **Anthropic Claude** (a paid hosted API) to **Ollama** (a free, self-hosted local LLM server), at the user's explicit request to avoid per-token cost. This is a configuration-only change: `Settings.llm_provider`/`llm_model`/`llm_base_url` defaults were updated, `requirements.txt` swapped `anthropic` for `langchain-ollama`, `docker-compose.yml` gained a companion `ollama` service, and `.env.example`/`README.md`/`verify_environment.py` were updated to match. No agent code was affected, because the Decision & Reporting Agent (the only component that would call `ILLMClient`) had not yet been implemented (it remains Phase 7 work) — this is exactly the scenario the Adapter-pattern `ILLMClient` port (Phase 2, §12) was designed to make cheap. Section 6 below is left as originally written (the Anthropic decision and its rationale) for audit-trail purposes, with a new Section 6a documenting the revision itself.

---

## 1. What Was Scaffolded

The full folder structure specified in Phase 2 §3 now exists on disk, with every Python package containing an `__init__.py` that documents the package's purpose and which phase will populate it — so an academic reviewer (or a future contributor) can navigate the empty scaffold and immediately understand its intended contents without any code existing yet.

```
autoclean-ai-plus/
├── src/autoclean/
│   ├── domain/{entities,value_objects}/          [documented, empty — Phase 4/5/6]
│   ├── application/{ports,use_cases}/             [documented, empty — Phase 5/6/7/8]
│   ├── infrastructure/
│   │   ├── persistence/sqlite/                    [documented, empty — Phase 4]
│   │   ├── llm/                                   [documented, empty — Phase 7]
│   │   ├── metrics/                               [documented, empty — Phase 6]
│   │   ├── reporting/                             [documented, empty — Phase 8]
│   │   └── logging_config.py                      [IMPLEMENTED this phase]
│   ├── agents/                                    [documented, empty — Phase 5]
│   ├── orchestration/{nodes}/                     [documented, empty — Phase 5/8]
│   ├── presentation/{pages,components}/           [documented, empty — Phase 9]
│   └── config/
│       ├── settings.py                            [IMPLEMENTED this phase]
│       └── objective_weights.yaml                 [IMPLEMENTED this phase, placeholder values]
├── tests/{unit/{domain,application,infrastructure},integration,fixtures}/  [documented, empty]
├── scripts/verify_environment.py                  [IMPLEMENTED this phase]
├── docs/{phase_deliverables,diagrams}/
├── data/{uploads,cleaned,reports,scripts}/         [empty, .gitkeep'd]
├── logs/                                           [empty, .gitkeep'd]
├── pyproject.toml, requirements.txt, requirements-dev.txt
├── Dockerfile, docker-compose.yml, .dockerignore
├── .env.example, .gitignore, .pre-commit-config.yaml, Makefile
└── README.md
```

---

## 2. Dependency Management Strategy

### Theory
Python dependency management tools trade off three properties: (a) reproducibility (exact, lockable versions), (b) simplicity/ubiquity (how much tooling knowledge is required to onboard), and (c) build/packaging sophistication (workspace support, lockfile resolution speed).

### Design Decision
`requirements.txt` (runtime) + `requirements-dev.txt` (tooling, layered on top via `-r requirements.txt`), with compatible-release (`~=`) version specifiers, plus a `pyproject.toml` used only for project metadata and tool configuration (Black/Ruff/mypy/Pytest/coverage), not for dependency resolution.

### Alternatives Considered
- **Poetry**: rejected — introduces a second lockfile format and a resolver with a learning curve disproportionate to this project's dependency graph size (~20 packages, no complex conflicting sub-dependencies); also a heavier ask for an academic panel that may just want to `pip install -r requirements.txt` and run.
- **pip-tools (`pip-compile`)**: a reasonable middle ground (generates a fully pinned lockfile from a loose `requirements.in`), but rejected for this phase as an extra moving part; noted below as a natural Phase 11 (Deployment) upgrade if fully pinned reproducibility becomes a priority at deployment time.
- **Conda/environment.yml**: rejected — the project has no dependency that requires Conda's binary package management (e.g., no GPU-bound scientific package with notoriously fragile pip wheels); pip is sufficient.

### Justification
`requirements.txt` is the lowest-friction option that still gives every dependency a controlled version range (`~=`), is instantly familiar to any Python reviewer, and integrates directly into the Dockerfile's builder stage without any additional tool being installed in the image.

---

## 3. Python Version and Package Layout

### Design Decision
Python `>=3.11,<3.13`, with source under `src/autoclean/` (the "src layout") rather than a flat top-level package.

### Alternatives Considered
- **Flat layout** (`autoclean/` directly at repo root, no `src/`): rejected — the src layout prevents accidentally importing the package from the working directory instead of the installed/editable package, which is a common source of "works on my machine" bugs precisely when tests run against source that hasn't actually been packaged correctly.
- **Python 3.9/3.10 support**: rejected — no requirement to support older interpreters for a new, single-deployment academic project; 3.11+ gives access to `tomllib`, improved error messages, and performance improvements with no compatibility cost here.

### Justification
`src/` layout is now standard Python packaging guidance (PyPA) specifically because it catches the "import works only because I'm in the right directory" failure mode before it reaches Phase 10 testing or Phase 11 deployment.

---

## 4. Configuration Management

### Theory
NFR-6 (Phase 1) requires configuration to be externalized to configuration files/environment variables, not hard-coded. The theoretical backing is the [Twelve-Factor App](https://12factor.net/config) principle: configuration that varies between deploys (secrets, resource handles) belongs in the environment, not in source code, so the same built artifact can run in development, test, and production without modification.

### Design Decision
A single `pydantic-settings` `BaseSettings` subclass (`src/autoclean/config/settings.py`) is the **only** sanctioned way to read configuration anywhere in the codebase; a `get_settings()` accessor is cached with `lru_cache` so settings are parsed and validated exactly once per process. A companion `objective_weights.yaml` holds the (currently placeholder) six-objective weights separately, since those are structured/numeric domain configuration rather than environment-style scalars — this mirrors how the paper's own weighted-gain parameter `alpha` was a tunable, not a hard-coded constant 🟦[PAPER-motivated separation of tunable weights from code].

### Alternatives Considered
- **`python-decouple` / raw `os.environ.get()` calls scattered across modules**: rejected — provides no single point of truth, no type validation, and no IDE-discoverable schema of "what can be configured," which directly undermines NFR-6's intent.
- **A single JSON/YAML config file for everything, including secrets**: rejected — mixing secrets (`LLM_API_KEY`) into a versioned config file structurally invites accidental commits of secrets; environment variables plus a gitignored `.env` cleanly separate secret material from versioned defaults.

### Justification
`pydantic-settings` gives NFR-6 (externalized config) and NFR-3 (type hints) simultaneously — every setting is both environment-overridable and statically typed/validated at process startup, so a misconfigured `.env` fails fast with a clear Pydantic validation error rather than surfacing as a mysterious runtime bug three layers deep in Phase 6's evaluation engine.

---

## 5. Logging Strategy

### Theory
NFR-4 requires structured logging, not print statements. Structured (JSON) logs are machine-parseable, which matters for a system that must also maintain a SQLite audit trail (Phase 2 §7) — logs and the audit trail are complementary, not redundant: the audit trail is the durable, queryable record of *decisions*; logs are the higher-frequency, rotating record of *execution*, useful for debugging failures that never became a persisted decision (e.g., an LLM timeout during explanation generation).

### Design Decision
Standard library `logging`, configured via `logging.config.dictConfig`, with two handlers: a human-readable console handler (development) and a rotating JSON file handler (`logs/autoclean.log`, 5 MB × 5 backups) via `python-json-logger`.

### Alternatives Considered
- **loguru**: rejected — a pleasant API, but an additional dependency for functionality the standard library already provides adequately once configured; adds a dependency with no NFR it satisfies that stdlib logging cannot.
- **No file handler, console only**: rejected — Docker deployment (Phase 11) benefits from a persisted, rotating log file independent of container stdout capture, especially for post-mortem debugging of a completed container run.

### Justification
Standard library `logging` plus one small formatter dependency keeps the dependency surface minimal (consistent with the dependency-management philosophy in §2) while still satisfying NFR-4 with machine-parseable structured output.

---

## 6. LLM Provider Decision (Open Item from Phase 2 §13, Now Resolved)

### Design Decision
The default LLM provider for the Decision & Reporting Agent's `ILLMClient` implementation is **Anthropic Claude**, via the official `anthropic` Python SDK, configured through `Settings.llm_provider` / `Settings.llm_model` / `Settings.llm_api_key`.

### Alternatives Considered
- **OpenAI GPT models**: a valid alternative also compatible with the Adapter-pattern `ILLMClient` port from Phase 2 §12; not chosen as the *default* only to keep one concrete, testable default for Phase 7, not because it is unsuitable.
- **A local/open-source model (e.g., via Ollama)**: attractive for zero marginal API cost, but rejected as the default because explanation quality/consistency is more predictable with a hosted frontier model for a final-year demo, and the paper itself used a frontier LLM (GPT-4o) as its top-tier method 🟦[PAPER], so a comparably capable hosted model keeps the explanation-quality bar consistent with the paper's own assumptions about what "the expensive, high-quality option" looks like.

### Justification
Because `ILLMClient` is a Port (Phase 2 §12, Adapter pattern), this choice is a **default, not a lock-in** — `Settings.llm_provider` already exists as a switch, and Phase 7 can add an OpenAI-compatible or local adapter alongside the Anthropic one without touching `ExplainRecommendationUseCase`. This resolves Phase 2's open item while preserving the architectural flexibility that made the item safe to defer in the first place.

---

## 6a. Revision: LLM Provider Changed to Ollama

### Theory
Ollama is a local LLM runtime that serves open-weight models (e.g., Llama 3.1, Qwen 2.5, Mistral) over a REST API on `localhost:11434`, with no per-token billing and no external network dependency once a model is pulled. It trades raw explanation quality and reasoning consistency (an 8B-parameter local model is not at frontier-model capability) for zero marginal cost and full data locality — no dataset summary or prompt content ever leaves the machine running AutoClean AI+.

### Design Decision
Default LLM provider changed from Anthropic Claude to **Ollama**, default model **`llama3.1:8b`**, reached over `Settings.llm_base_url` (default `http://localhost:11434`, overridden to the Docker Compose service name `http://ollama:11434` in containerized deployment). Integration path: `langchain-ollama`'s `ChatOllama`, chosen over the plain `ollama` Python client so the eventual `ILLMClientImpl` (Phase 7) can plug directly into a LangGraph node using the same `langchain-core` message types already used for orchestration, rather than hand-rolling request/response parsing against Ollama's raw REST API.

### Alternatives Considered
- **Keep Anthropic as default, let the user override via `Settings.llm_provider`**: rejected as the *default* — the user's stated priority is avoiding paid API cost entirely for this project, so the shipped default should reflect that, not require every fresh setup to remember an override.
- **OpenAI-compatible local server (e.g., LM Studio, vLLM's OpenAI-compatible endpoint)**: a reasonable alternative also reachable behind the same `ILLMClient` port; not chosen as default because Ollama has the simplest single-binary install and the most common `ollama pull <model>` workflow for a final-year project audience, minimizing setup friction documented in the README.
- **Plain `ollama` Python client instead of `langchain-ollama`**: rejected — would require a separate message-format translation layer between LangGraph's `langchain-core` message types and Ollama's raw JSON schema; `langchain-ollama` removes that translation layer entirely, at the cost of one additional dependency already justified by the project's existing LangGraph/langchain-core usage.
- **Larger local model (e.g., `llama3.1:70b`, `qwen2.5:32b`) as the default**: rejected as the *default* — a 70B-class model requires substantially more RAM/VRAM than can be assumed on a typical final-year-project development machine; `llama3.1:8b` is runnable on modest consumer hardware (CPU-only inference is viable, if slow). `Settings.llm_model` remains freely configurable for anyone with the hardware to run a larger model.

### Impact on Prior Decisions
- No agent code is affected — the Decision & Reporting Agent does not exist yet (Phase 7).
- `requirements.txt`: `anthropic~=0.34.0` replaced with `langchain-ollama~=0.2.0`.
- `Settings` (Phase 3, `config/settings.py`): added `llm_base_url`; `llm_api_key` is now optional and unused by the default provider, retained only for a future hosted-provider adapter.
- `docker-compose.yml`: revised from a single-service to a two-service deployment (`autoclean-app` + `ollama`), with a new `ollama-models` named volume. This is a **scope revision to the Phase 2 §11 Deployment Diagram**, which showed a single application container; it remains a single-machine, single-user deployment overall (Phase 1 §8 Out of Scope is unaffected), just with two containers instead of one.
- `scripts/verify_environment.py`: swapped the `anthropic` import check for `langchain_ollama`, and added a new **non-fatal** Ollama-reachability check (a warning, not a failure, since the LLM is not required until Phase 7).
- `.env.example` / `README.md`: updated to remove the API-key setup step and document `ollama pull llama3.1:8b` instead.

### Justification
This revision costs nothing architecturally — it is exactly the scenario the Adapter-pattern `ILLMClient` port was designed to absorb cheaply (Phase 2 §12) — and it directly satisfies the user's explicit cost constraint. The two-container Docker revision is flagged explicitly here, the same way the original `infrastructure/data_processing/` addendum was flagged in Phase 4, so the deviation from the originally-approved Phase 2 deployment diagram is visible and reviewable rather than silently introduced.

---

## 7. Docker Strategy

### Theory
A multi-stage Docker build separates the *build environment* (compilers, build-time-only packages) from the *runtime environment* (only what's needed to execute the app), producing a smaller, more secure final image.

### Design Decision
Two-stage `Dockerfile`: a `builder` stage (`python:3.11-slim` + `build-essential`) installs dependencies into a virtual environment; a `runtime` stage (`python:3.11-slim`, no build tools) copies only the venv and source, runs as a non-root `autoclean` user, and exposes Streamlit's default port 8501 with a healthcheck against Streamlit's own `/_stcore/health` endpoint.

### Alternatives Considered
- **Single-stage build**: rejected — would ship `build-essential` and other build-time-only tooling into the final production image, increasing image size and attack surface for no runtime benefit.
- **Alpine base image** (`python:3.11-alpine`): rejected — musl-libc compatibility issues are a well-known source of friction for the scientific Python stack (NumPy/SciPy/Pandas wheel availability), and the resulting debugging time is not worth the image-size savings for a single-deployment academic project.
- **Running as root in the container**: rejected — trivial to avoid (`useradd` + `USER autoclean`) and is a baseline container security practice with no functional cost here.

### Justification
This mirrors the Phase 2 §11 Deployment Diagram exactly: one application container, named volumes for `data/` and `logs/` so the SQLite audit trail and cleaned datasets persist across image rebuilds, and the LLM API key injected via `.env` (NFR-6) rather than baked into the image (which would also leak the secret into image layers/history).

---

## 8. Code Quality Tooling

### Design Decision
Black (formatting) + Ruff (linting, import sorting, and several rule families that used to require separate tools — flake8, isort, pyupgrade, flake8-bugbear) + mypy in `strict` mode over `src/` (relaxed only for the Presentation layer, where third-party Streamlit stubs are incomplete) + `pre-commit` to run all of the above automatically before each commit.

### Alternatives Considered
- **flake8 + isort + pyupgrade as separate tools**: rejected in favor of Ruff, which reimplements the relevant rule sets in a single, much faster Rust-based tool — functionally equivalent coverage with fewer moving parts and faster CI/pre-commit runs.
- **mypy in default (non-strict) mode everywhere, including Domain/Application**: rejected — Domain and Application are this project's own hand-written business logic and are exactly where strong typing (NFR-3) matters most; strict mode is deliberately *not* relaxed there, only for the Presentation layer where third-party stub gaps would otherwise generate noise unrelated to this project's own code quality.

### Justification
This tooling set directly operationalizes NFR-2 (Clean Architecture/SOLID — mypy strict mode makes layer-boundary type contracts enforceable) and NFR-3 (type hints — mypy strict mode fails the build on missing type hints) rather than leaving them as unenforced conventions.

---

## 9. Environment Verification Script

`scripts/verify_environment.py` (implemented this phase) performs five checks — Python version, dependency importability, `Settings` load/validation, logging configuration, and required directory creation — and returns a non-zero exit code with itemized failures if anything is wrong. This is intentionally the **only** executable logic written in this phase: it verifies the environment itself, performs no data cleaning, evaluation, or agent behavior, and is therefore in scope for "Environment Setup" without encroaching on Phase 4/5.

---

## 10. IEEE Paper Features vs. Original Contributions — Phase 3 Mapping

| Setup Artifact | 🟦 PAPER-derived | 🟩 ORIGINAL |
|---|---|---|
| `objective_weights.yaml` structure (weights as externalized, tunable config) | Conceptually mirrors the paper treating `alpha` (Eq. 7) as a tunable parameter rather than a hard-coded constant | The specific 6 named weight keys are 🟩 (paper has only 2 implicit objectives) |
| LLM-isolation enforced via package boundaries (`infrastructure/llm/` docstring: "Evaluation Agent must never import from here") | Enforces the 🟦-motivated project rule that the LLM never performs deterministic calculation | Enforcement mechanism itself (package-level convention, later a lint rule) is 🟩 |
| Everything else in this phase (Docker, logging, settings schema, tooling, folder scaffolding) | — | Entirely 🟩 — standard software engineering setup with no paper analogue |

---

## Review Checklist

- [ ] Folder structure matches Phase 2 §3 exactly (confirmed by directory listing above)
- [ ] Dependency management strategy (`requirements.txt` + `requirements-dev.txt`, pip-based) is approved
- [ ] `pyproject.toml` tool configuration (Black, Ruff, mypy strict, Pytest, coverage ≥80%) is approved
- [ ] `Settings` schema in `config/settings.py` covers all configuration needs anticipated through Phase 9 (paths, DB, LLM, EM parameters, Streamlit limits)
- [ ] Placeholder `objective_weights.yaml` values are understood as **not yet justified** — real justification is deferred to Phase 6, per Phase 1's risk mitigation plan
- [ ] Logging strategy (stdlib `logging`, JSON file handler + console handler) is approved
- [ ] **LLM provider decision — Anthropic Claude as default, behind the `ILLMClient` port — is explicitly approved or revised.** This is the one substantive open decision from Phase 2 being closed in this phase; please confirm before Phase 7 builds against it.
- [ ] Docker multi-stage build, non-root user, and named-volume persistence strategy are approved
- [ ] Code quality tooling (Black/Ruff/mypy strict/pre-commit) is approved
- [ ] `scripts/verify_environment.py` scope (verification only, no business logic) is confirmed appropriate for this phase
- [ ] No agent, evaluation, or cleaning logic has been implemented in this phase (confirmed)

---

## Summary of Completed Work

Phase 3 has scaffolded the entire Phase 2 folder structure with documented, empty packages; implemented three genuinely "environment setup" modules (`config/settings.py`, `infrastructure/logging_config.py`, `scripts/verify_environment.py`); externalized configuration via `pydantic-settings` and a `.env`-driven workflow (NFR-6); set up structured JSON logging (NFR-4); resolved Phase 2's open LLM-provider decision (Anthropic Claude, via the existing `ILLMClient` Adapter port); and produced a full Docker/Compose deployment setup, dependency files, and code-quality tooling (Black/Ruff/mypy/pre-commit/Makefile), consistent with NFR-2, NFR-3, NFR-8, and NFR-9 from Phase 1. No agent, evaluation, or cleaning business logic was implemented, per phase-gating rules.

## Remaining Work
Phases 4–12, beginning with Phase 4 (Core Data Processing), pending your approval of this document.

## Recommended Next Step
Review the checklist above — in particular, confirm or revise the LLM provider decision (§6) — then approve or request revisions. Once approved, Phase 4 will implement the Domain layer entities and the deterministic dataset profiling/issue-detection logic (Pandas/NumPy/Scikit-learn) that the Analysis Agent will later wrap.

## Git Commit Message
```
chore(phase-3): scaffold environment, config, logging, and tooling

- Create full src/autoclean package structure per Phase 2 folder design,
  with every package documented via __init__.py docstrings stating its
  purpose and target implementation phase
- Add pydantic-settings based Settings schema (config/settings.py) and
  placeholder objective_weights.yaml, externalizing all configuration
  per NFR-6
- Add structured JSON logging configuration (infrastructure/logging_config.py)
  per NFR-4
- Add scripts/verify_environment.py to validate Python version,
  dependencies, settings, logging, and required directories
- Resolve Phase 2's open LLM-provider decision: Anthropic Claude as the
  default ILLMClient implementation, configurable via Settings
- Add requirements.txt / requirements-dev.txt, pyproject.toml (Black,
  Ruff, mypy strict, Pytest, coverage config)
- Add multi-stage Dockerfile (non-root runtime user, healthcheck),
  docker-compose.yml with named volumes, .dockerignore
- Add .env.example, .gitignore, .pre-commit-config.yaml, Makefile, README.md
- No agent, evaluation, or cleaning business logic implemented in this phase
```
