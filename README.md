# AutoClean AI+

A Multi-Agent Explainable Decision Support System for Multi-Objective Data Cleaning Strategy Optimization.

Final-year engineering project, built on the research foundation of:

> Hu, T., Wang, J., Pu, W., Li, J., Gu, R., Bi, X., Yin, H., & Wang, Y.-P. (2026). *A Multi-Objective Optimization Framework for Data Cleaning Using Large Language Models.* Big Data Mining and Analytics, 9(3), 672–686.

Project documentation for every phase lives in [`docs/phase_deliverables/`](docs/phase_deliverables/). See [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) for the current, authoritative summary of project state, architecture, and open items.

## Project Status

Built phase-by-phase with an explicit approval gate between phases (see `PROJECT_SPECIFICATION.md`). Current status: **Phase 4 — Core Data Processing complete.** Domain entities and the deterministic profiling/issue-detection/strategy-generation engine are implemented and tested (50 unit tests, 97.3% coverage on new code). Agent orchestration (LangGraph) has not been implemented yet (begins Phase 5).

## Local Setup

Requires Python 3.11 or 3.12.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
make install-dev                # or: pip install -r requirements.txt -r requirements-dev.txt

# 3. Configure environment variables
cp .env.example .env
# Ollama defaults are already set in .env.example; no API key needed.

# 4. Install Ollama and pull the default model (only needed once Phase 7's
#    Decision & Reporting Agent is implemented -- not required for Phases 4-6)
#    See https://ollama.com for installation.
ollama pull llama3.1:8b
ollama serve   # if not already running as a background service

# 5. Verify the environment is correctly set up
make verify                     # or: python scripts/verify_environment.py
```

`make verify` checks the Python version, that every runtime dependency imports cleanly, that `Settings` loads and validates, that logging configures, and that the required `data/`/`logs/` directories exist — see `scripts/verify_environment.py`. It also does a non-fatal check that the configured Ollama server is reachable (a warning, not a failure, since the LLM is only used by Phase 7's not-yet-implemented Decision & Reporting Agent).

## Docker Setup

```bash
cp .env.example .env
make docker-build
make docker-up
```

This starts two containers: `autoclean-app` (Streamlit + LangGraph) and `autoclean-ollama` (the local LLM server). On first run, pull a model into the Ollama container:

```bash
docker exec autoclean-ollama ollama pull llama3.1:8b
```

The app will be available at `http://localhost:8501` once the Streamlit UI is implemented (Phase 9). The SQLite database, uploaded/cleaned datasets, and downloaded Ollama models all persist in named Docker volumes (`autoclean-data`, `autoclean-logs`, `ollama-models`) across rebuilds.

## Developer Commands

| Command | Purpose |
|---|---|
| `make install-dev` | Install runtime + dev dependencies and Git pre-commit hooks |
| `make verify` | Run the environment verification script |
| `make lint` | Run Ruff |
| `make format` | Run Black + Ruff `--fix` |
| `make typecheck` | Run mypy in strict mode over `src/` |
| `make test` | Run unit tests (`pytest -m unit`) |
| `make test-cov` | Run full test suite with coverage report |
| `make docker-build` / `make docker-up` / `make docker-down` | Docker lifecycle |

## Architecture

Four-layer Clean Architecture (Domain → Application → Infrastructure → Presentation) orchestrated by a LangGraph multi-agent workflow. Full details, diagrams, and design rationale: [`docs/phase_deliverables/Phase2_System_Design.md`](docs/phase_deliverables/Phase2_System_Design.md).

```
src/autoclean/
  domain/           # pure entities, no framework dependencies
  application/      # use cases + port interfaces (ABCs)
  infrastructure/   # SQLite repos, LLM adapter, metrics engines, reporting
  agents/           # thin LangGraph adapters (Analysis, Evaluation, Decision & Reporting)
  orchestration/    # shared WorkflowState + LangGraph graph_builder
  presentation/     # Streamlit app
  config/           # settings.py, objective_weights.yaml
```

## Traceability Convention

Every feature across this codebase and its documentation is tagged:
- **PAPER** — derived from Hu et al. (2026)
- **ORIGINAL** — introduced by AutoClean AI+

See `docs/phase_deliverables/Phase1_Research_and_Requirements.md` §9–§10 and `Phase2_System_Design.md` §14 for the full attribution tables.

## License

MIT (academic final-year project).
