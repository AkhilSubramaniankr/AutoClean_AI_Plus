"""Loads ObjectiveWeights from config/objective_weights.yaml.

A small, standalone Infrastructure-layer function rather than a method on
`ObjectiveWeights` itself (Domain layer), since parsing YAML/file I/O has no
place in a framework-free Domain value object (Phase 2, Section 2).
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from autoclean.domain.value_objects.objective_weights import ObjectiveWeights

logger = logging.getLogger(__name__)


def load_objective_weights(path: Path) -> ObjectiveWeights:
    """Load and validate ObjectiveWeights from a YAML file shaped like
    `config/objective_weights.yaml` (a top-level `weights:` mapping with the
    six required keys). Falls back to `ObjectiveWeights.uniform()` with a
    logged warning if the file is missing or malformed, rather than
    crashing the whole workflow over a config file problem.
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        weights = ObjectiveWeights.from_mapping(data["weights"])
        logger.info("Loaded objective weights", extra={"path": str(path)})
        return weights
    except (FileNotFoundError, KeyError, ValueError, yaml.YAMLError) as exc:
        logger.warning(
            "Failed to load objective_weights.yaml; falling back to uniform weights",
            extra={"path": str(path), "error": str(exc)},
        )
        return ObjectiveWeights.uniform()
