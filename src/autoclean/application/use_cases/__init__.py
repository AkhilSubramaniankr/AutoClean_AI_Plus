"""Use cases, one per functional requirement from Phase 1.

Implemented Phase 5: ProfileDatasetUseCase, GenerateStrategiesUseCase,
EvaluateStrategiesUseCase, ExplainRecommendationUseCase, ApproveStrategyUseCase.
Implemented Phase 8: ExecuteCleaningUseCase, ValidateCleanedDatasetUseCase,
GenerateReportUseCase.
"""

from autoclean.application.use_cases.approve_strategy import ApproveStrategyUseCase
from autoclean.application.use_cases.evaluate_strategies import EvaluateStrategiesUseCase
from autoclean.application.use_cases.execute_cleaning import ExecuteCleaningUseCase
from autoclean.application.use_cases.explain_recommendation import ExplainRecommendationUseCase
from autoclean.application.use_cases.generate_report import GenerateReportUseCase
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.application.use_cases.validate_cleaned_dataset import ValidateCleanedDatasetUseCase

__all__ = [
    "ApproveStrategyUseCase",
    "EvaluateStrategiesUseCase",
    "ExecuteCleaningUseCase",
    "ExplainRecommendationUseCase",
    "GenerateReportUseCase",
    "GenerateStrategiesUseCase",
    "ProfileDatasetUseCase",
    "ValidateCleanedDatasetUseCase",
]
