"""Deterministic metrics engines implementing IMetricsEngine.

Phase 6 (REAL, default): RealMetricsEngine -- full six-objective evaluation
(quality_metrics.py, cost_metrics.py, information_preservation.py,
statistical_validity.py, fairness_metrics.py, downstream_ml_metrics.py) plus
the paper-derived EM confidence estimator (em_quality_estimator.py, Eqs. 2-6).

Phase 5 (TEMPORARY, kept as a fast test double): PlaceholderMetricsEngine.
"""
