"""Headless tests for Page 4 (Experiment History), using AppTest with a
mocked WorkflowSession's repository (a real SQLite round-trip is already
covered by tests/unit/infrastructure/test_experiment_repository.py; this
page's own job is just to render whatever the repository returns).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from streamlit.testing.v1 import AppTest

import autoclean.presentation.workflow_session as workflow_session_module
from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.dataset import DatasetProfile
from autoclean.domain.entities.experiment import Experiment, ExperimentStatus

pytestmark = pytest.mark.unit

_PAGE_PATH = "src/autoclean/presentation/pages/4_Experiment_History.py"
_TIMEOUT = 30


@pytest.fixture
def fake_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = MagicMock()
    monkeypatch.setattr(workflow_session_module, "get_workflow_session", lambda: fake)
    return fake


class TestExperimentHistoryPageEmpty:
    def test_shows_info_message_when_no_experiments_exist(self, fake_session: MagicMock) -> None:
        fake_session.repository.list_experiments.return_value = []
        at = AppTest.from_file(_PAGE_PATH)
        at.run(timeout=_TIMEOUT)
        assert not at.exception
        assert any("No experiments yet" in i.value for i in at.info)


class TestExperimentHistoryPageWithData:
    def _real_experiment(self) -> Experiment:
        profile = DatasetProfile(row_count=10, column_count=2, missing_value_pct=5.0, duplicate_row_count=1, outlier_count=0)
        return Experiment(
            id="exp-1", dataset_name="sample.csv", dataset_hash="h1",
            status=ExperimentStatus.COMPLETED, dataset_profile=profile,
        )

    def test_renders_real_experiment_metrics(self, fake_session: MagicMock) -> None:
        experiment = self._real_experiment()
        fake_session.repository.list_experiments.return_value = [experiment]
        fake_session.repository.get_audit_trail.return_value = [
            AuditEvent(id="a1", experiment_id="exp-1", event_type="dataset_profiled", actor="AnalysisAgent", timestamp=datetime.now(UTC)),
        ]

        at = AppTest.from_file(_PAGE_PATH)
        at.run(timeout=_TIMEOUT)

        assert not at.exception
        metric_values = [m.value for m in at.get("metric")]
        assert "completed" in metric_values
        assert "10" in metric_values  # real row_count from the real profile
        assert any("dataset_profiled" in m.value for m in at.markdown)
