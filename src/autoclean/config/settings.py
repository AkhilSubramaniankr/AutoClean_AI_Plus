"""Application configuration, driven entirely by environment variables / .env file.

Design decision (Phase 3, Section 4 of the Environment Setup document):
Configuration is centralized in a single `pydantic-settings` `BaseSettings`
subclass so that (a) every configurable value has a documented type, default,
and validation rule in one place, and (b) NFR-6 ("configuration shall be
externalized to configuration files/environment variables, not hard-coded")
is enforced by construction -- any code that needs a configurable value must
import `get_settings()` rather than reading `os.environ` ad hoc.

This module intentionally contains NO business logic. It is populated in
Phase 3 (Environment Setup) and consumed, unchanged in structure, by later
phases.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized, validated application settings.

    Values are loaded, in order of precedence, from: (1) actual environment
    variables, (2) a `.env` file at the project root, (3) the defaults below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AUTOCLEAN_",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    app_name: str = "AutoClean AI+"
    environment: str = Field(default="development", description="development | test | production")
    log_level: str = Field(default="INFO", description="Standard Python logging level name.")

    # --- Paths ---
    project_root: Path = Path(__file__).resolve().parents[3]
    data_upload_dir: Path = Field(default=Path("data/uploads"))
    data_cleaned_dir: Path = Field(default=Path("data/cleaned"))
    reports_dir: Path = Field(default=Path("data/reports"))
    scripts_dir: Path = Field(default=Path("data/scripts"))

    # --- Database (SQLite) ---
    database_path: Path = Field(default=Path("data/autoclean.db"))

    # --- LLM client (Decision & Reporting Agent ONLY -- see Phase 2 Section 1) ---
    # Provider decision (REVISED -- see Phase 3 Addendum, Environment Setup doc):
    # Ollama, run locally/self-hosted, wrapped behind the ILLMClient port
    # (Adapter pattern) so the provider remains swappable without touching
    # use-case code. Chosen over a paid hosted API (Anthropic/OpenAI) to
    # avoid per-token cost for this academic project. No API key is required
    # for Ollama; llm_api_key is kept as an optional field for future
    # providers that do need one.
    llm_provider: str = Field(default="ollama", description="Adapter selector; see infrastructure/llm/")
    llm_model: str = Field(
        default="llama3.1:8b",
        description="Ollama model tag. Must be pulled locally first: `ollama pull llama3.1:8b`.",
    )
    llm_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL. In Docker Compose this is the 'ollama' service name (see docker-compose.yml).",
    )
    llm_api_key: str | None = Field(
        default=None, description="Not required for Ollama; reserved for future hosted-provider adapters."
    )
    llm_max_tokens: int = Field(default=1024, ge=1)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    llm_timeout_seconds: int = Field(default=60, ge=1, description="Higher default than a hosted API, since local inference is typically slower.")

    # --- Evaluation engine defaults (weights finalized/justified in Phase 6) ---
    objective_weights_path: Path = Field(default=Path("src/autoclean/config/objective_weights.yaml"))
    em_max_iterations: int = Field(default=50, ge=1)
    em_convergence_tolerance: float = Field(default=1e-4, gt=0.0)

    # --- Streamlit / interactive limits ---
    max_upload_size_mb: int = Field(default=200, ge=1)
    max_preview_rows: int = Field(default=1000, ge=1)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}, got {value!r}")
        return normalized

    def resolved(self, relative: Path) -> Path:
        """Resolve a configured relative path against the project root."""
        return relative if relative.is_absolute() else self.project_root / relative


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance.

    Cached with `lru_cache` so settings are parsed/validated exactly once per
    process, and so tests can call `get_settings.cache_clear()` to reload
    configuration between test cases that vary environment variables.
    """
    return Settings()
