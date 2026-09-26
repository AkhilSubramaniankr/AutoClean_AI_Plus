"""Headless tests for Page 1 (Upload & Profile), using Streamlit's
`AppTest` framework (real, in `streamlit.testing.v1`, ships with
Streamlit >= 1.28).

HONEST LIMITATION, documented here and in the Phase 9 deliverable: AppTest
has no supported way to simulate a `file_uploader` widget's file selection
(the widget renders as an opaque `UnknownElement` with no `set_value`-style
method). This means the upload -> analyze button click sequence cannot be
driven end-to-end through AppTest. What IS tested here is real: the page
renders without error before and after a file is "present" in
`st.session_state` (seeded directly, bypassing only the uploader widget
itself, not the page's own rendering logic), and the empty/initial state
renders correctly. The full upload -> real graph execution path is
covered by scripts/run_workflow_cli.py's manual verification (see
docs/VERIFICATION_GUIDE.md) and by the Phase 5/8 integration tests, which
exercise the same underlying graph directly.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

pytestmark = pytest.mark.unit

_PAGE_PATH = "src/autoclean/presentation/pages/1_Upload_and_Profile.py"
_TIMEOUT = 30  # default AppTest timeout (3s) is too short given this page's real import chain


class TestUploadAndProfilePage:
    def test_renders_without_error_before_any_upload(self) -> None:
        at = AppTest.from_file(_PAGE_PATH)
        at.run(timeout=_TIMEOUT)
        assert not at.exception

    def test_shows_a_file_uploader_widget(self) -> None:
        at = AppTest.from_file(_PAGE_PATH)
        at.run(timeout=_TIMEOUT)
        assert len(at.get("file_uploader")) == 1

    def test_renders_profile_metrics_when_a_result_is_already_in_session_state(self) -> None:
        """Simulates the post-analysis state directly via session_state
        (the only way to test this page's OWN rendering logic without a
        live file_uploader interaction) using REAL DatasetProfile/DataIssue
        objects from the real Phase 4 engine, not fabricated data.
        """
        import pandas as pd

        from autoclean.infrastructure.data_processing.issue_detector import IssueDetector
        from autoclean.infrastructure.data_processing.profiler import DatasetProfiler
        from autoclean.infrastructure.data_processing.strategy_generator import StrategyGenerator

        df = pd.DataFrame({"age": [25, 30, None, 40], "city": ["NY", "LA", "NY", "SF"]})
        profile = DatasetProfiler().profile(df)
        issues = IssueDetector().detect(df, profile)
        strategies = StrategyGenerator().generate(issues)

        at = AppTest.from_file(_PAGE_PATH)
        at.session_state["dataset_name"] = "test.csv"
        at.session_state["latest_result"] = {
            "dataset_profile": profile, "detected_issues": issues, "candidate_strategies": strategies,
        }
        at.run(timeout=_TIMEOUT)

        assert not at.exception
        metric_values = [m.value for m in at.get("metric")]
        assert str(profile.row_count) in metric_values
