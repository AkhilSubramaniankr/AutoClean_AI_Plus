"""OllamaLLMClient: the real ILLMClient implementation, replacing Phase 5's
TemplateLLMClient. Uses langchain-ollama's `ChatOllama`, per the Phase 3
Addendum LLM provider revision (Anthropic -> Ollama).

Design decision (testability): the constructor accepts an optional
`chat_model` parameter (any object exposing `.invoke(messages) -> message
with .content`). When omitted, a real `ChatOllama` is constructed from
`Settings`. This lets unit tests inject a fake chat model with a canned
response and verify PROMPT CONSTRUCTION and GROUNDING logic without a live
Ollama server -- while `scripts/run_workflow_cli.py` and any future
Streamlit usage (Phase 9) get a real one by default. This is the same
Dependency Injection principle used everywhere else in this project
(Phase 2, Section 12), applied to a concrete Infrastructure class rather
than only at the Port level.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from autoclean.application.ports.llm_client import ILLMClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are explaining a data-cleaning strategy recommendation to a human reviewer.

STRICT RULES, follow exactly:
1. You MUST use only the numeric scores given to you below. Do not invent,
   estimate, round differently, or introduce any statistic not explicitly provided.
2. Explain, in plain language, why the recommended strategy was chosen over the alternatives.
3. Explicitly discuss at least one trade-off (a dimension where an alternative
   scores better than the recommendation, if any alternative does).
4. State the confidence value (em_confidence) plainly, in your own words
   (e.g. "moderate confidence" for a mid-range value), without inventing a
   different number for it.
5. Keep your answer to 4-6 sentences. Do not use markdown formatting.
"""


class SupportsInvoke(Protocol):
    """Structural type for whatever chat-model object is injected -- avoids
    hard-coupling this module's type hints to langchain-ollama's concrete
    ChatOllama class, so a test fake satisfies the same interface trivially.
    The parameter is positional-only (the `/`) so structural matching
    doesn't require the injected object's parameter to be named "messages"
    specifically -- ChatOllama's own `invoke` names it "input".
    """

    def invoke(self, messages: list[BaseMessage], /) -> Any: ...


class OllamaLLMClient(ILLMClient):
    """Real LLM-backed explanation generation via a local Ollama server."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        chat_model: SupportsInvoke | None = None,
    ) -> None:
        if chat_model is not None:
            self._chat_model: SupportsInvoke = chat_model
        else:
            # Imported lazily so this module (and its tests, via the
            # chat_model injection path above) doesn't require
            # langchain-ollama / a reachable Ollama server just to import.
            from langchain_ollama import ChatOllama

            from autoclean.config.settings import get_settings

            settings = get_settings()
            self._chat_model = ChatOllama(
                model=model or settings.llm_model,
                base_url=base_url or settings.llm_base_url,
                temperature=temperature if temperature is not None else settings.llm_temperature,
            )

    def explain(self, context: dict[str, Any]) -> str:
        user_message = self._build_user_message(context)
        messages: list[BaseMessage] = [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=user_message)]

        response = self._chat_model.invoke(messages)
        explanation = str(response.content).strip()

        logger.info(
            "OllamaLLMClient generated explanation",
            extra={
                "strategy_name": context.get("recommended_strategy_name"),
                "explanation_length": len(explanation),
            },
        )
        return explanation

    @staticmethod
    def _build_user_message(context: dict[str, Any]) -> str:
        lines = [
            f"Recommended strategy: {context['recommended_strategy_name']}",
            f"Description: {context['recommended_strategy_description']}",
            f"Recommended strategy scores: {context['recommended_score']}",
        ]
        alternatives = context.get("alternatives", [])
        if alternatives:
            lines.append("Alternative strategies considered:")
            for alt in alternatives:
                lines.append(f"  - {alt['name']}: {alt['score']}")
        else:
            lines.append("No alternative strategies were available for comparison.")
        return "\n".join(lines)
