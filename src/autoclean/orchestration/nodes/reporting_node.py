"""ReportingNode: real report + script generation (Phase 8, replaces the
Phase 5 stub). Reads the full accumulated WorkflowState and produces a real
executive report (Markdown, via ReportGenerator) and a real reproducible
script (via ScriptExporter) -- both from actual computed values already in
state, no LLM involvement in the generation step itself.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from autoclean.application.use_cases.generate_report import GenerateReportUseCase
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
from autoclean.orchestration.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class ReportingNode:
    """LangGraph node: full experiment state -> executive report + reproducible script."""

    def __init__(
        self,
        generate_report_use_case: GenerateReportUseCase,
        report_dir: str = "data/reports",
        script_dir: str = "data/scripts",
    ) -> None:
        self._generate_report_use_case = generate_report_use_case
        self._report_dir = report_dir
        self._script_dir = script_dir
        self._profiler = DatasetProfiler()

    def run(self, state: WorkflowState) -> dict[str, Any]:
        experiment_id = state["experiment_id"]
        approved_id = state["approved_strategy_id"]
        strategies_by_id = {s.strategy_id: s for s in state["candidate_strategies"]}
        strategy = strategies_by_id[approved_id]
        score = EvaluationScore(**state["strategy_scores"][approved_id])

        alternatives = [
            {"name": strategies_by_id[sid].name, "score": state["strategy_scores"][sid]}
            for sid in state.get("ranked_strategy_ids", [])
            if sid != approved_id and sid in strategies_by_id
        ]

        cleaned_profile = self._profiler.profile(
            # Re-profiling here (rather than reusing ValidationNode's result)
            # keeps ReportingNode independently correct even if it ever runs
            # without ValidationNode having run first in some future graph
            # variation -- a small recomputation, not a meaningful cost.
            self._load_cleaned_df(state)
        )

        report_context: dict[str, Any] = {
            "experiment_id": experiment_id,
            "dataset_name": Path(state["dataset_path"]).name,
            "generated_at": datetime.now(UTC).isoformat(),
            "original_profile": state["dataset_profile"],
            "cleaned_profile": cleaned_profile,
            "strategy": strategy,
            "score": score,
            "alternatives": alternatives,
            "explanation_text": state.get("explanation_text", ""),
            "consistency_warnings": state.get("explanation_consistency_warnings", []),
            "decided_by": state.get("decided_by", "unknown"),
            "decided_at": state.get("decided_at", "unknown"),
            "validation": state.get("validation_report") or self._fallback_validation_dict(state),
        }

        report_path, script_path = self._generate_report_use_case.execute(
            report_context,
            strategy,
            f"{self._report_dir}/{experiment_id}_report.md",
            f"{self._script_dir}/{experiment_id}_reproduce.py",
        )

        audit_entry = {
            "id": str(uuid.uuid4()),
            "event_type": "report_generated",
            "actor": "ReportingNode",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {"report_path": report_path, "script_path": script_path},
        }
        logger.info("ReportingNode.run complete", extra={"report_path": report_path, "script_path": script_path})

        return {
            "executive_report_path": report_path,
            "reproducible_script_path": script_path,
            "current_node": "reporting_node",
            "audit_log_entries": [*state.get("audit_log_entries", []), audit_entry],
        }

    @staticmethod
    def _load_cleaned_df(state: WorkflowState) -> pd.DataFrame:
        return pd.read_csv(state["cleaned_dataset_path"])

    @staticmethod
    def _fallback_validation_dict(state: WorkflowState) -> dict[str, Any]:
        """Defensive fallback if ReportingNode somehow runs without a prior
        ValidationNode result in state (e.g. a future graph variation) --
        the report should degrade gracefully, not crash on a missing key.
        """
        return {
            "schema_consistent": True,
            "quality_threshold_met": state.get("validation_passed", False),
            "quality_score": 0.0,
            "quality_threshold": 0.5,
            "remaining_issue_count": 0,
        }
