"""graph_builder: builds and compiles the AutoClean AI+ LangGraph workflow
(Phase 2, Section 4) and exposes it as a Facade (Phase 2, Section 12) so the
Presentation layer (Phase 9) never has to know about LangGraph's node/edge
wiring directly.

Graph shape (Phase 2 diagram, unchanged since Phase 5):
    START -> analysis_agent -> evaluation_agent -> decision_reporting_agent
    decision_reporting_agent --[error: all rejected]--> END
    decision_reporting_agent --[else]--> human_approval  (INTERRUPT HERE)
    human_approval --[approved]--> execution_node -> validation_node
        -> reporting_node -> END
    human_approval --[rejected]--> decision_reporting_agent  (loop back)

PHASE 8 UPDATE: execution_node/validation_node/reporting_node are now real,
dependency-injected classes (ExecutionNode/ValidationNode/ReportingNode),
not the Phase 5 module-level stub functions -- `build_graph()`'s signature
changed accordingly. Flagged per this project's convention for any changed
call shape.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from autoclean.agents.analysis_agent import AnalysisAgent
from autoclean.agents.decision_reporting_agent import DecisionReportingAgent
from autoclean.agents.evaluation_agent import EvaluationAgent
from autoclean.orchestration.nodes.execution_node import ExecutionNode
from autoclean.orchestration.nodes.human_approval_node import human_approval_node
from autoclean.orchestration.nodes.reporting_node import ReportingNode
from autoclean.orchestration.nodes.validation_node import ValidationNode
from autoclean.orchestration.workflow_state import WorkflowState


def _route_after_decision(state: WorkflowState) -> str:
    return END if state.get("error") else "human_approval"


def _route_after_human_approval(state: WorkflowState) -> str:
    return "execution_node" if state.get("human_decision") == "approved" else "decision_reporting_agent"


def build_graph(
    analysis_agent: AnalysisAgent,
    evaluation_agent: EvaluationAgent,
    decision_reporting_agent: DecisionReportingAgent,
    execution_node: ExecutionNode,
    validation_node: ValidationNode,
    reporting_node: ReportingNode,
    checkpointer: BaseCheckpointSaver[Any],
) -> Any:
    """Build and compile the workflow graph.

    A `checkpointer` is REQUIRED (not optional/defaulted) because LangGraph's
    `interrupt_before` mechanism has no meaning without one -- there would be
    nothing to resume from. Callers pass `MemorySaver()` for a single-process
    run (Phase 5's demo CLI, tests) or a persistent checkpointer if one is
    added in a later phase.
    """
    builder = StateGraph(WorkflowState)

    builder.add_node("analysis_agent", analysis_agent.run)
    builder.add_node("evaluation_agent", evaluation_agent.run)
    builder.add_node("decision_reporting_agent", decision_reporting_agent.run)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("execution_node", execution_node.run)
    builder.add_node("validation_node", validation_node.run)
    builder.add_node("reporting_node", reporting_node.run)

    builder.add_edge(START, "analysis_agent")
    builder.add_edge("analysis_agent", "evaluation_agent")
    builder.add_edge("evaluation_agent", "decision_reporting_agent")
    builder.add_conditional_edges(
        "decision_reporting_agent",
        _route_after_decision,
        {"human_approval": "human_approval", END: END},
    )
    builder.add_conditional_edges(
        "human_approval",
        _route_after_human_approval,
        {"execution_node": "execution_node", "decision_reporting_agent": "decision_reporting_agent"},
    )
    builder.add_edge("execution_node", "validation_node")
    builder.add_edge("validation_node", "reporting_node")
    builder.add_edge("reporting_node", END)

    return builder.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])
