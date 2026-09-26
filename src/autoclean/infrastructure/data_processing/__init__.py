"""Deterministic dataset profiling, issue detection, and candidate strategy
generation (Pandas/NumPy/Scikit-learn only -- no LLM involvement, per NFR-1).

DESIGN ADDENDUM TO PHASE 2: this subpackage was not itemized by name in the
Phase 2 folder structure (Phase 2, Section 3), which anticipated profiling
logic as part of the Analysis Agent's use cases without specifying its
Infrastructure-layer home. Since Domain must stay framework-free (no Pandas)
per the Clean Architecture dependency rule (Phase 2, Section 2), and
`infrastructure/metrics/` was explicitly scoped in Phase 2 to the six
Evaluation Agent objectives (not issue *detection*), this dedicated
`infrastructure/data_processing/` package is added in Phase 4 to hold that
logic without overloading either existing package. Flagged explicitly here,
the same way Phase 2 flagged its own deferral of Eq. 8, so this addendum is
visible and reviewable rather than silently introduced.

Modules:
    profiler.py         -- DatasetProfiler: computes a DatasetProfile from a
                            pandas DataFrame.
    issue_detector.py   -- IssueDetector: detects DataIssue instances
                            (missing values, duplicates, outliers, dtype
                            inconsistencies) from a DataFrame + DatasetProfile.
    strategy_generator.py -- StrategyGenerator: deterministically generates
                            candidate CleaningStrategy objects from a list of
                            DataIssue (Phase 1, FR-3: at least 2 candidates).
"""
