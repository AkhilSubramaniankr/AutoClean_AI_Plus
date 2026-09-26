#!/usr/bin/env python
"""Verify that the local/container environment is correctly set up.

This script performs NO data cleaning, evaluation, or agent logic (that is
out of scope for Phase 3). It only checks that:
  1. The Python version is within the supported range.
  2. All runtime dependencies from requirements.txt are importable.
  3. Settings load and validate successfully from the environment / .env file.
  4. Logging configures without error.
  5. The expected data/ and logs/ directories exist or can be created.

Run with:
    python scripts/verify_environment.py

Exit code 0 = environment OK. Non-zero = at least one check failed, with the
failure(s) printed to stderr.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REQUIRED_MODULES = [
    "langgraph",
    "langchain_core",
    "langchain_ollama",
    "pandas",
    "numpy",
    "sklearn",
    "scipy",
    "plotly",
    "streamlit",
    "pydantic",
    "pydantic_settings",
    "dotenv",
    "sqlalchemy",
    "jinja2",
    "markdown",
    "pythonjsonlogger",
]

MIN_PYTHON = (3, 11)
MAX_PYTHON_EXCLUSIVE = (3, 13)


def check_python_version() -> list[str]:
    errors = []
    current = sys.version_info[:2]
    if not (MIN_PYTHON <= current < MAX_PYTHON_EXCLUSIVE):
        errors.append(
            f"Python {'.'.join(map(str, MIN_PYTHON))} <= version < "
            f"{'.'.join(map(str, MAX_PYTHON_EXCLUSIVE))} required, found {sys.version.split()[0]}"
        )
    return errors


def check_dependencies() -> list[str]:
    errors = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            errors.append(f"Missing or broken dependency '{module_name}': {exc}")
    return errors


def check_settings() -> list[str]:
    errors = []
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        from autoclean.config.settings import get_settings  # noqa: PLC0415

        settings = get_settings()
        if settings.app_name != "AutoClean AI+":
            errors.append("Settings loaded but app_name did not match expected value.")
    except Exception as exc:  # noqa: BLE001 - top-level verification script
        errors.append(f"Settings failed to load/validate: {exc}")
    return errors


def check_logging() -> list[str]:
    errors = []
    try:
        from autoclean.infrastructure.logging_config import configure_logging  # noqa: PLC0415

        configure_logging()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Logging configuration failed: {exc}")
    return errors


def check_directories() -> list[str]:
    errors = []
    for rel_dir in ["data/uploads", "data/cleaned", "logs"]:
        path = Path(rel_dir)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            errors.append(f"Could not create required directory '{rel_dir}': {exc}")
    return errors


def check_ollama_reachable() -> list[str]:
    """Non-fatal check: is the configured Ollama server reachable right now?

    Deliberately returns warnings, not hard errors -- Ollama is only used by
    the Decision & Reporting Agent (Phase 7, not yet implemented), so a
    developer working on Phases 4-6 should not have environment verification
    fail just because they haven't started `ollama serve` yet. Phase 7's own
    tests will assert connectivity where it actually matters.
    """
    warnings: list[str] = []
    try:
        import urllib.request

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        from autoclean.config.settings import get_settings  # noqa: PLC0415

        settings = get_settings()
        url = f"{settings.llm_base_url.rstrip('/')}/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=3) as response:  # noqa: S310
                if response.status != 200:
                    warnings.append(
                        f"Ollama server at {settings.llm_base_url} responded with "
                        f"status {response.status}"
                    )
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                f"Ollama server not reachable at {settings.llm_base_url} ({exc}). "
                "Not required until Phase 7 (Decision & Reporting Agent); "
                "start it with `ollama serve` and `ollama pull llama3.1:8b` before then."
            )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Could not check Ollama reachability: {exc}")
    return warnings


def main() -> int:
    checks = [
        ("Python version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Settings", check_settings),
        ("Logging", check_logging),
        ("Directories", check_directories),
    ]

    all_errors: list[str] = []
    for name, check_fn in checks:
        errors = check_fn()
        status = "OK" if not errors else "FAILED"
        print(f"[{status}] {name}")
        for error in errors:
            print(f"    - {error}", file=sys.stderr)
        all_errors.extend(errors)

    # Ollama reachability is checked separately and never fails the overall
    # verification (see check_ollama_reachable docstring).
    ollama_warnings = check_ollama_reachable()
    status = "OK" if not ollama_warnings else "WARN"
    print(f"[{status}] Ollama reachability")
    for warning in ollama_warnings:
        print(f"    - {warning}", file=sys.stderr)

    if all_errors:
        print(f"\n{len(all_errors)} check(s) failed. See details above.", file=sys.stderr)
        return 1

    print("\nEnvironment verification passed. Ready for Phase 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
