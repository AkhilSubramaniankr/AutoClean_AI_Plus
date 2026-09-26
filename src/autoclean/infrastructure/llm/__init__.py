"""LLM client adapter implementing the ILLMClient port.

CRITICAL ARCHITECTURAL RULE: the Evaluation Agent must NEVER import from
this package. Only the Decision & Reporting Agent (via ExplainRecommendationUseCase)
may depend on ILLMClient.

Phase 7 (REAL, default): OllamaLLMClient (real Ollama server via
langchain-ollama's ChatOllama), wrapped in FallbackLLMClient (Decorator
pattern, new this phase) which falls back to TemplateLLMClient if the real
LLM call fails for any reason (server not running, model not pulled,
timeout, etc.) -- never crashes the workflow over an external service being
unavailable, and always says so visibly in the returned text.

Phase 5 (TEMPORARY, kept as fallback + fast test double): TemplateLLMClient.

Phase 7 also adds explanation_consistency_checker.py: flags numeric claims
in ANY explanation (real or templated) that don't trace back to a real
computed score -- the concrete implementation of the anti-fabrication
safeguard named in Phase 1's Risk table.
"""
