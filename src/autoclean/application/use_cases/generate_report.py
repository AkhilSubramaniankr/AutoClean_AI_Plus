"""GenerateReportUseCase: orchestrates ReportGenerator + ScriptExporter
(Phase 1, FR-11/FR-12).
"""

from __future__ import annotations

import logging
from typing import Any

from autoclean.domain.entities.cleaning_strategy import CleaningStrategy
from autoclean.infrastructure.reporting.report_generator import ReportGenerator
from autoclean.infrastructure.reporting.script_exporter import ScriptExporter

logger = logging.getLogger(__name__)


class GenerateReportUseCase:
    def __init__(
        self,
        report_generator: ReportGenerator | None = None,
        script_exporter: ScriptExporter | None = None,
    ) -> None:
        self._report_generator = report_generator or ReportGenerator()
        self._script_exporter = script_exporter or ScriptExporter()

    def execute(
        self,
        report_context: dict[str, Any],
        strategy: CleaningStrategy,
        report_output_path: str,
        script_output_path: str,
    ) -> tuple[str, str]:
        """Returns (report_path, script_path)."""
        report_path = self._report_generator.generate(report_context, report_output_path)
        script_path = self._script_exporter.export(strategy, script_output_path)
        logger.info(
            "GenerateReportUseCase complete",
            extra={"report_path": report_path, "script_path": script_path},
        )
        return report_path, script_path
