from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import cvxpy as cp
import torch
import torch.nn as nn

try:
    import coptpy
except ImportError:
    pass

from camp_core.outer_master.benders_master import BendersCut
from camp_core.integrations.diffusion_planner_v25_context import (
    PHI_DIMENSION,
    context_weights,
    validate_column_simplex_theta,
    validate_phi,
)
from camp_core.outer_master.robust_margin_master import (
    candidate_ranking_violations,
    empirical_cvar,
)

@dataclass
class ParametricCVXPYMasterConfig:
    num_atoms: int
    embedding_dim: int
    risk_type: str = "cvar"
    alpha: float = 0.9
    prior_reg_strength: float = 1.0
    offline_anchor_weight: float = 0.0
    device: str = "cpu"
    solver: str = "ECOS"

class ParametricCVXPYMaster:
    def __init__(
        self,
        config: ParametricCVXPYMasterConfig,
        scene_embeddings: np.ndarray, # [M, D] (or tensor, we will handle on CPU)
    ):
        self.cfg = config
        self.num_atoms = config.num_atoms
        self.emb_dim = config.embedding_dim
        
        # Convert embeddings to CPU numpy
        if isinstance(scene_embeddings, torch.Tensor):
            scene_embeddings = scene_embeddings.detach().cpu().numpy()
            
        self.M = len(scene_embeddings)
        self.M_active = self.M
        
        # Augment embeddings with 1 for bias
        self.phi_aug = np.concatenate([scene_embeddings, np.ones((self.M, 1))], axis=1) # [M, D+1]
        
        # CVXPY Variables
        self.Theta = cp.Variable((self.num_atoms, self.emb_dim + 1))
        self.eta = cp.Variable() # Global VaR
        
        self.cuts = collections.defaultdict(list)
        
        # State
        self.theta_value = np.zeros((self.num_atoms, self.emb_dim + 1))
        # Initialize uniform weights
        self.theta_value[:, -1] = 1.0 / self.num_atoms
        self.last_loss = float('inf')

    def add_cut(self, scenario_idx: int, cut: BendersCut):
        self.cuts[scenario_idx].append(cut)

    def _build_problem(self, active_indices: Optional[Sequence[int]] = None, prior_weights: Optional[np.ndarray] = None):
        if active_indices is None:
            active_indices = np.arange(self.M)
        
        M_act = len(active_indices)
        
        # Local slice of context embeddings
        # self.phi_aug is [M, D+1]
        phi_act = self.phi_aug[active_indices, :] # [M_act, D+1]
        
        # Build strict local variables to eliminate the 20000+ unbounded dummy dimensionalities
        Theta = self.Theta # Just reuse the global model parameters
        W_act = Theta @ phi_act.T # [R, M_act]
        
        theta_vars = cp.Variable(M_act)
        s = cp.Variable(M_act, nonneg=True)
        eta = self.eta
        
        constraints = []
        
        # Weight constraints (Simplex per scene)
        constraints.append(W_act >= 0)
        constraints.append(cp.sum(W_act, axis=0) == 1)
        
        # Build Matrix Vectorized Cuts (MASSIVE SPEEDUP + CORRECT INTERCEPT)
        if M_act > 0 and len(self.cuts[active_indices[0]]) > 0:
            num_cuts = len(self.cuts[active_indices[0]])
            for k in range(num_cuts):
                grad_k = np.array([self.cuts[idx][k].gradient for idx in active_indices]).T # [R, M_act]
                val_k = np.array([self.cuts[idx][k].value for idx in active_indices]) # [M_act]
                w_anch_k = np.array([self.cuts[idx][k].w_anchor for idx in active_indices]).T # [R, M_act]
                
                intercepts = val_k - np.sum(grad_k * w_anch_k, axis=0) # [M_act]
                
                constraints.append(theta_vars >= intercepts + cp.sum(cp.multiply(W_act, grad_k), axis=0))
                
        # Vectorized CVaR constraints
        constraints.append(s >= theta_vars - eta)
            
        # Objective
        if self.cfg.risk_type == "cvar":
            risk_obj = eta + (1.0 / ((1.0 - self.cfg.alpha) * M_act)) * cp.sum(s)
        else: # mean
            risk_obj = (1.0 / M_act) * cp.sum(theta_vars)
            
        # Regularization (Bayesian Trust Region / L2)
        reg_obj = 0.0
        if self.cfg.prior_reg_strength > 0:
            reg_obj = self.cfg.prior_reg_strength * cp.sum_squares(Theta)
            
        # Offline Anchor Weight Regularization (Distance from prior on average)
        anchor_obj = 0.0
        if self.cfg.offline_anchor_weight > 0 and prior_weights is not None:
            # W_mean = average of W over all active scenes
            W_mean = cp.sum(W_act, axis=1) / M_act
            anchor_obj = self.cfg.offline_anchor_weight * cp.sum_squares(W_mean - prior_weights)
            
        obj = cp.Minimize(risk_obj + reg_obj + anchor_obj)
        prob = cp.Problem(obj, constraints)
        return prob, risk_obj

    def solve(self, verbose: bool = False, active_indices: Optional[Sequence[int]] = None, prior_weights: Optional[np.ndarray] = None):
        prob, risk_obj = self._build_problem(active_indices, prior_weights)
        
        try:
            solver_mode = getattr(cp, self.cfg.solver.upper())
            
            # Try primary solver with increased iterations if supported
            kwargs = {}
            if self.cfg.solver.upper() == "CLARABEL":
                kwargs["max_iter"] = 1000
            elif self.cfg.solver.upper() == "SCS":
                kwargs["max_iters"] = 5000
                
            prob.solve(solver=solver_mode, verbose=verbose, **kwargs)
            
            # Soft failure fallback
            if prob.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                print(f"Primary solver {self.cfg.solver.upper()} returned {prob.status}. Triggering ECOS fallback...")
                prob.solve(solver=cp.ECOS, verbose=verbose, max_iters=5000)
                
                if prob.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                    print(f"ECOS returned {prob.status}. Triggering SCS fallback...")
                    prob.solve(solver=cp.SCS, verbose=verbose, max_iters=10000)
                    
        except AttributeError:
            print(f"Solver {self.cfg.solver} not found in cvxpy. Falling back to ECOS/SCS.")
            try: prob.solve(solver=cp.ECOS, verbose=verbose, max_iters=5000)
            except cp.SolverError: prob.solve(solver=cp.SCS, verbose=verbose, max_iters=10000)
        except cp.SolverError as e:
            if self.cfg.solver.upper() != "SCS":
                try: prob.solve(solver=cp.SCS, verbose=verbose, max_iters=10000)
                except cp.SolverError as e2: return {"status": "error", "error": str(e2)}
            else: return {"status": "error", "error": str(e)}
        
        if prob.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
            self.theta_value = self.Theta.value
            self.last_loss = prob.value
            return {
                "status": "optimal",
                "loss": prob.value,
                "risk_loss": risk_obj.value,
                "Theta": self.theta_value
            }
        else:
            return {"status": prob.status}

    def update_head_weights(self, head: nn.Module, theta_value: np.ndarray):
        with torch.no_grad():
            head.linear.weight.copy_(torch.tensor(theta_value[:, :-1], dtype=torch.float32))
            head.linear.bias.copy_(torch.tensor(theta_value[:, -1], dtype=torch.float32))


