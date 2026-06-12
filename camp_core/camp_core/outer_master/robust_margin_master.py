from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np


@dataclass(frozen=True)
class RobustMarginConfig:
    mode: str
    risk_type: str = "cvar"
    alpha: float = 0.9
    l2_reg: float = 1e-4
    max_iter: int = 20
    tolerance: float = 1e-6
    solver: str = "CLARABEL"
    verbose: bool = False
    static_weight_lower_bounds: Optional[tuple[float, ...]] = None

    def validate(self) -> None:
        if self.mode not in {"static", "theta"}:
            raise ValueError(f"mode must be 'static' or 'theta', got {self.mode!r}.")
        if self.risk_type not in {"mean", "cvar"}:
            raise ValueError(
                f"risk_type must be 'mean' or 'cvar', got {self.risk_type!r}."
            )
        if self.risk_type == "cvar" and not 0.0 <= self.alpha < 1.0:
            raise ValueError("alpha must be in [0, 1) for CVaR.")
        if self.l2_reg < 0.0:
            raise ValueError("l2_reg must be nonnegative.")
        if self.max_iter <= 0:
            raise ValueError("max_iter must be positive.")
        if self.tolerance < 0.0:
            raise ValueError("tolerance must be nonnegative.")
        if self.static_weight_lower_bounds is not None:
            lower = np.asarray(
                self.static_weight_lower_bounds,
                dtype=np.float64,
            ).reshape(-1)
            if self.mode != "static":
                raise ValueError(
                    "static_weight_lower_bounds require static mode."
                )
            if (
                not np.all(np.isfinite(lower))
                or np.any(lower < 0.0)
                or float(np.sum(lower)) > 1.0 + 1e-12
            ):
                raise ValueError(
                    "static_weight_lower_bounds must be finite, nonnegative, "
                    "and sum to at most one."
                )


@dataclass
class RobustMarginResult:
    static_weights: Optional[np.ndarray]
    theta: Optional[np.ndarray]
    train_weights: np.ndarray
    train_violations: np.ndarray
    final_master_gap: float
    history: list[dict[str, Any]]
    converged: bool
    cuts_per_scene: list[int]
    solver_status: str


