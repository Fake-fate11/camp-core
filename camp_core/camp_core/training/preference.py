"""The final masked point-estimate calibration numerics, shared with the CLI."""
from __future__ import annotations

from typing import Any
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

def _differences(evidence: np.ndarray, mask: np.ndarray) -> np.ndarray:
    difference = evidence[:, 0:1, :] - evidence[:, 1:, :]
    return np.where(mask[:, None, :], difference, 0.0)


def _nll_and_gradient(
    beta: np.ndarray,
    difference: np.ndarray,
    sample_weight: np.ndarray | None = None,
) -> tuple[float, np.ndarray]:
    logits = np.einsum("nkd,d->nk", difference, beta, optimize=True)
    augmented = np.concatenate((np.zeros((logits.shape[0], 1)), logits), axis=1)
    normalizer = logsumexp(augmented, axis=1)
    probability = np.exp(logits - normalizer[:, None])
    row_gradient = np.einsum("nk,nkd->nd", probability, difference, optimize=True)
    if sample_weight is None:
        return float(np.sum(normalizer)), np.sum(row_gradient, axis=0)
    weight = np.asarray(sample_weight, dtype=np.float64)
    return float(np.dot(weight, normalizer)), np.einsum("n,nd->d", weight, row_gradient)


def _constraints(groups: tuple[np.ndarray, np.ndarray, np.ndarray]) -> tuple[dict[str, Any], ...]:
    safety, comfort, other = groups
    return (
        {"type": "eq", "fun": lambda b: float(np.sum(b) - 1.0), "jac": lambda b: np.ones_like(b)},
        {
            "type": "ineq",
            "fun": lambda b: float(np.sum(b[safety]) - np.sum(b[comfort])),
            "jac": lambda b: np.asarray([1.0 if i in safety else -1.0 if i in comfort else 0.0 for i in range(b.size)]),
        },
        {
            "type": "ineq",
            "fun": lambda b: float(np.sum(b[comfort]) - np.sum(b[other])),
            "jac": lambda b: np.asarray([1.0 if i in comfort else -1.0 if i in other else 0.0 for i in range(b.size)]),
        },
    )


def _fit(
    difference: np.ndarray,
    groups: tuple[np.ndarray, np.ndarray, np.ndarray],
    initial: np.ndarray,
    sample_weight: np.ndarray | None = None,
) -> Any:
    denominator = float(difference.shape[0] if sample_weight is None else np.sum(sample_weight))

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        value, gradient = _nll_and_gradient(beta, difference, sample_weight)
        return value / denominator, gradient / denominator

    return minimize(
        objective,
        np.asarray(initial, dtype=np.float64),
        jac=True,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * initial.size,
        constraints=_constraints(groups),
        options={"ftol": 1e-11, "maxiter": 1000, "disp": False},
    )


def _hessian(beta: np.ndarray, difference: np.ndarray) -> np.ndarray:
    logits = np.einsum("nkd,d->nk", difference, beta, optimize=True)
    augmented = np.concatenate((np.zeros((logits.shape[0], 1)), logits), axis=1)
    probabilities = np.exp(augmented - logsumexp(augmented, axis=1)[:, None])
    vectors = np.concatenate((np.zeros((difference.shape[0], 1, difference.shape[2])), difference), axis=1)
    mean = np.einsum("na,nad->nd", probabilities, vectors, optimize=True)
    second = np.einsum("na,nad,nae->de", probabilities, vectors, vectors, optimize=True)
    return second - np.einsum("nd,ne->de", mean, mean, optimize=True)


def _candidate_target(candidate: np.ndarray, beta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scores = np.einsum("nkd,d->nk", candidate, beta, optimize=True)
    minimum = np.min(scores, axis=1, keepdims=True)
    target = scores == minimum
    if np.any(~target.any(axis=1)):
        raise RuntimeError("point-estimate ChoiceRank produced an empty target set")
    return scores, target
