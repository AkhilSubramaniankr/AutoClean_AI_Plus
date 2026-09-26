"""em_quality_estimator.py: 🟦 PAPER-derived EM algorithm (Hu et al. 2026,
Section 3.3, Eqs. 2-6), adapted from per-sample/per-method confusion-matrix
estimation to per-strategy confidence estimation.

THE PAPER'S ORIGINAL SETUP (Eqs. 2-6): K methods each label the same N
samples; without ground truth, EM alternately estimates (a) each sample's
true-label posterior gamma_i(l), and (b) each method's confusion matrix
Theta_u = [theta_{u,l,c}] = P(method u outputs c | true label is l). This
requires multiple "labelers" judging the SAME items -- which is exactly the
structural feature this project's multiple candidate strategies provide,
once each strategy's cleaning decisions are reduced to a same-shape label
vector over the same rows.

THE ADAPTATION (🟩 ORIGINAL unit-of-analysis choice, 🟦 PAPER algorithm):
for a given original dataset, every candidate strategy u produces a binary
label y_hat_{i,u} for each original row i: 1 if strategy u judged row i
"clean" (survived unaltered), 0 if strategy u flagged/altered/removed it.
Treating each strategy as one of the paper's K "methods" and each row as
one of the paper's N samples reduces exactly to the paper's original EM
setup with 2 classes (l, c in {0, 1}). The output -- each strategy's
estimated diagonal confusion-matrix accuracy -- becomes that strategy's
`em_confidence`: how much the OTHER strategies' collective judgments concur
with this one, without needing ground truth for "was this row actually a
problem."

Equations implemented verbatim from the paper:
    E-step: gamma_i(l) <- pi_i(l) * PRODUCT_u theta_{u,l,yhat_{i,u}}          (Eq. ~3)
            (normalized so SUM_l gamma_i(l) = 1)
    M-step: theta_{u,l,c} <- SUM_i gamma_i(l) * 1(yhat_{i,u}=c) / SUM_i gamma_i(l)   (Eq. ~5)
            pi_i(l) <- gamma_i(l)                                             (Eq. ~6)
Iterated until the average absolute change in gamma across all samples
falls below `Settings.em_convergence_tolerance`, or `Settings.em_max_iterations`
is reached (both already defined in Phase 3's config/settings.py).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_NUM_CLASSES = 2  # binary: 0 = "flagged/altered", 1 = "judged clean"


class EMQualityEstimator:
    """Estimates each strategy's confidence via EM over binary row-clean labels."""

    def __init__(self, max_iterations: int = 50, convergence_tolerance: float = 1e-4) -> None:
        self._max_iterations = max_iterations
        self._convergence_tolerance = convergence_tolerance

    def estimate(self, strategy_labels: dict[str, np.ndarray[Any, Any]]) -> dict[str, float]:
        """Args:
            strategy_labels: strategy_id -> 1D array of 0/1 labels, one per
                original row, ALL THE SAME LENGTH and referring to the SAME
                rows in the SAME order across every strategy.

        Returns:
            strategy_id -> em_confidence in [0.0, 1.0].

        With fewer than 2 strategies, EM cannot estimate anything meaningful
        (there is no "agreement between labelers" to exploit) -- returns a
        neutral 0.5 for whatever single strategy is present, rather than
        fabricating a confidence value or raising an error.
        """
        strategy_ids = list(strategy_labels.keys())
        if len(strategy_ids) < 2:
            return {sid: 0.5 for sid in strategy_ids}

        labels_matrix = np.stack([strategy_labels[sid] for sid in strategy_ids], axis=1)  # (N, K)
        n_samples, n_methods = labels_matrix.shape
        if n_samples == 0:
            return {sid: 0.5 for sid in strategy_ids}

        # Initialize pi_i(l) from the majority vote across strategies for row i
        # (a standard, unbiased EM warm-start -- not itself the answer, just
        # a starting point the E/M steps will refine).
        mean_label = labels_matrix.mean(axis=1)  # fraction of strategies saying "clean" for row i
        gamma = np.stack([1.0 - mean_label, mean_label], axis=1)  # (N, 2): [P(l=0), P(l=1)]
        gamma = np.clip(gamma, 1e-6, 1.0)
        gamma /= gamma.sum(axis=1, keepdims=True)

        theta = self._m_step(labels_matrix, gamma, n_methods)

        delta = 1.0
        for iteration in range(self._max_iterations):
            new_gamma = self._e_step(labels_matrix, gamma, theta, n_methods)
            delta = float(np.mean(np.abs(new_gamma - gamma)))
            gamma = new_gamma
            theta = self._m_step(labels_matrix, gamma, n_methods)
            if delta < self._convergence_tolerance:
                logger.info(
                    "EMQualityEstimator converged", extra={"iterations": iteration + 1, "delta": delta}
                )
                break
        else:
            logger.info(
                "EMQualityEstimator reached max_iterations without full convergence",
                extra={"max_iterations": self._max_iterations, "final_delta": delta},
            )

        # Each strategy's confidence = its estimated diagonal accuracy,
        # weighted by the estimated class priors -- i.e. how often this
        # strategy's label matches the EM-estimated true label, overall.
        class_priors = gamma.mean(axis=0)  # (2,)
        confidences: dict[str, float] = {}
        for method_index, strategy_id in enumerate(strategy_ids):
            accuracy = sum(
                class_priors[label] * theta[method_index, label, label] for label in range(_NUM_CLASSES)
            )
            confidences[strategy_id] = float(max(0.0, min(1.0, accuracy)))
        return confidences

    @staticmethod
    def _e_step(
        labels_matrix: np.ndarray[Any, Any], gamma: np.ndarray[Any, Any], theta: np.ndarray[Any, Any], n_methods: int
    ) -> np.ndarray[Any, Any]:
        n_samples = labels_matrix.shape[0]
        pi = gamma  # pi_i(l) <- gamma_i(l) from the previous round (Eq. 6)
        new_gamma = np.zeros((n_samples, _NUM_CLASSES))
        for label in range(_NUM_CLASSES):
            likelihood = np.ones(n_samples)
            for method_index in range(n_methods):
                observed = labels_matrix[:, method_index]
                likelihood *= theta[method_index, label, observed]
            new_gamma[:, label] = pi[:, label] * likelihood
        new_gamma = np.clip(new_gamma, 1e-300, None)  # avoid all-zero rows before normalizing
        new_gamma /= new_gamma.sum(axis=1, keepdims=True)
        return new_gamma

    @staticmethod
    def _m_step(labels_matrix: np.ndarray[Any, Any], gamma: np.ndarray[Any, Any], n_methods: int) -> np.ndarray[Any, Any]:
        theta = np.zeros((n_methods, _NUM_CLASSES, _NUM_CLASSES))
        for method_index in range(n_methods):
            observed = labels_matrix[:, method_index]
            for true_label in range(_NUM_CLASSES):
                weight_total = gamma[:, true_label].sum()
                if weight_total <= 0:
                    theta[method_index, true_label, :] = 0.5  # uninformative fallback
                    continue
                for observed_label in range(_NUM_CLASSES):
                    mask = observed == observed_label
                    theta[method_index, true_label, observed_label] = (
                        gamma[mask, true_label].sum() / weight_total
                    )
        return theta