def outcome_oracle_and_margins(
    outcome_values: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    margin_scale: float,
    margin_clip: float,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(outcome_values, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    if values.ndim != 2 or feasible.shape != values.shape:
        raise ValueError(
            "outcome_values and feasible_mask must both have shape [N,K], "
            f"got {values.shape} and {feasible.shape}."
        )
    if margin_scale < 0.0 or margin_clip < 0.0:
        raise ValueError("margin_scale and margin_clip must be nonnegative.")
    finite_feasible = feasible & np.isfinite(values)
    if not finite_feasible.any(axis=1).all():
        raise ValueError("Each record must contain a finite feasible outcome.")

    masked = np.where(finite_feasible, values, -np.inf)
    oracle = np.argmax(masked, axis=1)
    oracle_values = values[np.arange(values.shape[0]), oracle]
    margins = float(margin_scale) * (oracle_values[:, None] - values)
    margins = np.clip(
        np.nan_to_num(margins, nan=0.0, posinf=margin_clip, neginf=0.0),
        0.0,
        float(margin_clip),
    )
    margins[~finite_feasible] = 0.0
    margins[np.arange(values.shape[0]), oracle] = 0.0
    return oracle.astype(np.int64), margins


def candidate_ranking_violations(
    normalized_atoms: np.ndarray,
    weights: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    feasible_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    atoms = np.asarray(normalized_atoms, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    oracle = np.asarray(oracle_indices, dtype=np.int64).reshape(-1)
    margin_values = np.asarray(margins, dtype=np.float64)
    if atoms.ndim != 3:
        raise ValueError(f"normalized_atoms must be [N,K,R], got {atoms.shape}.")
    if feasible.shape != atoms.shape[:2] or margin_values.shape != atoms.shape[:2]:
        raise ValueError("feasible_mask and margins must match atoms [N,K].")
    if oracle.shape != (atoms.shape[0],):
        raise ValueError(f"oracle_indices must have shape ({atoms.shape[0]},).")
    if not feasible[np.arange(atoms.shape[0]), oracle].all():
        raise ValueError("Every oracle candidate must be feasible.")

    weight_values = np.asarray(weights, dtype=np.float64)
    if weight_values.ndim == 1:
        if weight_values.shape != (atoms.shape[2],):
            raise ValueError("Static weights must match the atom dimension.")
        weight_values = np.broadcast_to(weight_values, (atoms.shape[0], atoms.shape[2]))
    if weight_values.shape != (atoms.shape[0], atoms.shape[2]):
        raise ValueError(
            "weights must have shape [R] or [N,R], "
            f"got {weight_values.shape} for atoms {atoms.shape}."
        )

    oracle_atoms = atoms[np.arange(atoms.shape[0]), oracle]
    atom_deltas = oracle_atoms[:, None, :] - atoms
    candidate_values = margin_values + np.einsum(
        "nkr,nr->nk", atom_deltas, weight_values
    )
    candidate_values[~feasible] = -np.inf
    worst_indices = np.argmax(candidate_values, axis=1)
    scene_violations = np.maximum(
        candidate_values[np.arange(atoms.shape[0]), worst_indices],
        0.0,
    )
    return candidate_values, scene_violations, worst_indices.astype(np.int64)


def empirical_cvar(losses: np.ndarray, alpha: float) -> tuple[float, float]:
    values = np.asarray(losses, dtype=np.float64).reshape(-1)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("losses must contain finite values.")
    if not 0.0 <= alpha < 1.0:
        raise ValueError("alpha must be in [0, 1).")
    candidates = np.unique(values)
    objectives = np.asarray(
        [
            eta
            + np.maximum(values - eta, 0.0).sum()
            / ((1.0 - float(alpha)) * values.size)
            for eta in candidates
        ]
    )
    best = int(np.argmin(objectives))
    return float(objectives[best]), float(candidates[best])


def project_simplex_rows(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    if array.ndim != 2 or array.shape[1] == 0:
        raise ValueError(f"values must have shape [N,R], got {array.shape}.")
    projected = np.empty_like(array)
    for row_idx, row in enumerate(array):
        sorted_row = np.sort(row)[::-1]
        cumulative = np.cumsum(sorted_row) - 1.0
        positive = sorted_row - cumulative / np.arange(1, row.size + 1) > 0.0
        rho = int(np.flatnonzero(positive)[-1])
        threshold = cumulative[rho] / float(rho + 1)
        projected[row_idx] = np.maximum(row - threshold, 0.0)
    return projected


def theta_weights(theta: np.ndarray, features: np.ndarray) -> np.ndarray:
    feature_values = np.asarray(features, dtype=np.float64)
    theta_values = np.asarray(theta, dtype=np.float64)
    if feature_values.ndim != 2:
        raise ValueError("features must have shape [N,D].")
    if theta_values.shape[1] != feature_values.shape[1] + 1:
        raise ValueError("Theta must have shape [R,D+1].")
    augmented = np.concatenate(
        [feature_values, np.ones((feature_values.shape[0], 1), dtype=np.float64)],
        axis=1,
    )
    return project_simplex_rows(augmented @ theta_values.T)


def _risk_value(losses: np.ndarray, config: RobustMarginConfig) -> float:
    if config.risk_type == "mean":
        return float(np.mean(losses))
    return empirical_cvar(losses, config.alpha)[0]


def _static_lower_bounds(
    config: RobustMarginConfig,
    num_atoms: int,
) -> np.ndarray:
    if config.static_weight_lower_bounds is None:
        return np.zeros(num_atoms, dtype=np.float64)
    lower = np.asarray(
        config.static_weight_lower_bounds,
        dtype=np.float64,
    ).reshape(-1)
    if lower.shape != (num_atoms,):
        raise ValueError(
            "static_weight_lower_bounds must match the atom dimension."
        )
    return lower


def _solve_master(
    normalized_atoms: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    cuts: list[set[int]],
    config: RobustMarginConfig,
    features: Optional[np.ndarray],
) -> tuple[Optional[np.ndarray], Optional[np.ndarray], np.ndarray, str, float]:
    try:
        import cvxpy as cp
    except ImportError as exc:
        raise RuntimeError(
            "Robust CAMP training requires cvxpy>=1.5.0. "
            "Install the repository requirements in the training environment."
        ) from exc

    atoms = normalized_atoms
    num_records, _, num_atoms = atoms.shape
    oracle_atoms = atoms[np.arange(num_records), oracle_indices]
    loss_vars = cp.Variable(num_records, nonneg=True)
    constraints = []
    static_var = None
    theta_var = None

    if config.mode == "static":
        lower = _static_lower_bounds(config, num_atoms)
        residual = 1.0 - float(np.sum(lower))
        static_var = cp.Variable(num_atoms)
        constraints.extend([static_var >= 0.0, cp.sum(static_var) == 1.0])
        static_weights_expr = lower + residual * static_var

        def weight_expr(record_idx: int):
            return static_weights_expr

        uniform = np.full(num_atoms, 1.0 / num_atoms, dtype=np.float64)
        regularization = config.l2_reg * cp.sum_squares(
            static_weights_expr - uniform
        )
    else:
        if features is None:
            raise ValueError("Theta mode requires normalized scene features.")
        feature_values = np.asarray(features, dtype=np.float64)
        augmented = np.concatenate(
            [
                feature_values,
                np.ones((feature_values.shape[0], 1), dtype=np.float64),
            ],
            axis=1,
        )
        theta_var = cp.Variable((num_atoms, augmented.shape[1]))
        scene_weights = theta_var @ augmented.T
        constraints.extend(
            [scene_weights >= 0.0, cp.sum(scene_weights, axis=0) == 1.0]
        )

        def weight_expr(record_idx: int):
            return scene_weights[:, record_idx]

        uniform = np.full(num_atoms, 1.0 / num_atoms, dtype=np.float64)
        regularization = config.l2_reg * (
            cp.sum_squares(theta_var[:, :-1])
            + cp.sum_squares(theta_var[:, -1] - uniform)
        )

    for record_idx, candidate_indices in enumerate(cuts):
        for candidate_idx in candidate_indices:
            atom_delta = oracle_atoms[record_idx] - atoms[record_idx, candidate_idx]
            constraints.append(
                loss_vars[record_idx]
                >= margins[record_idx, candidate_idx]
                + atom_delta @ weight_expr(record_idx)
            )

    if config.risk_type == "mean":
        risk_objective = cp.sum(loss_vars) / num_records
    else:
        eta = cp.Variable(nonneg=True)
        excess = cp.Variable(num_records, nonneg=True)
        constraints.append(excess >= loss_vars - eta)
        risk_objective = eta + cp.sum(excess) / (
            (1.0 - config.alpha) * num_records
        )
    problem = cp.Problem(cp.Minimize(risk_objective + regularization), constraints)

    installed = set(cp.installed_solvers())
    solver_candidates = []
    for solver_name in (config.solver, "CLARABEL", "SCS", "ECOS", "OSQP"):
        upper = solver_name.upper()
        if upper in installed and upper not in solver_candidates:
            solver_candidates.append(upper)
    if not solver_candidates:
        raise RuntimeError("No compatible CVXPY solver is installed.")

    last_error: Optional[Exception] = None
    for solver_name in solver_candidates:
        try:
            problem.solve(solver=solver_name, verbose=config.verbose)
        except cp.SolverError as exc:
            last_error = exc
            continue
        if problem.status in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
            static_value = (
                None
                if static_var is None
                else np.asarray(
                    static_weights_expr.value,
                    dtype=np.float64,
                ).reshape(-1)
            )
            theta_value = (
                None
                if theta_var is None
                else np.asarray(theta_var.value, dtype=np.float64)
            )
            return (
                static_value,
                theta_value,
                np.asarray(loss_vars.value, dtype=np.float64).reshape(-1),
                str(problem.status),
                float(problem.value),
            )
    if last_error is not None:
        raise RuntimeError(f"All CVXPY solvers failed: {last_error}") from last_error
    raise RuntimeError(f"Robust margin master returned status {problem.status!r}.")


def solve_robust_margin_cutting_plane(
    normalized_atoms: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    config: RobustMarginConfig,
    features: Optional[np.ndarray] = None,
) -> RobustMarginResult:
    config.validate()
    atoms = np.asarray(normalized_atoms, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    oracle = np.asarray(oracle_indices, dtype=np.int64).reshape(-1)
    margin_values = np.asarray(margins, dtype=np.float64)
    if atoms.ndim != 3:
        raise ValueError("normalized_atoms must have shape [N,K,R].")
    if atoms.shape[0] == 0 or atoms.shape[1] == 0 or atoms.shape[2] == 0:
        raise ValueError("normalized_atoms dimensions must all be non-empty.")
    if not np.all(np.isfinite(atoms)):
        raise ValueError("normalized_atoms must contain only finite values.")
    if np.any(atoms < 0.0):
        raise ValueError(
            "normalized_atoms must be nonnegative cost features so simplex "
            "weights preserve the declared atom direction."
        )
    if feasible.shape != atoms.shape[:2] or margin_values.shape != atoms.shape[:2]:
        raise ValueError("feasible_mask and margins must match atoms [N,K].")
    if not np.all(np.isfinite(margin_values)) or np.any(margin_values < 0.0):
        raise ValueError("margins must contain finite nonnegative values.")
    if oracle.shape != (atoms.shape[0],):
        raise ValueError("oracle_indices must match the record count.")
    if np.any(oracle < 0) or np.any(oracle >= atoms.shape[1]):
        raise ValueError("oracle_indices must identify a candidate in each record.")
    if not feasible[np.arange(atoms.shape[0]), oracle].all():
        raise ValueError("Every oracle candidate must be feasible.")
    if config.mode == "theta":
        feature_values = np.asarray(features, dtype=np.float64)
        if feature_values.ndim != 2 or feature_values.shape[0] != atoms.shape[0]:
            raise ValueError("Theta features must have shape [N,D].")
    else:
        feature_values = None

    num_records, _, num_atoms = atoms.shape
    if config.mode == "static":
        _static_lower_bounds(config, num_atoms)
    cuts: list[set[int]] = [set() for _ in range(num_records)]
    static_weights: Optional[np.ndarray] = None
    theta: Optional[np.ndarray] = None
    if config.mode == "static":
        train_weights = np.full(
            (num_records, num_atoms), 1.0 / num_atoms, dtype=np.float64
        )
    else:
        theta = np.zeros((num_atoms, feature_values.shape[1] + 1), dtype=np.float64)
        theta[:, -1] = 1.0 / num_atoms
        train_weights = theta_weights(theta, feature_values)

    _, _, initial_worst = candidate_ranking_violations(
        atoms, train_weights, oracle, margin_values, feasible
    )
    for record_idx, candidate_idx in enumerate(initial_worst):
        cuts[record_idx].add(int(candidate_idx))

    history: list[dict[str, Any]] = []
    converged = False
    solver_status = "not_solved"
    master_losses = np.zeros(num_records, dtype=np.float64)
    for iteration in range(1, config.max_iter + 1):
        (
            static_weights,
            theta,
            master_losses,
            solver_status,
            master_objective,
        ) = _solve_master(
            atoms,
            oracle,
            margin_values,
            cuts,
            config,
            feature_values,
        )
        if config.mode == "static":
            train_weights = np.broadcast_to(
                static_weights, (num_records, num_atoms)
            ).copy()
        else:
            train_weights = theta_weights(theta, feature_values)

        _, true_losses, worst_indices = candidate_ranking_violations(
            atoms, train_weights, oracle, margin_values, feasible
        )
        gap = np.maximum(true_losses - master_losses, 0.0)
        max_gap = float(np.max(gap))
        new_cuts = 0
        for record_idx, candidate_idx in enumerate(worst_indices):
            candidate = int(candidate_idx)
            if candidate not in cuts[record_idx] and gap[record_idx] > config.tolerance:
                cuts[record_idx].add(candidate)
                new_cuts += 1
        history.append(
            {
                "iteration": iteration,
                "master_objective": float(master_objective),
                "exact_risk": _risk_value(true_losses, config),
                "mean_violation": float(np.mean(true_losses)),
                "max_violation": float(np.max(true_losses)),
                "max_master_gap": max_gap,
                "new_cuts": new_cuts,
                "total_cuts": int(sum(len(scene_cuts) for scene_cuts in cuts)),
                "stalled": bool(new_cuts == 0 and max_gap > config.tolerance),
            }
        )
        if max_gap <= config.tolerance:
            converged = True
            break
        if new_cuts == 0:
            break

    if not converged:
        (
            static_weights,
            theta,
            master_losses,
            solver_status,
            master_objective,
        ) = _solve_master(
            atoms,
            oracle,
            margin_values,
            cuts,
            config,
            feature_values,
        )
        if config.mode == "static":
            train_weights = np.broadcast_to(
                static_weights, (num_records, num_atoms)
            ).copy()
        else:
            train_weights = theta_weights(theta, feature_values)
        _, true_losses, _ = candidate_ranking_violations(
            atoms, train_weights, oracle, margin_values, feasible
        )
        final_gap = np.maximum(true_losses - master_losses, 0.0)
        final_max_gap = float(np.max(final_gap))
        converged = final_max_gap <= config.tolerance
        history.append(
            {
                "iteration": config.max_iter + 1,
                "master_objective": float(master_objective),
                "exact_risk": _risk_value(true_losses, config),
                "mean_violation": float(np.mean(true_losses)),
                "max_violation": float(np.max(true_losses)),
                "max_master_gap": final_max_gap,
                "new_cuts": 0,
                "total_cuts": int(sum(len(scene_cuts) for scene_cuts in cuts)),
                "final_resolve": True,
            }
        )

    _, train_violations, _ = candidate_ranking_violations(
        atoms, train_weights, oracle, margin_values, feasible
    )
    final_master_gap = float(
        np.max(np.maximum(train_violations - master_losses, 0.0))
    )
    return RobustMarginResult(
        static_weights=static_weights,
        theta=theta,
        train_weights=train_weights,
        train_violations=train_violations,
        final_master_gap=final_master_gap,
        history=history,
        converged=converged,
        cuts_per_scene=[len(scene_cuts) for scene_cuts in cuts],
        solver_status=solver_status,
    )
