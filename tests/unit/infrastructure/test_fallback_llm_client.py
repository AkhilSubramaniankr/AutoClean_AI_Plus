"""Unit tests for FallbackLLMClient (Phase 7, Decorator pattern)."""

from __future__ import annotations

from typing import Any

import pytest

from autoclean.application.ports.llm_client import ILLMClient
from autoclean.infrastructure.llm.fallback_llm_client import FallbackLLMClient

pytestmark = pytest.mark.unit


class _WorkingLLMClient(ILLMClient):
    def __init__(self, response: str = "primary response") -> None:
        self.response = response
        self.was_called = False

    def explain(self, context: dict[str, Any]) -> str:
        self.was_called = True
        return self.response


class _BrokenLLMClient(ILLMClient):
    def explain(self, context: dict[str, Any]) -> str:
        raise ConnectionError("Ollama server not reachable")


class TestFallbackLLMClient:
    def test_uses_primary_when_it_succeeds(self) -> None:
        primary = _WorkingLLMClient("real explanation")
        fallback = _WorkingLLMClient("template explanation")
        client = FallbackLLMClient(primary=primary, fallback=fallback)

        result = client.explain({})
        assert result == "real explanation"
        assert fallback.was_called is False

    def test_falls_back_when_primary_raises(self) -> None:
        primary = _BrokenLLMClient()
        fallback = _WorkingLLMClient("template explanation")
        client = FallbackLLMClient(primary=primary, fallback=fallback)

        result = client.explain({})
        assert fallback.was_called is True
        assert "template explanation" in result

    def test_fallback_result_visibly_discloses_that_fallback_occurred(self) -> None:
        """Transparency requirement: a human reading the explanation must be
        able to tell it did NOT come from the real LLM.
        """
        client = FallbackLLMClient(primary=_BrokenLLMClient(), fallback=_WorkingLLMClient("text"))
        result = client.explain({})
        assert "unavailable" in result.lower() or "note" in result.lower()

    def test_does_not_swallow_a_fallback_failure(self) -> None:
        """If BOTH primary and fallback fail, the exception should propagate
        -- silently returning nothing would be worse than a clear crash.
        """
        client = FallbackLLMClient(primary=_BrokenLLMClient(), fallback=_BrokenLLMClient())
        with pytest.raises(ConnectionError):
            client.explain({})
