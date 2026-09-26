"""Domain entities: Dataset, DataIssue, CleaningStrategy, CleaningStep,
EvaluationScore, Experiment, Decision, AuditEvent, ValidationReport.

Implemented in Phase 4 (Core Data Processing); ValidationReport added
Phase 8 (Cleaning Execution & Validation). Pure Python, no framework
dependencies -- see each module's docstring for the specific design
rationale carried over from Phase 2's Clean Architecture layer design.
"""

from autoclean.domain.entities.audit_event import AuditEvent
from autoclean.domain.entities.cleaning_strategy import (
    CleaningOperation,
    CleaningStep,
    CleaningStrategy,
)
from autoclean.domain.entities.data_issue import DataIssue, IssueType
from autoclean.domain.entities.dataset import Dataset, DatasetProfile
from autoclean.domain.entities.decision import Decision, DecisionType
from autoclean.domain.entities.evaluation_score import EvaluationScore
from autoclean.domain.entities.experiment import Experiment, ExperimentStatus
from autoclean.domain.entities.validation_report import ValidationReport

__all__ = [
    "AuditEvent",
    "CleaningOperation",
    "CleaningStep",
    "CleaningStrategy",
    "DataIssue",
    "IssueType",
    "Dataset",
    "DatasetProfile",
    "Decision",
    "DecisionType",
    "EvaluationScore",
    "Experiment",
    "ExperimentStatus",
    "ValidationReport",
]
