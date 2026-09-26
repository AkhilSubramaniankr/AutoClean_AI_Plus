"""streamlit_app.py: AutoClean AI+ main entry point / home page.

Run with: streamlit run src/autoclean/presentation/streamlit_app.py

This file is deliberately thin -- it only sets page config, shows an
overview, and links to the four workflow pages (Phase 2, Section 3:
upload & profile, compare strategies, review & approve, experiment
history). All actual workflow logic lives in the pages/ and the shared
workflow_session.py, never here.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="AutoClean AI+", page_icon="🧹", layout="wide")

st.title("🧹 AutoClean AI+")
st.markdown(
    """
A multi-agent, explainable decision-support system for data cleaning.

Upload a dataset, review multiple candidate cleaning strategies scored across
six objectives, read a grounded explanation of the recommendation, approve
or reject it, and get back a cleaned dataset, an executive report, and a
standalone reproducible script -- all with a full audit trail.

**Get started:**
"""
)

st.page_link("pages/1_Upload_and_Profile.py", label="1. Upload & Profile a Dataset", icon="📤")
st.page_link("pages/2_Compare_Strategies.py", label="2. Compare Candidate Strategies", icon="📊")
st.page_link("pages/3_Review_and_Approve.py", label="3. Review Explanation & Approve", icon="✅")
st.page_link("pages/4_Experiment_History.py", label="4. Browse Experiment History", icon="🕘")

st.divider()
st.caption(
    "Built on the multi-objective optimization framework from Hu et al. (2026), "
    "extended with a multi-agent architecture, human-in-the-loop approval, and "
    "explainable AI recommendations. See PROJECT_MEMORY.md for full project history."
)