@dataclass(frozen=True)
class V25ParametricMasterConfig:
    """Strict scene-conditioned master for the frozen V25 context contract."""

    alpha: float = 0.9
    l2_reg: float = 1e-4
    bt_anchor_reg: float = 1e-4
    max_iter: int = 20
    tolerance: float = 1e-6
    solver: str = "CLARABEL"
    solver_options: tuple[tuple[str, Any], ...] = (
        ("max_iter", 1000),
        ("tol_gap_abs", 1e-9),
        ("tol_gap_rel", 1e-9),
        ("tol_feas", 1e-9),
    )
    bt_iterations: int = 80
    bt_learning_rate: float = 0.5
    bt_l2_reg: float = 1e-4
    bt_max_pairs: int = 8192

    def validate(self) -> None:
        if not 0.0 <= self.alpha < 1.0:
            raise ValueError("alpha must be in [0,1).")
        if self.l2_reg < 0.0 or self.bt_anchor_reg < 0.0:
            raise ValueError("master regularization strengths must be nonnegative.")
        if self.max_iter < 1 or self.tolerance < 0.0:
            raise ValueError("max_iter must be positive and tolerance nonnegative.")
        if self.solver.upper() != "CLARABEL":
            raise ValueError("V25 master requires strict CLARABEL with no fallback.")
        if self.bt_iterations < 1 or self.bt_learning_rate <= 0.0:
            raise ValueError("BT iterations and learning rate must be positive.")
        if self.bt_l2_reg < 0.0 or self.bt_max_pairs < 1:
            raise ValueError("BT regularization must be nonnegative and pairs positive.")
        keys = [str(key) for key, _value in self.solver_options]
        if len(keys) != len(set(keys)) or {"solver", "verbose"} & set(keys):
            raise ValueError("solver_options contain duplicate or reserved keys.")


