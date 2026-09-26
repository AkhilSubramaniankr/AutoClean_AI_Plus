"""Thin LangGraph agent adapters. Translate WorkflowState <-> use case calls
only; contain no business logic themselves. Implemented in Phase 5.

AnalysisAgent      -- no IMetricsEngine/ILLMClient dependency
EvaluationAgent    -- no ILLMClient dependency (architecturally enforced:
                      inspect EvaluationAgent.__init__'s signature yourself)
DecisionReportingAgent -- the only agent depending on ILLMClient (via
                      ExplainRecommendationUseCase)
"""

from autoclean.agents.analysis_agent import AnalysisAgent
from autoclean.agents.decision_reporting_agent import DecisionReportingAgent
from autoclean.agents.evaluation_agent import EvaluationAgent

__all__ = ["AnalysisAgent", "DecisionReportingAgent", "EvaluationAgent"]
