"""FallbackLLMClient: Decorator pattern (new to this project's pattern list
in Phase 7) wrapping a primary ILLMClient with a fallback ILLMClient.

Rationale: a real Ollama server is an external process this application
doesn't control -- it may not be running, the configured model may not be
pulled yet, or the request may time out. Per this project's established
"never crash, degrade honestly and visibly" philosophy (already used for
fairness_metrics.py and downstream_ml_metrics.py's neutral-0.5 fallbacks in
Phase 6), a failed real-LLM call should not crash the whole workflow --
it should fall back to the deterministic TemplateLLMClient and SAY SO in
the returned text, so a human reviewer is never silently shown a
lower-quality explanation without knowing it happened.
"""

from __future__ import annotations

import logging
from typing import Any

from autoclean.application.ports.llm_client import ILLMClient

logger = logging.getLogger(__name__)

_FALLBACK_NOTICE = (
    "[Note: the local LLM was unavailable, so this explanation was generated "
    "from a deterministic template instead of a language model. All numbers "
    "below are still real, computed values -- only the prose is templated.]\n\n"
)


class FallbackLLMClient(ILLMClient):
    """Tries `primary.explain()`; on ANY exception, logs a warning and
    returns `fallback.explain()` with a visible notice prepended.
    """

    def __init__(self, primary: ILLMClient, fallback: ILLMClient) -> None:
        self._primary = primary
        self._fallback = fallback

    def explain(self, context: dict[str, Any]) -> str:
        try:
            return self._primary.explain(context)
        except Exception as exc:  # noqa: BLE001 -- intentionally broad: any primary failure should fall back
            logger.warning(
                "Primary ILLMClient failed; falling back to secondary implementation",
                extra={"error": str(exc), "primary_type": type(self._primary).__name__},
            )
            return _FALLBACK_NOTICE + self._fallback.explain(context)