@dataclass(frozen=True)
class V25BradleyTerryResult:
    theta: np.ndarray
    pair_count_available: int
    pair_count_used: int
    initial_loss: float
    final_loss: float
    iterations: int
    history: tuple[dict[str, float], ...]
    label_contract: str = "train_only_causal_oracle_pair_preferences"
    optimizer_contract: str = "convex_logistic_projected_gradient_no_softmax"


@dataclass(frozen=True)
class V25ParametricMasterResult:
    theta: np.ndarray
    train_weights: np.ndarray
    train_violations: np.ndarray
    final_master_gap: float
    converged: bool
    iterations: int
    cuts_per_scene: tuple[int, ...]
    history: tuple[dict[str, Any], ...]
    solver_status: str
    solver_name: str
    bt_warmup: V25BradleyTerryResult
    wall_seconds: float


def v25_bradley_terry_warmup(
    normalized_atoms: np.ndarray,
    phi: np.ndarray,
    oracle_indices: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    iterations: int = 80,
    learning_rate: float = 0.5,
    l2_reg: float = 1e-4,
    max_pairs: int = 8192,
) -> V25BradleyTerryResult:
    """Convex BT warmup from train-only causal pair preferences.

    This is not a neural shortcut. The objective is logistic in ``Theta`` and
    each deterministic gradient step is projected column-wise onto the same
    convex simplex feasible set used by the authoritative master. The warmup
    never consumes GT futures, closed-loop outcomes, holdout fields, or IDs.
    """
    atoms, phi_values, oracle, feasible, num_atoms = _validate_v25_problem(
        normalized_atoms, phi, oracle_indices, feasible_mask, margins=None
    )
    if iterations < 1 or learning_rate <= 0.0 or l2_reg < 0.0 or max_pairs < 1:
        raise ValueError("invalid Bradley-Terry optimizer settings.")
    pair_mask = feasible.copy()
    pair_mask[np.arange(atoms.shape[0]), oracle] = False
    records, candidates = np.nonzero(pair_mask)
    available = int(records.size)
    if available == 0:
        raise ValueError("Bradley-Terry warmup requires a non-oracle feasible pair.")
    if available > int(max_pairs):
        sample = np.linspace(0, available - 1, num=int(max_pairs), dtype=np.int64)
        records = records[sample]
        candidates = candidates[sample]
    pair_phi = phi_values[records]
    deltas = (
        atoms[records, oracle[records], :] - atoms[records, candidates, :]
    )
    uniform = np.full(
        (num_atoms, PHI_DIMENSION), 1.0 / num_atoms, dtype=np.float64
    )
    theta = uniform.copy()

    def objective(values: np.ndarray) -> float:
        logits = np.einsum("mr,rp,mp->m", deltas, values, pair_phi)
        return float(
            np.mean(np.logaddexp(0.0, logits))
            + float(l2_reg) * np.sum((values - uniform) ** 2)
        )

    initial_loss = objective(theta)
    history: list[dict[str, float]] = []
    for iteration in range(1, int(iterations) + 1):
        current_loss = objective(theta)
        logits = np.einsum("mr,rp,mp->m", deltas, theta, pair_phi)
        sigmoid = 1.0 / (1.0 + np.exp(-np.clip(logits, -50.0, 50.0)))
        gradient = deltas.T @ (sigmoid[:, None] * pair_phi) / float(records.size)
        gradient += 2.0 * float(l2_reg) * (theta - uniform)
        step = float(learning_rate) / np.sqrt(float(iteration))
        updated = _project_columns_to_simplex(theta - step * gradient)
        updated_loss = objective(updated)
        backtracks = 0
        while updated_loss > current_loss + 1e-12 and backtracks < 20:
            step *= 0.5
            updated = _project_columns_to_simplex(theta - step * gradient)
            updated_loss = objective(updated)
            backtracks += 1
        if updated_loss > current_loss + 1e-12:
            updated = theta.copy()
            updated_loss = current_loss
        delta_norm = float(np.linalg.norm(updated - theta))
        theta = updated
        if iteration == 1 or iteration % 10 == 0 or iteration == int(iterations):
            history.append(
                {
                    "iteration": float(iteration),
                    "objective": updated_loss,
                    "theta_delta_l2": delta_norm,
                    "step_size": step,
                    "backtracks": float(backtracks),
                }
            )
    validate_column_simplex_theta(theta, num_atoms=num_atoms)
    return V25BradleyTerryResult(
        theta=theta,
        pair_count_available=available,
        pair_count_used=int(records.size),
        initial_loss=initial_loss,
        final_loss=objective(theta),
        iterations=int(iterations),
        history=tuple(history),
    )


