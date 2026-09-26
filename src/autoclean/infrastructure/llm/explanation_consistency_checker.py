"""explanation_consistency_checker.py: flags numeric claims in an LLM-generated
explanation that don't trace back to a real computed score.

🟩 ORIGINAL. Directly implements the mitigation named in Phase 1's Risk
table ("automated consistency checks can flag numeric mismatches between
the explanation text and the source scores") and is the concrete answer to
this project's core trust question: once a real LLM is writing prose (this
phase replaces TemplateLLMClient with a real Ollama-backed adapter), how do
we know it didn't quietly invent a number?

Method: extract every decimal number that LOOKS like a score (a float
between 0.0 and 1.0, since every objective and em_confidence are already
constrained to that range by EvaluationScore's own validation) from the
explanation text, and check each one against the set of real score values
actually present in the grounding context (the recommended strategy's score
plus every alternative's score), within a small rounding tolerance. Any
extracted number that matches nothing in that set is flagged.

Deliberate scope limits, stated plainly:
- This is a heuristic grounded in this project's own score format (values
  in [0, 1], typically rendered to 2 decimal places), not a general-purpose
  fact-checker. It cannot catch a fabricated CLAIM that uses no numbers
  (e.g. an invented qualitative claim like "this strategy is used by most
  data scientists") -- only numeric grounding is checked.
- A false positive is possible if the LLM legitimately writes an unrelated
  number in [0, 1] that isn't a score (e.g. "roughly half the columns").
  This is why results are returned as a list of WARNINGS to review/log, not
  used to silently reject or rewrite the explanation.
"""

from __future__ import annotations

import re
from typing import Any

_SCORE_LIKE_NUMBER_PATTERN = re.compile(r"\b0\.\d{1,4}\b|\b1\.0{1,4}\b")
_ROUNDING_TOLERANCE = 0.015  # generous enough for "0.83" vs a true 0.826, still tight enough to catch invention


def _collect_real_scores(context: dict[str, Any]) -> set[float]:
    real_scores: set[float] = set()
    recommended_score = context.get("recommended_score", {})
    real_scores.update(float(v) for v in recommended_score.values())
    for alternative in context.get("alternatives", []):
        real_scores.update(float(v) for v in alternative.get("score", {}).values())
    return real_scores


def check_consistency(explanation_text: str, context: dict[str, Any]) -> list[str]:
    """Returns a list of human-readable warnings, empty if nothing looked
    suspicious. Never raises -- a checker that can crash the explanation
    pipeline over a regex edge case would be worse than not checking at all.
    """
    real_scores = _collect_real_scores(context)
    if not real_scores:
        return ["No real scores were found in context to check the explanation against."]

    warnings: list[str] = []
    for match in _SCORE_LIKE_NUMBER_PATTERN.finditer(explanation_text):
        if _is_part_of_a_range_descriptor(explanation_text, match.start(), match.end()):
            # e.g. "(0.0-1.0, higher is better)" is a range LABEL, not a
            # claimed score -- found as a real false positive while testing
            # this checker against TemplateLLMClient's own boilerplate text.
            continue
        try:
            candidate = float(match.group())
        except ValueError:
            continue
        if not any(abs(candidate - real) <= _ROUNDING_TOLERANCE for real in real_scores):
            warnings.append(
                f"Explanation contains the number {candidate!r}, which does not match any "
                f"real computed score within tolerance ({_ROUNDING_TOLERANCE}) -- possible fabrication."
            )
    return warnings


def _is_part_of_a_range_descriptor(text: str, start: int, end: int) -> bool:
    """True if the matched number is immediately adjacent to a hyphen
    joining it to another number (a "0.0-1.0"-style range label), on either
    side -- e.g. "(0.0-1.0, ...)" or "1.0-2.0".
    """
    before = text[max(0, start - 1) : start]
    after = text[end : end + 1]
    return before == "-" or after == "-"
