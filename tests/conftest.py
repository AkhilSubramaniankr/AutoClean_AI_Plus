"""Shared Pytest fixtures for the AutoClean AI+ test suite.

Pytest auto-discovers `conftest.py` at the root of the test tree, so these
fixtures are available to every test module under tests/ without an explicit
import (standard Pytest convention).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def messy_dataframe() -> pd.DataFrame:
    """A small, deliberately messy DataFrame exercising all four in-scope
    issue types (Phase 1, FR-2): missing values (age), an outlier
    (age=200), a dtype issue (income stored as text), and duplicate rows
    (row index 1 duplicated).
    """
    df = pd.DataFrame(
        {
            "age": [25, 30, np.nan, 40, 200, 28, 33, 30, 30, 45],
            "income": [
                "50000",
                "60000",
                "55000",
                "abc",
                "58000",
                "62000",
                "59000",
                "60000",
                "60000",
                "61000",
            ],
            "city": ["NY", "LA", "NY", "SF", "NY", "LA", "SF", "LA", "LA", "NY"],
        }
    )
    return pd.concat([df, df.iloc[[1]]], ignore_index=True)


@pytest.fixture
def clean_dataframe() -> pd.DataFrame:
    """A DataFrame with no missing values, duplicates, outliers, or dtype issues."""
    return pd.DataFrame(
        {
            "age": [25, 30, 35, 40, 45],
            "income": [50000, 60000, 55000, 58000, 62000],
            "city": ["NY", "LA", "NY", "SF", "NY"],
        }
    )
