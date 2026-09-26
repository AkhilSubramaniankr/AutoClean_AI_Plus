"""Headless tests for Page 3 (Review Explanation & Approve), using
`AppTest` with a MOCKED `WorkflowSession` (see this module's docstring in
test_page_upload_and_profile.py for why file_uploader-driven end-to-end
testing isn't possible via AppTest).

Mocking `get_workflow_session()` here is not a compromise -- it is the
correct unit-testing boundary: this page's own job is to wire button
clicks to the right backend calls (approve_use_case.execute,
graph.update_state, graph.invoke) and update session_state/rerun
correctly. Whether the REAL graph correctly executes/validates/reports is
already verified directly, without any Streamlit involved, by
tests/integration/test_workflow.py (Phase 5/8). Testing both at their
correct boundary is more rigorous than trying to force one enormous
UI-driven end-to-end test through a framework limitation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import autoclean.presentation.workflow_session as workflow_session_module
from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
from autoclean.infrastructure.data_processing.strategy_generator import StrategyGenerator
from autoclean.infrastructure.metrics.placeholder_metrics_engine import PlaceholderMetricsEngine

pytestmark = pytest.mark.unit

_PAGE_PATH = "src/autoclean/presentation/pages/3_Review_and_Approve.py"
_TIMEOUT = 30


def _real_pending_result() -> dict:
    """Builds a REAL result dict using the actual Phase 4/6 engine (not
    fabricated), representing the state right after DecisionReportingAgent
    has produced a recommendation and the graph has paused at the interrupt.
    """
    df = pd.DataFrame({"age": [25, 30, None, 40, 200], "city": ["NY", "LA", "NY", "SF", "NY"]})
    profile = DatasetProfiler().profile(df)
    issues = IssueDetector().detect(df, profile)
    strategies = StrategyGenerator().generate(issues)
    scores = {s.strategy_id: PlaceholderMetricsEngine().score(s, profile).as_dict() for s in strategies}
    ranked_ids = sorted(scores, key=lambda sid: sum(scores[sid].values()), reverse=True)
    return {
        "candidate_strategies": strategies, "strategy_scores": scores, "ranked_strategy_ids": ranked_ids,
        "recommended_strategy_id": ranked_ids[0], "explanation_text": "This is a real explanation.",
        "explanation_consistency_warnings": [], "audit_log_entries": [], "current_node": "decision_reporting_agent",
    }


@pytest.fixture
def fake_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = MagicMock()
    monkeypatch.setattr(workflow_session_module, "get_workflow_session", lambda: fake)
    return fake


class TestReviewAndApprovePageNoResult:
    def test_shows_warning_when_nothing_analyzed_yet(self, fake_session: MagicMock) -> None:
        at = AppTest.from_file(_PAGE_PATH)
        at.run(timeout=_TIMEOUT)
        assert not at.exception
        assert any("analyzed yet" in w.value for w in at.warning)


class TestReviewAndApprovePagePendingDecision:
    def test_renders_the_real_explanation_text(self, fake_session: MagicMock) -> None:
        result = _real_pending_result()
        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["latest_result"] = result
        at.session_state["experiment_id"] = "e1"
        at.session_state["config"] = {"configurable": {"thread_id": "e1"}}
        at.run(timeout=_TIMEOUT)
        assert not at.exception
        assert any("real explanation" in m.value for m in at.markdown)

    def test_approve_button_calls_approve_use_case_and_resumes_the_graph(self, fake_session: MagicMock) -> None:
        result = _real_pending_result()
        fake_session.graph.invoke.return_value = {**result, "current_node": "decision_reporting_agent"}

        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["latest_result"] = result
        at.session_state["experiment_id"] = "e1"
        at.session_state["config"] = {"configurable": {"thread_id": "e1"}}
        at.session_state["persisted_audit_count"] = 0
        at.run(timeout=_TIMEOUT)

        approve_button = next(b for b in at.button if "Approve" in b.label)
        approve_button.click().run(timeout=_TIMEOUT)

        assert not at.exception
        fake_session.approve_use_case.execute.assert_called_once()
        call_kwargs = fake_session.approve_use_case.execute.call_args.kwargs
        assert call_kwargs["strategy_id"] == result["recommended_strategy_id"]
        fake_session.graph.update_state.assert_called_once_with(
            {"configurable": {"thread_id": "e1"}}, {"human_decision": "approved", "decided_by": "analyst"}
        )
        fake_session.graph.invoke.assert_called_once_with(None, {"configurable": {"thread_id": "e1"}})

    def test_reject_button_calls_approve_use_case_with_rejected_and_resumes(self, fake_session: MagicMock) -> None:
        result = _real_pending_result()
        fake_session.graph.invoke.return_value = {**result, "recommended_strategy_id": result["ranked_strategy_ids"][1]}

        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["latest_result"] = result
        at.session_state["experiment_id"] = "e1"
        at.session_state["config"] = {"configurable": {"thread_id": "e1"}}
        at.session_state["persisted_audit_count"] = 0
        at.run(timeout=_TIMEOUT)

        reject_button = next(b for b in at.button if "Reject" in b.label)
        reject_button.click().run(timeout=_TIMEOUT)

        assert not at.exception
        from autoclean.domain.entities.decision import DecisionType

        call_kwargs = fake_session.approve_use_case.execute.call_args.kwargs
        assert call_kwargs["decision_type"] == DecisionType.REJECTED
        fake_session.graph.update_state.assert_called_once_with(
            {"configurable": {"thread_id": "e1"}}, {"human_decision": "rejected", "decided_by": "analyst"}
        )


class TestReviewAndApprovePageCompleted:
    def test_shows_download_buttons_when_reporting_node_reached(
        self, fake_session: MagicMock, tmp_path
    ) -> None:
        cleaned_csv = tmp_path / "cleaned.csv"
        cleaned_csv.write_text("a,b\n1,2\n")
        report_md = tmp_path / "report.md"
        report_md.write_text("# Report\n\nSome content.")
        script_py = tmp_path / "script.py"
        script_py.write_text("print('hello')")

        result = {
            "current_node": "reporting_node", "validation_report": None,
            "cleaned_dataset_path": str(cleaned_csv), "executive_report_path": str(report_md),
            "reproducible_script_path": str(script_py),
        }
        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["latest_result"] = result
        at.session_state["experiment_id"] = "e1"
        at.run(timeout=_TIMEOUT)

        assert not at.exception
        assert any("complete" in s.value for s in at.success)
        assert len(at.get("download_button")) == 3


class TestReviewAndApprovePageAllRejected:
    def test_shows_error_message_when_all_strategies_rejected(self, fake_session: MagicMock) -> None:
        result = {"error": "All candidate strategies have been rejected by the human reviewer."}
        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["latest_result"] = result
        at.session_state["experiment_id"] = "e1"
        at.run(timeout=_TIMEOUT)

        assert not at.exception
        assert any("rejected" in e.value for e in at.error)
