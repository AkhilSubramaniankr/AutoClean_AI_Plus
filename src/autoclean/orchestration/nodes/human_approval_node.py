"""human_approval_node: the LangGraph interrupt point (Phase 1 FR-9).

This function body does almost nothing on purpose -- the actual "pause and
wait for a human" behavior comes entirely from `graph_builder.py` compiling
the graph with `interrupt_before=["human_approval"]`. This function only
runs *after* the graph is resumed (i.e., after a human decision has already
been written into state via `graph.update_state`), so all it needs to do is
record that the approval step happened and pass state through unchanged.
"""

from __future__ import annotations

from typing import Any

import logging
import uuid
from datetime import UTC, datetime

from autoclean.orchestration.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


def human_approval_node(state: WorkflowState) -> dict[str, Any]:
    decision = state.get("human_decision")
    decided_at = datetime.now(UTC).isoformat()
    audit_entry = {
        "id": str(uuid.uuid4()),
        "event_type": "human_approval_step_resumed",
        "actor": f"human:{state.get('decided_by', 'unknown')}",
        "timestamp": decided_at,
        "payload": {"human_decision": decision, "strategy_id": state.get("recommended_strategy_id")},
    }
    logger.info("human_approval_node resumed", extra={"human_decision": decision})
    return {
        "current_node": "human_approval",
        "decided_at": decided_at,
        "audit_log_entries": [*state.get("audit_log_entries", []), audit_entry],
    }
