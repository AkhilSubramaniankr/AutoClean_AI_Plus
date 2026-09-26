"""Unit tests for FileDatasetRepository, against real temporary files
(not mocked) -- the whole point of this class is correct Pandas
load/save-by-extension behavior."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from autoclean.infrastructure.persistence.file_dataset_repository import FileDatasetRepository

pytestmark = pytest.mark.unit


class TestFileDatasetRepository:
    def test_save_then_load_csv_round_trip(self, tmp_path: Path, clean_dataframe: pd.DataFrame) -> None:
        repo = FileDatasetRepository()
        path = str(tmp_path / "out.csv")
        repo.save(clean_dataframe, path)
        loaded = repo.load(path)
        pd.testing.assert_frame_equal(loaded, clean_dataframe)

    def test_save_then_load_parquet_round_trip(self, tmp_path: Path, clean_dataframe: pd.DataFrame) -> None:
        repo = FileDatasetRepository()
        path = str(tmp_path / "out.parquet")
        repo.save(clean_dataframe, path)
        loaded = repo.load(path)
        pd.testing.assert_frame_equal(loaded, clean_dataframe)

    def test_save_creates_parent_directories(self, tmp_path: Path, clean_dataframe: pd.DataFrame) -> None:
        repo = FileDatasetRepository()
        path = str(tmp_path / "nested" / "dir" / "out.csv")
        repo.save(clean_dataframe, path)
        assert Path(path).exists()

    def test_unsupported_extension_raises_on_load(self, tmp_path: Path) -> None:
        repo = FileDatasetRepository()
        with pytest.raises(ValueError, match="Unsupported dataset format"):
            repo.load(str(tmp_path / "data.json"))

    def test_unsupported_extension_raises_on_save(self, tmp_path: Path, clean_dataframe: pd.DataFrame) -> None:
        repo = FileDatasetRepository()
        with pytest.raises(ValueError, match="Unsupported dataset format"):
            repo.save(clean_dataframe, str(tmp_path / "data.json"))