def solve_v25_parametric_cutting_plane(
    normalized_atoms: np.ndarray,
    phi: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    config: V25ParametricMasterConfig = V25ParametricMasterConfig(),
) -> V25ParametricMasterResult:
    """Solve the V25 finite-candidate CVaR/L2 master with exact gap checks."""
    start = time.perf_counter()
    config.validate()
    atoms, phi_values, oracle, feasible, num_atoms = _validate_v25_problem(
        normalized_atoms, phi, oracle_indices, feasible_mask, margins=margins
    )
    margin_values = np.asarray(margins, dtype=np.float64)
    bt = v25_bradley_terry_warmup(
        atoms,
        phi_values,
        oracle,
        feasible,
        iterations=config.bt_iterations,
        learning_rate=config.bt_learning_rate,
        l2_reg=config.bt_l2_reg,
        max_pairs=config.bt_max_pairs,
    )
    cuts: list[set[int]] = [set() for _ in range(atoms.shape[0])]
    train_weights = context_weights(bt.theta, phi_values)
    _, _, initial_worst = candidate_ranking_violations(
        atoms, train_weights, oracle, margin_values, feasible
    )
    for record_index, candidate_index in enumerate(initial_worst):
        cuts[record_index].add(int(candidate_index))

    theta = bt.theta.copy()
    master_losses = np.zeros(atoms.shape[0], dtype=np.float64)
    history: list[dict[str, Any]] = []
    converged = False
    solver_status = "not_solved"
    solver_name = "not_solved"
    final_gap = float("inf")
    for iteration in range(1, config.max_iter + 1):
        theta, master_losses, solver_status, solver_name, master_objective = (
            _solve_v25_restricted_master(
                atoms=atoms,
                phi=phi_values,
                oracle=oracle,
                margins=margin_values,
                cuts=cuts,
                config=config,
                bt_theta=bt.theta,
            )
        )
        train_weights = context_weights(theta, phi_values)
        _, exact_losses, worst = candidate_ranking_violations(
            atoms, train_weights, oracle, margin_values, feasible
        )
        gaps = np.maximum(exact_losses - master_losses, 0.0)
        final_gap = float(np.max(gaps))
        new_cuts = 0
        for record_index, candidate_index in enumerate(worst):
            candidate = int(candidate_index)
            if candidate not in cuts[record_index] and gaps[record_index] > config.tolerance:
                cuts[record_index].add(candidate)
                new_cuts += 1
        history.append(
            {
                "iteration": iteration,
                "master_objective": float(master_objective),
                "exact_cvar": float(empirical_cvar(exact_losses, config.alpha)[0]),
                "mean_violation": float(np.mean(exact_losses)),
                "max_violation": float(np.max(exact_losses)),
                "max_master_gap": final_gap,
                "new_cuts": int(new_cuts),
                "total_cuts": int(sum(len(values) for values in cuts)),
                "solver_status": solver_status,
                "solver_name": solver_name,
            }
        )
        if final_gap <= config.tolerance:
            converged = True
            break
        if new_cuts == 0:
            break

    if not converged:
        theta, master_losses, solver_status, solver_name, master_objective = (
            _solve_v25_restricted_master(
                atoms=atoms,
                phi=phi_values,
                oracle=oracle,
                margins=margin_values,
                cuts=cuts,
                config=config,
                bt_theta=bt.theta,
            )
        )
        train_weights = context_weights(theta, phi_values)
        _, exact_losses, _ = candidate_ranking_violations(
            atoms, train_weights, oracle, margin_values, feasible
        )
        final_gap = float(np.max(np.maximum(exact_losses - master_losses, 0.0)))
        converged = final_gap <= config.tolerance
    else:
        _, exact_losses, _ = candidate_ranking_violations(
            atoms, train_weights, oracle, margin_values, feasible
        )
    return V25ParametricMasterResult(
        theta=theta,
        train_weights=train_weights,
        train_violations=exact_losses,
        final_master_gap=final_gap,
        converged=bool(converged),
        iterations=len(history),
        cuts_per_scene=tuple(len(values) for values in cuts),
        history=tuple(history),
        solver_status=solver_status,
        solver_name=solver_name,
        bt_warmup=bt,
        wall_seconds=float(time.perf_counter() - start),
    )


