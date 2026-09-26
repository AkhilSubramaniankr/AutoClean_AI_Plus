"""Unit tests for objective_weights_loader.py (Phase 6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autoclean.infrastructure.objective_weights_loader import load_objective_weights

pytestmark = pytest.mark.unit


class TestLoadObjectiveWeights:
    def test_loads_valid_yaml_file(self, tmp_path: Path) -> None:
        path = tmp_path / "weights.yaml"
        path.write_text(
            "weights:\n"
            "  data_quality: 0.3\n"
            "  computational_cost: 0.1\n"
            "  information_preservation: 0.15\n"
            "  statistical_validity: 0.15\n"
            "  fairness_impact: 0.15\n"
            "  downstream_ml: 0.15\n"
        )
        weights = load_objective_weights(path)
        assert weights.data_quality == 0.3

    def test_falls_back_to_uniform_when_file_missing(self, tmp_path: Path) -> None:
        weights = load_objective_weights(tmp_path / "does_not_exist.yaml")
        assert weights.data_quality == pytest.approx(1.0 / 6.0)

    def test_falls_back_to_uniform_when_yaml_malformed(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text("not: valid: yaml: [structure")
        weights = load_objective_weights(path)
        assert weights.data_quality == pytest.approx(1.0 / 6.0)

    def test_falls_back_to_uniform_when_weights_key_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "no_weights_key.yaml"
        path.write_text("something_else: 1\n")
        weights = load_objective_weights(path)
        assert weights.data_quality == pytest.approx(1.0 / 6.0)

    def test_falls_back_to_uniform_when_weights_dont_sum_to_one(self, tmp_path: Path) -> None:
        path = tmp_path / "bad_sum.yaml"
        path.write_text(
            "weights:\n"
            "  data_quality: 0.9\n"
            "  computational_cost: 0.9\n"
            "  information_preservation: 0.9\n"
            "  statistical_validity: 0.9\n"
            "  fairness_impact: 0.9\n"
            "  downstream_ml: 0.9\n"
        )
        weights = load_objective_weights(path)
        assert weights.data_quality == pytest.approx(1.0 / 6.0)

    def test_actual_project_config_file_loads_and_sums_to_one(self) -> None:
        """The real config/objective_weights.yaml shipped with this project
        should load successfully and reflect the Phase 6 justified defaults.
        """
        project_root = Path(__file__).resolve().parents[3]
        real_path = project_root / "src" / "autoclean" / "config" / "objective_weights.yaml"
        weights = load_objective_weights(real_path)
        total = (
            weights.data_quality + weights.computational_cost + weights.information_preservation
            + weights.statistical_validity + weights.fairness_impact + weights.downstream_ml
        )
        assert total == pytest.approx(1.0)
        assert weights.data_quality == 0.30  # the highest-weighted objective, per Phase 6 justification
