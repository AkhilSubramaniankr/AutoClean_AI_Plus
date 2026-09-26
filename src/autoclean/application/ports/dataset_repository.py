"""Port interface for reading/writing dataset files.

Design note: this port's signatures use `pandas.DataFrame` directly, rather
than a bespoke Domain type, as a deliberate pragmatic exception -- Pandas is
this project's declared in-memory tabular data structure (Phase 1 Technology
Stack) across every layer that touches data, not a web/UI framework the
Domain layer needs isolating from. `DatasetProfile` (Domain) remains
framework-free; only the raw tabular data itself is represented as a
DataFrame at this boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class IDatasetRepository(ABC):
    """Loads and saves tabular datasets from/to the file system."""

    @abstractmethod
    def load(self, path: str) -> pd.DataFrame:
        """Load a dataset from `path`. Supports csv/xlsx/parquet (Phase 1 §8)."""
        raise NotImplementedError

    @abstractmethod
    def save(self, df: pd.DataFrame, path: str) -> str:
        """Save `df` to `path`, creating parent directories as needed.
        Returns the final path written to.
        """
        raise NotImplementedError
