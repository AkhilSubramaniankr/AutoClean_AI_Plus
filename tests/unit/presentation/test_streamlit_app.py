"""Headless test for the main streamlit_app.py entry point (Phase 9)."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

pytestmark = pytest.mark.unit

_TIMEOUT = 30


class TestMainApp:
    def test_renders_without_error(self) -> None:
        at = AppTest.from_file("src/autoclean/presentation/streamlit_app.py")
        at.run(timeout=_TIMEOUT)
        assert not at.exception

    def test_shows_the_app_title(self) -> None:
        at = AppTest.from_file("src/autoclean/presentation/streamlit_app.py")
        at.run(timeout=_TIMEOUT)
        assert any("AutoClean AI+" in t.value for t in at.title)

    def test_links_to_all_four_workflow_pages(self) -> None:
        at = AppTest.from_file("src/autoclean/presentation/streamlit_app.py")
        at.run(timeout=_TIMEOUT)
        page_links = at.get("page_link")
        assert len(page_links) == 4
