"""Shared LangGraph workflow state (Phase 2, Section 6).

A TypedDict, not a class with methods -- LangGraph nodes return partial
dicts that get merged into this state by the graph runtime, which is the
`TypedDict` usage pattern LangGraph is built around. `total=False` because
most fields don't exist yet when the graph starts (they're populated as
each node runs) and LangGraph merges partial updates, not full replacements.
"""

from __future__ import annotations

from typing import Any, TypedDict

from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.domain.entities.data_issue import DataIssue
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.validation_report import ValidationReport


class WorkflowState(TypedDict, total=False):
    # Set at workflow start
    experiment_id: str
    dataset_path: str

    # Written by AnalysisAgent
    dataset_profile: DatasetProfile
    detected_issues: list[DataIssue]
    candidate_strategies: list[CleaningStrategy]

    # Written by EvaluationAgent
    strategy_scores: dict[str, dict[str, float]]  # strategy_id -> EvaluationScore.as_dict()
    ranked_strategy_ids: list[str]

    # Written by DecisionReportingAgent (decision/explanation phase)
    recommended_strategy_id: str
    explanation_text: str
    explanation_consistency_warnings: list[str]
    rejected_strategy_ids: list[str]

    # Written by / for the human approval interrupt
    human_decision: str  # "approved" | "rejected"
    decided_by: str
    decided_at: str

    # Written by execution/validation/reporting nodes (Phase 8: real logic)
    approved_strategy_id: str
    cleaned_dataset_path: str
    validation_passed: bool
    validation_report: ValidationReport
    executive_report_path: str | None
    reproducible_script_path: str | None

    # Cross-cutting
    audit_log_entries: list[dict[str, Any]]
    current_node: str
    error: str
