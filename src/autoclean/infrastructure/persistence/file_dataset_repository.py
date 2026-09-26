"""Concrete IDatasetRepository implementation: reads/writes csv/xlsx/parquet
via Pandas. No database involved despite living under `persistence/` --
grouped here because it is the Infrastructure-layer counterpart to
`sqlite/` for the *other* kind of persisted data this project has (files,
not rows).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from autoclean.application.ports.dataset_repository import IDatasetRepository

logger = logging.getLogger(__name__)

_LOADERS: dict[str, Callable[[str], pd.DataFrame]] = {
    "csv": pd.read_csv,
    "xlsx": pd.read_excel,
    "parquet": pd.read_parquet,
}
_SAVERS: dict[str, Callable[[pd.DataFrame, str], None]] = {
    "csv": lambda df, path: df.to_csv(path, index=False),
    "xlsx": lambda df, path: df.to_excel(path, index=False),
    "parquet": lambda df, path: df.to_parquet(path, index=False),
}


class FileDatasetRepository(IDatasetRepository):
    """Loads/saves datasets by file extension (Phase 1 §8: csv/xlsx/parquet)."""

    def load(self, path: str) -> pd.DataFrame:
        extension = Path(path).suffix.lstrip(".").lower()
        loader = _LOADERS.get(extension)
        if loader is None:
            raise ValueError(f"Unsupported dataset format '{extension}' for path {path!r}")
        df = loader(path)
        logger.info("Dataset loaded", extra={"path": path, "rows": len(df), "columns": len(df.columns)})
        return df

    def save(self, df: pd.DataFrame, path: str) -> str:
        extension = Path(path).suffix.lstrip(".").lower()
        saver = _SAVERS.get(extension)
        if saver is None:
            raise ValueError(f"Unsupported dataset format '{extension}' for path {path!r}")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        saver(df, path)
        logger.info("Dataset saved", extra={"path": path, "rows": len(df), "columns": len(df.columns)})
        return path
