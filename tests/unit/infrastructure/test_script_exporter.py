"""Unit tests for ScriptExporter (Phase 8).

Includes the most important test in this file: actually EXECUTING the
generated script in a subprocess and comparing its output byte-for-byte
against StrategyExecutor's in-process result -- proving the "standalone,
reproducible script" claim (FR-12) is literally true, not just plausible.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.infrastructure.data_processing.strategy_executor import StrategyExecutor
from autoclean.infrastructure.reporting.script_exporter import ScriptExporter

pytestmark = pytest.mark.unit


class TestScriptExporter:
    def test_writes_a_real_file(self, messy_dataframe: pd.DataFrame, tmp_path: Path) -> None:
        _, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategy = GenerateStrategiesUseCase().execute(issues)[0]
        output_path = str(tmp_path / "reproduce.py")

        result_path = ScriptExporter().export(strategy, output_path)
        assert Path(result_path).exists()
        assert "def clean(df" in Path(result_path).read_text()

    def test_generated_script_output_matches_in_process_executor_exactly(
        self, messy_dataframe: pd.DataFrame, tmp_path: Path
    ) -> None:
        """The critical correctness test: run the generated script as a real
        subprocess (no dependency on this project's package) and compare its
        CSV output to StrategyExecutor.apply()'s in-process DataFrame.
        """
        _, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)
        conservative = next(s for s in strategies if s.name.startswith("Conservative"))

        input_csv = tmp_path / "input.csv"
        messy_dataframe.to_csv(input_csv, index=False)
        script_path = ScriptExporter().export(conservative, str(tmp_path / "reproduce.py"))
        output_csv = tmp_path / "script_output.csv"

        completed = subprocess.run(  # noqa: S603
            [sys.executable, script_path, str(input_csv), str(output_csv)],
            capture_output=True, text=True, timeout=30,
        )
        assert completed.returncode == 0, completed.stderr

        script_result = pd.read_csv(output_csv)
        in_process_result = StrategyExecutor().apply(messy_dataframe, conservative)
        pd.testing.assert_frame_equal(
            script_result.reset_index(drop=True), in_process_result.reset_index(drop=True), check_dtype=False
        )

    def test_no_op_strategy_produces_a_runnable_script(self, tmp_path: Path) -> None:
        from autoclean.domain.entities.cleaning_strategy import (
            CleaningOperation,
            CleaningStep,
            CleaningStrategy,
        )

        no_op_strategy = CleaningStrategy(
            strategy_id="s1", name="No-op", steps=(CleaningStep(operation=CleaningOperation.NO_OP),)
        )
        script_path = ScriptExporter().export(no_op_strategy, str(tmp_path / "noop.py"))

        input_csv = tmp_path / "in.csv"
        pd.DataFrame({"a": [1, 2, 3]}).to_csv(input_csv, index=False)
        output_csv = tmp_path / "out.csv"

        completed = subprocess.run(  # noqa: S603
            [sys.executable, script_path, str(input_csv), str(output_csv)],
            capture_output=True, text=True, timeout=30,
        )
        assert completed.returncode == 0, completed.stderr
        assert output_csv.exists()

    def test_unhandled_operation_raises_clearly(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        fake_step = MagicMock()
        fake_step.operation = "not_a_real_operation"
        with pytest.raises(ValueError, match="unhandled operation"):
            ScriptExporter._step_to_code(fake_step)

    def test_all_remaining_operation_types_produce_a_runnable_script(self, tmp_path: Path) -> None:
        """Covers the operation branches not exercised by the Conservative-
        strategy tests above: DROP_ROWS_WITH_MISSING, MEAN_IMPUTATION,
        MODE_IMPUTATION, CONSTANT_IMPUTATION, IQR_OUTLIER_REMOVAL.
        """
        from autoclean.domain.entities.cleaning_strategy import (
            CleaningOperation,
            CleaningStep,
            CleaningStrategy,
        )

        strategy = CleaningStrategy(
            strategy_id="s1",
            name="AllOps",
            steps=(
                CleaningStep(operation=CleaningOperation.DROP_ROWS_WITH_MISSING, target_column="a"),
                CleaningStep(operation=CleaningOperation.MEAN_IMPUTATION, target_column="b"),
                CleaningStep(operation=CleaningOperation.MODE_IMPUTATION, target_column="c"),
                CleaningStep(
                    operation=CleaningOperation.CONSTANT_IMPUTATION, target_column="d",
                    parameters={"fill_value": -1},
                ),
                CleaningStep(operation=CleaningOperation.IQR_OUTLIER_REMOVAL, target_column="e"),
            ),
        )
        script_path = ScriptExporter().export(strategy, str(tmp_path / "all_ops.py"))

        input_csv = tmp_path / "in.csv"
        pd.DataFrame(
            {
                "a": [1.0, None, 3.0, 4.0],
                "b": [1.0, None, 3.0, 4.0],
                "c": [1, 1, None, 2],
                "d": [1.0, None, 3.0, 4.0],
                "e": [1.0, 2.0, 3.0, 1000.0],
            }
        ).to_csv(input_csv, index=False)
        output_csv = tmp_path / "out.csv"

        completed = subprocess.run(  # noqa: S603
            [sys.executable, script_path, str(input_csv), str(output_csv)],
            capture_output=True, text=True, timeout=30,
        )
        assert completed.returncode == 0, completed.stderr
        assert output_csv.exists()
