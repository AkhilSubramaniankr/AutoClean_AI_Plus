"""Unit tests for the three LangGraph agent wrappers (Phase 5).

Uses fakes exclusively -- no real file I/O, no real LLM.
"""

from __future__ import annotations

import inspect

import pandas as pd
import pytest

from autoclean.agents.analysis_agent import AnalysisAgent
from autoclean.agents.decision_reporting_agent import DecisionReportingAgent
from autoclean.agents.evaluation_agent import EvaluationAgent
from autoclean.application.use_cases.evaluate_strategies import EvaluateStrategiesUseCase
from autoclean.application.use_cases.explain_recommendation import ExplainRecommendationUseCase
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.domain.value_objects.objective_weights import ObjectiveWeights
from autoclean.infrastructure.metrics.placeholder_metrics_engine import PlaceholderMetricsEngine
from tests.fakes import FakeDatasetRepository, FakeLLMClient

pytestmark = pytest.mark.unit


class TestAnalysisAgent:
    def test_run_populates_expected_state_fields(self, messy_dataframe: pd.DataFrame) -> None:
        agent = AnalysisAgent(
            FakeDatasetRepository(messy_dataframe), ProfileDatasetUseCase(), GenerateStrategiesUseCase()
        )
        result = agent.run({"experiment_id": "e1", "dataset_path": "irrelevant.csv"})

        assert result["dataset_profile"].row_count == len(messy_dataframe)
        assert len(result["detected_issues"]) == 4
        assert len(result["candidate_strategies"]) >= 2
        assert result["current_node"] == "analysis_agent"
        assert len(result["audit_log_entries"]) == 1

    def test_run_loads_from_the_configured_path(self, messy_dataframe: pd.DataFrame) -> None:
        fake_repo = FakeDatasetRepository(messy_dataframe)
        agent = AnalysisAgent(fake_repo, ProfileDatasetUseCase(), GenerateStrategiesUseCase())
        agent.run({"experiment_id": "e1", "dataset_path": "my_file.csv"})
        assert fake_repo.loaded_paths == ["my_file.csv"]


class TestEvaluationAgent:
    def test_has_no_llm_dependency_anywhere_in_its_signature(self) -> None:
        sig = inspect.signature(EvaluationAgent.__init__)
        for param_name, param in sig.parameters.items():
            assert "llm" not in param_name.lower()
            assert "LLM" not in str(param.annotation)

    def test_run_populates_scores_and_ranking(self, messy_dataframe: pd.DataFrame) -> None:
        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)

        agent = EvaluationAgent(
            FakeDatasetRepository(messy_dataframe),
            EvaluateStrategiesUseCase(PlaceholderMetricsEngine(), ObjectiveWeights.uniform()),
        )
        result = agent.run(
            {
                "experiment_id": "e1",
                "dataset_path": "irrelevant.csv",
                "candidate_strategies": strategies,
                "dataset_profile": profile,
                "audit_log_entries": [],
            }
        )

        assert set(result["strategy_scores"].keys()) == {s.strategy_id for s in strategies}
        assert set(result["ranked_strategy_ids"]) == {s.strategy_id for s in strategies}
        assert result["current_node"] == "evaluation_agent"


class TestDecisionReportingAgent:
    def _evaluated_state(self, messy_dataframe: pd.DataFrame) -> dict:
        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)
        weights = ObjectiveWeights.uniform()
        scores, ranked_ids = EvaluateStrategiesUseCase(PlaceholderMetricsEngine(), weights).execute(
            strategies, messy_dataframe, profile
        )
        return {
            "experiment_id": "e1",
            "candidate_strategies": strategies,
            "strategy_scores": {sid: score.as_dict() for sid, score in scores.items()},
            "ranked_strategy_ids": ranked_ids,
            "audit_log_entries": [],
        }

    def test_recommends_top_ranked_strategy_first(self, messy_dataframe: pd.DataFrame) -> None:
        state = self._evaluated_state(messy_dataframe)
        agent = DecisionReportingAgent(ExplainRecommendationUseCase(FakeLLMClient()))
        result = agent.run(state)
        assert result["recommended_strategy_id"] == state["ranked_strategy_ids"][0]
        assert result["explanation_text"].startswith("FAKE EXPLANATION")

    def test_rejection_advances_to_next_ranked_strategy(self, messy_dataframe: pd.DataFrame) -> None:
        state = self._evaluated_state(messy_dataframe)
        agent = DecisionReportingAgent(ExplainRecommendationUseCase(FakeLLMClient()))

        first = agent.run(state)
        state.update(first)
        state["human_decision"] = "rejected"

        second = agent.run(state)
        assert second["recommended_strategy_id"] != first["recommended_strategy_id"]
        assert first["recommended_strategy_id"] in second["rejected_strategy_ids"]

    def test_rejecting_every_strategy_sets_error_not_exception(self, messy_dataframe: pd.DataFrame) -> None:
        state = self._evaluated_state(messy_dataframe)
        agent = DecisionReportingAgent(ExplainRecommendationUseCase(FakeLLMClient()))

        result = agent.run(state)
        for _ in range(len(state["ranked_strategy_ids"])):
            state.update(result)
            state["human_decision"] = "rejected"
            result = agent.run(state)

        assert result.get("error") == "All candidate strategies have been rejected by the human reviewer."
