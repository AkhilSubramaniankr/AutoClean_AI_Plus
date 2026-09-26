"""explanation_panel.py: renders the Decision & Reporting Agent's
explanation, plus any Phase 7 consistency warnings, in the Streamlit UI.

Kept as a small, focused rendering function (not a page) so it can be
reused identically on the Review & Approve page and, if useful later, on
the Experiment History page for past explanations.
"""

from __future__ import annotations

import streamlit as st


def render_explanation_panel(explanation_text: str, consistency_warnings: list[str]) -> None:
    st.markdown("#### Why this strategy?")
    st.markdown(explanation_text)

    if consistency_warnings:
        st.warning(
            "⚠ The automated consistency check flagged possible issues with this "
            "explanation (a number that doesn't match a real computed score):"
        )
        for warning in consistency_warnings:
            st.markdown(f"- {warning}")
