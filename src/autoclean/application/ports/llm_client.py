"""Port interface for LLM-based explanation, implemented by the Infrastructure layer.

Design decision (Phase 2, Section 12, Adapter pattern): only the Decision &
Reporting Agent's use cases may depend on this ABC. Neither the Analysis
Agent nor the Evaluation Agent import from `infrastructure/llm/` anywhere in
this codebase -- that is the concrete, checkable form of the "LLM never
computes" rule (see `infrastructure/llm/__init__.py`).

Phase 5 note: the concrete implementation wired in by default this phase is
`infrastructure/llm/template_llm_client.py`, an explicitly TEMPORARY,
deterministic, non-LLM stand-in (string templates over real computed
numbers -- no fabrication, just no actual language model yet). The real
Ollama-backed implementation is Phase 7 work. Both are equally valid
`ILLMClient` implementations from this port's point of view.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ILLMClient(ABC):
    """Generates a natural-language explanation from already-computed evidence.

    Implementations MUST treat `context` as read-only evidence to describe,
    never as something to recompute or override (NFR-1).
    """

    @abstractmethod
    def explain(self, context: dict[str, Any]) -> str:
        """Return a natural-language explanation grounded in `context`.

        Args:
            context: A plain dict containing, at minimum, the recommended
                strategy's name/description, its EvaluationScore (as a
                dict, via `EvaluationScore.as_dict()`), and the scores of
                any alternative strategies being compared against. Every
                number in the returned explanation must trace back to a
                value present in `context` -- implementations must not
                invent scores, statistics, or claims not derivable from it.
        """
        raise NotImplementedError
