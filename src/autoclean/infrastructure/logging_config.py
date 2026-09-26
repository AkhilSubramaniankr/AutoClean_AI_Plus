"""Structured logging configuration for AutoClean AI+.

Design decision (Phase 3, Section 5 of the Environment Setup document):
Uses the Python standard library `logging` module (not a third-party logger
like loguru) with a JSON formatter, so that (a) no extra runtime dependency
is introduced for something the stdlib already does well, and (b) every log
line is machine-parseable JSON -- which matters here specifically because
log lines double as a lightweight supplementary trace alongside the SQLite
audit trail (Phase 2, AUDIT_LOG table) during development and debugging.

This module contains configuration only, no business logic, per the
Phase 3 scope boundary (no core data processing / agent logic yet).
"""

from __future__ import annotations

import logging
import logging.config
from typing import Any

from pythonjsonlogger import jsonlogger

from autoclean.config.settings import get_settings


class AutoCleanJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that always includes level, logger name, and timestamp.

    Note: earlier project environments needed a `type: ignore` here because
    `python-json-logger` shipped no type stubs; this environment's installed
    version resolves cleanly under mypy, so no ignore is needed. If a future
    environment reintroduces the stub gap, mypy will report it plainly
    (`import-untyped`) rather than silently -- re-add a scoped
    `# type: ignore[import-untyped]` on the `from pythonjsonlogger import
    jsonlogger` line above if that happens, not a blanket ignore here.
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
        if not log_record.get("timestamp"):
            log_record["timestamp"] = self.formatTime(record, self.datefmt)


def build_logging_config(log_level: str) -> dict[str, Any]:
    """Return a `logging.config.dictConfig`-compatible configuration dict."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": AutoCleanJsonFormatter,
                "format": "%(timestamp)s %(level)s %(logger)s %(message)s",
            },
            "console": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": log_level,
            },
            "file_json": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": "logs/autoclean.log",
                "maxBytes": 5_242_880,  # 5 MB
                "backupCount": 5,
                "level": log_level,
            },
        },
        "root": {
            "handlers": ["console", "file_json"],
            "level": log_level,
        },
        "loggers": {
            # Keep third-party libraries quieter than our own application logs.
            "urllib3": {"level": "WARNING", "propagate": True},
            "httpx": {"level": "WARNING", "propagate": True},
        },
    }


def configure_logging() -> None:
    """Configure application-wide logging from Settings. Call once at startup."""
    import os

    os.makedirs("logs", exist_ok=True)
    settings = get_settings()
    logging.config.dictConfig(build_logging_config(settings.log_level))
    logging.getLogger(__name__).info(
        "Logging configured", extra={"environment": settings.environment}
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience accessor so call sites can write `get_logger(__name__)`."""
    return logging.getLogger(name)
