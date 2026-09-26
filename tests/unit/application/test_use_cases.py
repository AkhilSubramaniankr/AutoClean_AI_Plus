"""Unit tests for Application-layer use cases (Phase 5).

Every test here uses fakes (tests/fakes.py) or the Phase 4 deterministic
engine directly -- no real SQLite, no real LLM, no real file I/O -- proving
the Repository/Adapter pattern's testability payoff (Phase 2, Section 12).
"""

from __future__ import annotations

import pandas as pd
import pytest

from autoclean.application.use_cases.approve_strategy import ApproveStrategyUseCase
from autoclean.application.use_cases.evaluate_strategies import EvaluateStrategiesUseCase
from autoclean.application.use_cases.explain_recommendation import ExplainRecommendationUseCase
from autoclean.application.use_cases.generate_strategies import GenerateStrategiesUseCase
from autoclean.application.use_cases.profile_dataset import ProfileDatasetUseCase
from autoclean.domain.entities.decision import DecisionType
from autoclean.domain.value_objects.objective_weights import ObjectiveWeights
from autoclean.infrastructure.metrics.placeholder_metrics_engine import PlaceholderMetricsEngine
from tests.fakes import FakeLLMClient, InMemoryExperimentRepository

pytestmark = pytest.mark.unit


class TestProfileDatasetUseCase:
    def test_execute_returns_profile_and_issues(self, messy_dataframe: pd.DataFrame) -> None:
        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        assert profile.row_count == len(messy_dataframe)
        assert len(issues) == 4  # all 4 issue types present in the messy fixture


class TestGenerateStrategiesUseCase:
    def test_execute_satisfies_fr3(self, messy_dataframe: pd.DataFrame) -> None:
        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)
        assert len(strategies) >= 2


class TestEvaluateStrategiesUseCase:
    def test_execute_scores_and_ranks_all_strategies(self, messy_dataframe: pd.DataFrame) -> None:
        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)

        use_case = EvaluateStrategiesUseCase(PlaceholderMetricsEngine(), ObjectiveWeights.uniform())
        scores, ranked_ids = use_case.execute(strategies, messy_dataframe, profile)

        assert set(scores.keys()) == {s.strategy_id for s in strategies}
        assert set(ranked_ids) == {s.strategy_id for s in strategies}

    def test_ranking_is_sorted_descending_by_weighted_total(self, messy_dataframe: pd.DataFrame) -> None:
        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)
        weights = ObjectiveWeights.uniform()
        use_case = EvaluateStrategiesUseCase(PlaceholderMetricsEngine(), weights)
        scores, ranked_ids = use_case.execute(strategies, messy_dataframe, profile)

        totals = [scores[sid].compute_weighted_total(weights) for sid in ranked_ids]
        assert totals == sorted(totals, reverse=True)

    def test_has_no_llm_client_parameter(self) -> None:
        import inspect

        sig = inspect.signature(EvaluateStrategiesUseCase.__init__)
        for param_name in sig.parameters:
            assert "llm" not in param_name.lower()

    def test_works_identically_with_real_metrics_engine(self, messy_dataframe: pd.DataFrame) -> None:
        """Confirms EvaluateStrategiesUseCase is genuinely engine-agnostic
        (Adapter pattern payoff): swapping PlaceholderMetricsEngine for
        RealMetricsEngine requires zero changes to this use case.
        """
        from autoclean.infrastructure.metrics.real_metrics_engine import RealMetricsEngine

        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)
        weights = ObjectiveWeights.uniform()

        use_case = EvaluateStrategiesUseCase(RealMetricsEngine(), weights)
        scores, ranked_ids = use_case.execute(strategies, messy_dataframe, profile)

        assert set(scores.keys()) == {s.strategy_id for s in strategies}
        for score in scores.values():
            for value in score.as_dict().values():
                assert 0.0 <= value <= 1.0
                assert isinstance(value, float)  # not numpy.float64 (regression test)


class TestExplainRecommendationUseCase:
    def test_context_is_grounded_in_real_scores(self, messy_dataframe: pd.DataFrame) -> None:
        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)
        weights = ObjectiveWeights.uniform()
        scores, ranked_ids = EvaluateStrategiesUseCase(PlaceholderMetricsEngine(), weights).execute(
            strategies, messy_dataframe, profile
        )

        fake_llm = FakeLLMClient()
        strategies_by_id = {s.strategy_id: s for s in strategies}
        top_id = ranked_ids[0]
        recommended_strategy = strategies_by_id[top_id]
        recommended_score = scores[top_id]
        alternatives = [(strategies_by_id[sid], scores[sid]) for sid in ranked_ids[1:]]

        ExplainRecommendationUseCase(fake_llm).execute(recommended_strategy, recommended_score, alternatives)

        assert fake_llm.last_context is not None
        assert fake_llm.last_context["recommended_strategy_name"] == recommended_strategy.name
        # Every score value passed to the LLM must trace back to the real computed score
        assert fake_llm.last_context["recommended_score"] == recommended_score.as_dict()

    def test_returns_explanation_and_consistency_warnings_tuple(self, messy_dataframe: pd.DataFrame) -> None:
        profile, issues = ProfileDatasetUseCase().execute(messy_dataframe)
        strategies = GenerateStrategiesUseCase().execute(issues)
        weights = ObjectiveWeights.uniform()
        scores, ranked_ids = EvaluateStrategiesUseCase(PlaceholderMetricsEngine(), weights).execute(
            strategies, messy_dataframe, profile
        )
        strategies_by_id = {s.strategy_id: s for s in strategies}
        top_id = ranked_ids[0]

        result = ExplainRecommendationUseCase(FakeLLMClient()).execute(
            strategies_by_id[top_id], scores[top_id], []
        )

        assert isinstance(result, tuple)
        explanation, warnings = result
        assert isinstance(explanation, str)
        assert isinstance(warnings, list)
        # FakeLLMClient's canned text contains no numbers, so nothing should be flagged
        assert warnings == []


class TestApproveStrategyUseCase:
    def test_execute_persists_decision_and_audit_event(self) -> None:
        repo = InMemoryExperimentRepository()
        use_case = ApproveStrategyUseCase(repo)

        decision = use_case.execute(
            experiment_id="exp-1", strategy_id="strat-1",
            decision_type=DecisionType.APPROVED, decided_by="analyst1",
        )

        assert repo.decisions == [decision]
        assert len(repo.audit_events) == 1
        assert repo.audit_events[0].event_type == "human_decision_recorded"
        assert repo.audit_events[0].experiment_id == "exp-1"