def _validate_v25_problem(
    normalized_atoms: np.ndarray,
    phi: np.ndarray,
    oracle_indices: np.ndarray,
    feasible_mask: np.ndarray,
    margins: Optional[np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    atoms = np.asarray(normalized_atoms, dtype=np.float64)
    phi_values = np.asarray(phi, dtype=np.float64)
    oracle = np.asarray(oracle_indices, dtype=np.int64).reshape(-1)
    feasible = np.asarray(feasible_mask, dtype=bool)
    if atoms.ndim != 3 or min(atoms.shape) < 1:
        raise ValueError("normalized_atoms must have nonempty shape [N,K,R].")
    if not np.all(np.isfinite(atoms)) or np.any(atoms < 0.0):
        raise ValueError("normalized_atoms must be finite nonnegative costs.")
    validate_phi(phi_values)
    if phi_values.ndim != 2 or phi_values.shape[0] != atoms.shape[0]:
        raise ValueError("phi must have one row per training record.")
    if feasible.shape != atoms.shape[:2]:
        raise ValueError("feasible_mask must match atoms [N,K].")
    if oracle.shape != (atoms.shape[0],) or np.any(oracle < 0) or np.any(
        oracle >= atoms.shape[1]
    ):
        raise ValueError("oracle_indices must identify one candidate per record.")
    if not feasible[np.arange(atoms.shape[0]), oracle].all():
        raise ValueError("every causal oracle candidate must be feasible.")
    if margins is not None:
        margin_values = np.asarray(margins, dtype=np.float64)
        if margin_values.shape != atoms.shape[:2] or not np.all(
            np.isfinite(margin_values)
        ) or np.any(margin_values < 0.0):
            raise ValueError("margins must be finite nonnegative [N,K].")
    return atoms, phi_values, oracle, feasible, int(atoms.shape[2])


def _solve_v25_restricted_master(
    *,
    atoms: np.ndarray,
    phi: np.ndarray,
    oracle: np.ndarray,
    margins: np.ndarray,
    cuts: list[set[int]],
    config: V25ParametricMasterConfig,
    bt_theta: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, str, str, float]:
    num_records, _candidate_count, num_atoms = atoms.shape
    theta = cp.Variable((num_atoms, PHI_DIMENSION))
    losses = cp.Variable(num_records, nonneg=True)
    weights = theta @ phi.T
    constraints = [theta >= 0.0, cp.sum(theta, axis=0) == 1.0]
    oracle_atoms = atoms[np.arange(num_records), oracle]
    for record_index, candidate_indices in enumerate(cuts):
        for candidate_index in candidate_indices:
            if not np.isfinite(margins[record_index, candidate_index]):
                raise ValueError("cut margin must be finite.")
            atom_delta = oracle_atoms[record_index] - atoms[record_index, candidate_index]
            constraints.append(
                losses[record_index]
                >= margins[record_index, candidate_index]
                + atom_delta @ weights[:, record_index]
            )
    eta = cp.Variable(nonneg=True)
    excess = cp.Variable(num_records, nonneg=True)
    constraints.append(excess >= losses - eta)
    risk = eta + cp.sum(excess) / ((1.0 - config.alpha) * num_records)
    uniform = np.full(
        (num_atoms, PHI_DIMENSION), 1.0 / num_atoms, dtype=np.float64
    )
    regularization = config.l2_reg * cp.sum_squares(theta - uniform)
    regularization += config.bt_anchor_reg * cp.sum_squares(theta - bt_theta)
    problem = cp.Problem(cp.Minimize(risk + regularization), constraints)
    if "CLARABEL" not in {name.upper() for name in cp.installed_solvers()}:
        raise RuntimeError("strict V25 master requires installed CLARABEL.")
    try:
        problem.solve(
            solver=cp.CLARABEL,
            verbose=False,
            **dict(config.solver_options),
        )
    except cp.SolverError as exc:
        raise RuntimeError(f"strict CLARABEL solve failed: {exc}") from exc
    if problem.status != cp.OPTIMAL:
        raise RuntimeError(
            f"strict V25 master requires OPTIMAL, got {problem.status!r}; no fallback."
        )
    theta_value = np.asarray(theta.value, dtype=np.float64)
    validate_column_simplex_theta(theta_value, num_atoms=num_atoms, atol=1e-7)
    if np.any(theta_value < -1e-9) or not np.allclose(
        theta_value.sum(axis=0), 1.0, rtol=0.0, atol=1e-8
    ):
        raise RuntimeError("CLARABEL result failed the runtime column-simplex tolerance.")
    return (
        theta_value,
        np.asarray(losses.value, dtype=np.float64).reshape(-1),
        str(problem.status),
        str(problem.solver_stats.solver_name or "CLARABEL").upper(),
        float(problem.value),
    )


def _project_columns_to_simplex(values: np.ndarray) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError("values must be a matrix.")
    result = np.empty_like(matrix)
    for column in range(matrix.shape[1]):
        vector = matrix[:, column]
        ordered = np.sort(vector)[::-1]
        cumulative = np.cumsum(ordered) - 1.0
        positive = ordered - cumulative / np.arange(1, vector.size + 1) > 0.0
        rho = int(np.flatnonzero(positive)[-1])
        threshold = cumulative[rho] / float(rho + 1)
        result[:, column] = np.maximum(vector - threshold, 0.0)
    return result
