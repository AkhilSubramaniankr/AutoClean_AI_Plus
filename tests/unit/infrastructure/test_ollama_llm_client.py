"""Unit tests for OllamaLLMClient (Phase 7).

Uses a FAKE chat model injected via the constructor's `chat_model`
parameter -- these tests verify prompt construction and grounding logic,
NOT a live Ollama server (this sandboxed environment has no Ollama
installed; a genuine end-to-end round trip must be verified on a machine
that actually runs Ollama -- see docs/VERIFICATION_GUIDE.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from autoclean.infrastructure.llm.ollama_llm_client import OllamaLLMClient

pytestmark = pytest.mark.unit


@dataclass
class _FakeResponse:
    content: str


class _FakeChatModel:
    """Records the messages it was invoked with; returns a fixed response."""

    def __init__(self, response_text: str = "This is a fake LLM response.") -> None:
        self.response_text = response_text
        self.last_messages: list[BaseMessage] | None = None

    def invoke(self, messages: list[BaseMessage]) -> _FakeResponse:
        self.last_messages = messages
        return _FakeResponse(content=self.response_text)


_SAMPLE_CONTEXT: dict[str, Any] = {
    "recommended_strategy_name": "Conservative",
    "recommended_strategy_description": "Imputes and clips.",
    "recommended_score": {"data_quality_score": 0.81, "computational_cost_score": 0.98},
    "alternatives": [{"name": "Baseline", "description": "Minimal.", "score": {"data_quality_score": 0.62}}],
}


class TestOllamaLLMClient:
    def test_returns_the_chat_models_response_content(self) -> None:
        fake_model = _FakeChatModel(response_text="Real explanation text.")
        client = OllamaLLMClient(chat_model=fake_model)
        result = client.explain(_SAMPLE_CONTEXT)
        assert result == "Real explanation text."

    def test_sends_a_system_message_with_grounding_rules(self) -> None:
        fake_model = _FakeChatModel()
        client = OllamaLLMClient(chat_model=fake_model)
        client.explain(_SAMPLE_CONTEXT)

        assert fake_model.last_messages is not None
        system_messages = [m for m in fake_model.last_messages if isinstance(m, SystemMessage)]
        assert len(system_messages) == 1
        assert "only the numeric scores" in system_messages[0].content

    def test_user_message_includes_real_scores_not_fabricated_ones(self) -> None:
        fake_model = _FakeChatModel()
        client = OllamaLLMClient(chat_model=fake_model)
        client.explain(_SAMPLE_CONTEXT)

        human_messages = [m for m in fake_model.last_messages if isinstance(m, HumanMessage)]
        assert len(human_messages) == 1
        user_text = human_messages[0].content
        assert "0.81" in user_text
        assert "0.98" in user_text
        assert "Conservative" in user_text
        assert "Baseline" in user_text  # the alternative is included for comparison

    def test_handles_no_alternatives_gracefully(self) -> None:
        fake_model = _FakeChatModel()
        client = OllamaLLMClient(chat_model=fake_model)
        context_no_alts = {**_SAMPLE_CONTEXT, "alternatives": []}
        client.explain(context_no_alts)  # must not raise

        human_messages = [m for m in fake_model.last_messages if isinstance(m, HumanMessage)]
        assert "No alternative strategies" in human_messages[0].content

    def test_strips_surrounding_whitespace_from_response(self) -> None:
        fake_model = _FakeChatModel(response_text="  \n  Some explanation.  \n")
        client = OllamaLLMClient(chat_model=fake_model)
        assert client.explain(_SAMPLE_CONTEXT) == "Some explanation."
