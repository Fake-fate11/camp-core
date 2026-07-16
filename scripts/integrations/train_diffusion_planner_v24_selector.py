#!/usr/bin/env python3
"""Train the frozen v24 static affine selector on train-only causal labels."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_CAMP_ATOM_NAMES_V10,
)
from camp_core.outer_master.robust_margin_master import (  # noqa: E402
    RobustMarginConfig,
    _solve_master,
    candidate_ranking_violations,
    project_simplex_rows,
)
from scripts.integrations.preflight_diffusion_planner_v24_convex_training import (  # noqa: E402
    _canonical_json_bytes,
    _file_sha256,
    _is_sha256,
    _read_jsonl,
    _require_clean_repo,
    verify_complete_seal,
)
from scripts.integrations.review_diffusion_planner_v24_atom_availability import (  # noqa: E402
    _snapshot_arrays,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_SOURCE_HEAD = "bfc0a52307bf7d9184a5f4596b951058c02ba67c"
LABEL_SOURCE_HEAD = "5659677944269f758cb775fe69c297489df360ad"
PLAN_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_convex_training_static_preflight_bfc0a523_20260716T195856CST"
)
PLAN_ROOT_SHA256 = (
    "43f26263ff24cad5966cb3a740af6d3307490ab1bd3e07d03284589bee0d28f5"
)
LABEL_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_train_causal_labels_56596779_20260716T204104CST"
)
LABEL_ROOT_SHA256 = (
    "9a14fb003fe9145e62b24c20fcecc013baedd72e312add82a8c6a6e6dcde966c"
)
LABEL_REVIEW_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_train_causal_labels_independent_review_56596779_"
    "20260716T204427CST"
)
LABEL_REVIEW_ROOT_SHA256 = (
    "d23d09564ea675b0ef7ce35d968c6dd03ead1df5e1282c498704827986eab468"
)
MERGED_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_native_corpus_merged_train_assembly_5b725629_"
    "20260716T154602CST"
)
MERGED_ROOT_SHA256 = (
    "d8278d030cabd71af88f60d13c410a37c515f22e0ea4c606a592abecc598bdcc"
)
CONFIG_RELATIVE = Path(
    "configs/integrations/diffusion_planner_v24_convex_training_plan.json"
)
AUDIT_RELATIVE = Path("docs/diffusion_planner_v24_iteration_audit.md")
EXPECTED_SNAPSHOTS = 67796
EXPECTED_CANDIDATES = EXPECTED_SNAPSHOTS * 8
EXPECTED_ROUTES = 375
EXPECTED_ROUTE_SEEDS = 1875
EXPECTED_LEVELS = (25, 50, 75, 100)
EXPECTED_LEVEL_ROUTES = (94, 188, 281, 375)
EXPECTED_LEVEL_SNAPSHOTS = (16979, 35022, 50752, 67796)
EXPECTED_LEVEL_ROUTE_SEEDS = (470, 940, 1405, 1875)
EXPECTED_LEVEL_COMPLETE = (262, 550, 789, 1054)
EXPECTED_LEVEL_FAILED = (208, 390, 616, 821)
EXPECTED_SEEDS = (24001, 24002, 24003, 24004, 24005)
EXPECTED_SOURCE_VALID_CANDIDATES = 542368
EXPECTED_PHYSICAL_FEASIBLE_CANDIDATES = 470138
EXPECTED_ALL_K_HIGH_RISK = 7783
MARGIN_SCALE = 0.1
MARGIN_CLIP = 2.0
CVAR_ALPHA = 0.9
L2_REGULARIZATION = 1e-4
MAX_ITERATIONS = 20
ACCEPTANCE_GAP = 1e-6
SOLVER = "CLARABEL"
SOLVER_OPTIONS = (
    ("tol_gap_abs", 1e-10),
    ("tol_gap_rel", 1e-10),
    ("tol_feas", 1e-10),
)
MINIMUM_FREE_BYTES = 10 * 1024**3
TRAINING_LOCK = Path("/root/autodl-tmp/.camp_dp_v24_convex_training.lock")
CORPUS_LOCK = Path("/root/autodl-tmp/.camp_dp_v24_native_corpus_remaining.lock")
LABEL_LOCK = Path(
    "/root/autodl-tmp/.camp_dp_v24_training_label_materialization.lock"
)
EXECUTOR_PROVENANCE_FILES = (
    "scripts/integrations/train_diffusion_planner_v24_selector.py",
    "scripts/integrations/preflight_diffusion_planner_v24_training_executor.py",
    "scripts/integrations/review_diffusion_planner_v24_training_executor_preflight.py",
    "scripts/integrations/review_diffusion_planner_v24_training_execution_failure.py",
    "scripts/integrations/review_diffusion_planner_v24_training_retry_failure.py",
    "configs/integrations/diffusion_planner_v24_convex_training_plan.json",
    "camp_core/camp_core/outer_master/robust_margin_master.py",
    "scripts/integrations/preflight_diffusion_planner_v24_convex_training.py",
    "scripts/integrations/review_diffusion_planner_v24_atom_availability.py",
)
PLAN_STABLE_PROVENANCE_FILES = (
    "configs/integrations/diffusion_planner_v24_convex_training_plan.json",
    "camp_core/camp_core/outer_master/robust_margin_master.py",
    "scripts/integrations/preflight_diffusion_planner_v24_convex_training.py",
    "scripts/integrations/review_diffusion_planner_v24_atom_availability.py",
)


@dataclass
class V24CuttingPlaneResult:
    raw_static_weights: np.ndarray
    train_violations: np.ndarray
    final_master_gap: float
    projected_train_violations: np.ndarray
    final_projected_master_gap: float
    final_raw_cut_gap: float
    final_projected_cut_gap: float
    history: list[dict[str, Any]]
    converged: bool
    final_cut_mask: np.ndarray
    final_master_losses: np.ndarray
    solver_status: str
    solver_name: str
    registry_receipt: dict[str, Any]


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _git_blob_bytes(repo: Path, head: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def tracked_source_provenance(
    *, repo: Path, current_head: str
) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for relative in EXECUTOR_PROVENANCE_FILES:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        live = (Path(repo) / relative).read_bytes()
        current = _git_blob_bytes(Path(repo), current_head, relative)
        blob = subprocess.run(
            ["git", "rev-parse", f"{current_head}:{relative}"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if live != current or len(blob) != 40 or set(blob) - set("0123456789abcdef"):
            raise ValueError(f"training source is not tracked at current HEAD: {relative}")
        stable = relative in PLAN_STABLE_PROVENANCE_FILES
        if stable and live != _git_blob_bytes(Path(repo), PLAN_SOURCE_HEAD, relative):
            raise ValueError(f"frozen convex source changed after Gate 36: {relative}")
        receipts[relative] = {
            "git_blob": blob,
            "sha256": hashlib.sha256(live).hexdigest(),
            "matches_current_head": True,
            "matches_plan_source_head": stable,
        }
    return receipts


@contextmanager
def clarabel_only_solver_registry() -> Iterator[dict[str, Any]]:
    """Expose only CLARABEL to the frozen master for this process-local solve."""
    import cvxpy as cp

    installed = tuple(sorted(str(name).upper() for name in cp.installed_solvers()))
    if SOLVER not in installed:
        raise RuntimeError("CLARABEL is not installed")
    original = cp.installed_solvers
    cp.installed_solvers = lambda: [SOLVER]
    try:
        if cp.installed_solvers() != [SOLVER]:
            raise RuntimeError("CLARABEL-only solver registry could not be frozen")
        yield {
            "installed_solvers_before_scope": list(installed),
            "solvers_exposed_to_master": [SOLVER],
            "fallback_solvers_exposed": [],
        }
    finally:
        cp.installed_solvers = original


def empirical_cvar_fast(losses: np.ndarray, alpha: float) -> tuple[float, float]:
    values = np.asarray(losses, dtype=np.float64).reshape(-1)
    if values.size == 0 or not np.isfinite(values).all() or not 0.0 <= alpha < 1.0:
        raise ValueError("CVaR losses and alpha are invalid")
    ordered = np.sort(values)
    candidates = np.unique(ordered)
    right = np.searchsorted(ordered, candidates, side="right")
    suffix = np.concatenate(
        [np.cumsum(ordered[::-1], dtype=np.float64)[::-1], np.asarray([0.0])]
    )
    counts = values.size - right
    excess = suffix[right] - candidates * counts
    objectives = candidates + excess / ((1.0 - float(alpha)) * values.size)
    best = int(np.argmin(objectives))
    return float(objectives[best]), float(candidates[best])


def _lock_is_free(path: Path) -> bool:
    import fcntl

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _cut_mask(cuts: Sequence[set[int]], candidate_count: int) -> np.ndarray:
    mask = np.zeros((len(cuts), candidate_count), dtype=bool)
    for row, indices in enumerate(cuts):
        for index in indices:
            if index < 0 or index >= candidate_count:
                raise ValueError("cut candidate index is out of range")
            mask[row, index] = True
    return mask


def cut_and_full_loss_details(
    normalized_atoms: np.ndarray,
    weights: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    feasible_mask: np.ndarray,
    final_cut_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    atoms = np.asarray(normalized_atoms, dtype=np.float64)
    feasible = np.asarray(feasible_mask)
    cuts = np.asarray(final_cut_mask)
    oracle = np.asarray(oracle_indices, dtype=np.int64)
    if feasible.dtype != np.bool_ or cuts.dtype != np.bool_:
        raise ValueError("full-K feasible and cut masks must be strict booleans")
    if feasible.shape != atoms.shape[:2] or cuts.shape != atoms.shape[:2]:
        raise ValueError("full-K feasible/cut masks must match atom rows")
    oracle_atoms = atoms[np.arange(atoms.shape[0]), oracle]
    values = np.asarray(margins, dtype=np.float64) + np.einsum(
        "nkr,r->nk", oracle_atoms[:, None, :] - atoms, weights
    )
    values[~feasible] = -np.inf
    full_losses = np.maximum(np.max(values, axis=1), 0.0)
    cut_values = np.where(cuts & feasible, values, -np.inf)
    if not np.isfinite(np.max(cut_values, axis=1)).all():
        raise ValueError("every snapshot must retain at least one feasible final cut")
    cut_losses = np.maximum(np.max(cut_values, axis=1), 0.0)
    gaps = np.maximum(full_losses - cut_losses, 0.0)
    return full_losses, cut_losses, gaps


def cut_and_full_losses(
    normalized_atoms: np.ndarray,
    weights: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    feasible_mask: np.ndarray,
    final_cut_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, int]:
    full_losses, cut_losses, gaps = cut_and_full_loss_details(
        normalized_atoms,
        weights,
        oracle_indices,
        margins,
        feasible_mask,
        final_cut_mask,
    )
    omitted = int(np.sum(gaps > ACCEPTANCE_GAP))
    return full_losses, cut_losses, float(np.max(gaps)), omitted


def solve_v24_cutting_plane(
    normalized_atoms: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    config: RobustMarginConfig,
    features: Any = None,
    master_solver: Callable[..., Any] = _solve_master,
    solver_scope: Callable[[], Any] = clarabel_only_solver_registry,
) -> V24CuttingPlaneResult:
    config.validate()
    atoms = np.asarray(normalized_atoms, dtype=np.float64)
    feasible = np.asarray(feasible_mask)
    oracle = np.asarray(oracle_indices, dtype=np.int64)
    margin_values = np.asarray(margins, dtype=np.float64)
    if (
        config.mode != "static"
        or config.risk_type != "cvar"
        or config.alpha != CVAR_ALPHA
        or config.l2_reg != L2_REGULARIZATION
        or config.max_iter != MAX_ITERATIONS
        or config.tolerance != ACCEPTANCE_GAP
        or config.solver != SOLVER
        or config.solver_options != SOLVER_OPTIONS
        or config.static_weight_lower_bounds != tuple([0.0] * 14)
        or features is not None
    ):
        raise ValueError("v24 cutting-plane config differs from the frozen master")
    if (
        atoms.ndim != 3
        or atoms.shape[1:] != (8, 14)
        or atoms.shape[0] == 0
        or not np.isfinite(atoms).all()
        or np.any(atoms < 0.0)
        or feasible.dtype != np.bool_
        or feasible.shape != atoms.shape[:2]
        or margin_values.shape != atoms.shape[:2]
        or not np.isfinite(margin_values).all()
        or np.any(margin_values < 0.0)
        or oracle.shape != (atoms.shape[0],)
        or not feasible[np.arange(atoms.shape[0]), oracle].all()
    ):
        raise ValueError("v24 cutting-plane arrays are invalid")
    cuts: list[set[int]] = [set() for _ in range(atoms.shape[0])]
    uniform = np.full(14, 1.0 / 14.0, dtype=np.float64)
    _, _, initial_worst = candidate_ranking_violations(
        atoms, uniform, oracle, margin_values, feasible
    )
    for row, candidate in enumerate(initial_worst):
        cuts[row].add(int(candidate))
    history: list[dict[str, Any]] = []
    raw_weights: Optional[np.ndarray] = None
    master_losses = np.zeros(atoms.shape[0], dtype=np.float64)
    solver_status = "not_solved"
    solver_name = "not_solved"
    converged = False
    with solver_scope() as registry_receipt:
        for iteration in range(1, MAX_ITERATIONS + 1):
            (
                raw_weights,
                theta,
                master_losses,
                solver_status,
                solver_name,
                master_objective,
            ) = master_solver(
                atoms, oracle, margin_values, cuts, config, None
            )
            if raw_weights is None or not np.isfinite(raw_weights).all():
                raise RuntimeError("v24 CLARABEL returned invalid static weights")
            if theta is not None or solver_name != SOLVER or solver_status != "optimal":
                raise RuntimeError("v24 requires exact optimal static CLARABEL")
            _, raw_true_losses, raw_worst = candidate_ranking_violations(
                atoms, raw_weights, oracle, margin_values, feasible
            )
            projected_weights = project_simplex_rows(raw_weights)[0]
            _, projected_true_losses, projected_worst = candidate_ranking_violations(
                atoms, projected_weights, oracle, margin_values, feasible
            )
            current_cut_mask = _cut_mask(cuts, atoms.shape[1])
            raw_full_losses, _, raw_cut_gap = cut_and_full_loss_details(
                atoms,
                raw_weights,
                oracle,
                margin_values,
                feasible,
                current_cut_mask,
            )
            projected_full_losses, _, projected_cut_gap = cut_and_full_loss_details(
                atoms,
                projected_weights,
                oracle,
                margin_values,
                feasible,
                current_cut_mask,
            )
            if not np.allclose(
                raw_true_losses, raw_full_losses, rtol=0.0, atol=1e-12
            ) or not np.allclose(
                projected_true_losses,
                projected_full_losses,
                rtol=0.0,
                atol=1e-12,
            ):
                raise RuntimeError("cut separation full-K recomputation drift")
            raw_master_gap = np.maximum(raw_true_losses - master_losses, 0.0)
            projected_master_gap = np.maximum(
                projected_true_losses - master_losses, 0.0
            )
            raw_max_master_gap = float(np.max(raw_master_gap))
            projected_max_master_gap = float(np.max(projected_master_gap))
            raw_max_cut_gap = float(np.max(raw_cut_gap))
            projected_max_cut_gap = float(np.max(projected_cut_gap))
            max_master_gap = max(raw_max_master_gap, projected_max_master_gap)
            max_cut_gap = max(raw_max_cut_gap, projected_max_cut_gap)
            max_gap = max(max_master_gap, max_cut_gap)
            new_cuts = 0
            for row, (raw_candidate, projected_candidate) in enumerate(
                zip(raw_worst, projected_worst)
            ):
                for candidate, row_gap in (
                    (
                        int(raw_candidate),
                        max(raw_master_gap[row], raw_cut_gap[row]),
                    ),
                    (
                        int(projected_candidate),
                        max(projected_master_gap[row], projected_cut_gap[row]),
                    ),
                ):
                    if candidate not in cuts[row] and row_gap > ACCEPTANCE_GAP:
                        cuts[row].add(candidate)
                        new_cuts += 1
            history.append(
                {
                    "iteration": iteration,
                    "master_objective": float(master_objective),
                    "exact_cvar": empirical_cvar_fast(
                        projected_true_losses, CVAR_ALPHA
                    )[0],
                    "raw_mean_violation": float(np.mean(raw_true_losses)),
                    "raw_max_violation": float(np.max(raw_true_losses)),
                    "projected_mean_violation": float(
                        np.mean(projected_true_losses)
                    ),
                    "projected_max_violation": float(np.max(projected_true_losses)),
                    "raw_max_master_gap": raw_max_master_gap,
                    "projected_max_master_gap": projected_max_master_gap,
                    "max_master_gap": max_master_gap,
                    "raw_max_cut_gap": raw_max_cut_gap,
                    "projected_max_cut_gap": projected_max_cut_gap,
                    "max_cut_gap": max_cut_gap,
                    "max_separation_gap": max_gap,
                    "new_cuts": new_cuts,
                    "total_cuts": int(sum(len(row) for row in cuts)),
                    "final_resolve": False,
                }
            )
            if max_gap <= ACCEPTANCE_GAP and new_cuts == 0:
                converged = True
                break
            if new_cuts == 0:
                raise RuntimeError("cut generation stalled above tolerance")
    if not converged or raw_weights is None:
        raise RuntimeError("v24 cutting plane did not converge within 20 iterations")
    _, true_losses, _ = candidate_ranking_violations(
        atoms, raw_weights, oracle, margin_values, feasible
    )
    projected_weights = project_simplex_rows(raw_weights)[0]
    _, projected_true_losses, _ = candidate_ranking_violations(
        atoms, projected_weights, oracle, margin_values, feasible
    )
    final_gap = float(np.max(np.maximum(true_losses - master_losses, 0.0)))
    final_projected_gap = float(
        np.max(np.maximum(projected_true_losses - master_losses, 0.0))
    )
    final_cut_mask = _cut_mask(cuts, atoms.shape[1])
    _, _, raw_cut_gap = cut_and_full_loss_details(
        atoms,
        raw_weights,
        oracle,
        margin_values,
        feasible,
        final_cut_mask,
    )
    _, _, projected_cut_gap = cut_and_full_loss_details(
        atoms,
        projected_weights,
        oracle,
        margin_values,
        feasible,
        final_cut_mask,
    )
    return V24CuttingPlaneResult(
        raw_static_weights=np.asarray(raw_weights, dtype=np.float64),
        train_violations=true_losses,
        final_master_gap=final_gap,
        projected_train_violations=projected_true_losses,
        final_projected_master_gap=final_projected_gap,
        final_raw_cut_gap=float(np.max(raw_cut_gap)),
        final_projected_cut_gap=float(np.max(projected_cut_gap)),
        history=history,
        converged=True,
        final_cut_mask=final_cut_mask,
        final_master_losses=np.asarray(master_losses, dtype=np.float64),
        solver_status=solver_status,
        solver_name=solver_name,
        registry_receipt=dict(registry_receipt),
    )


def prepare_training_problem(
    atoms: np.ndarray,
    candidate_cost: np.ndarray,
    source_valid: np.ndarray,
    oracle_index: np.ndarray,
    *,
    frozen_scales: np.ndarray,
) -> dict[str, np.ndarray]:
    matrix = np.asarray(atoms, dtype=np.float64)
    costs = np.asarray(candidate_cost, dtype=np.float64)
    valid = np.asarray(source_valid)
    oracle = np.asarray(oracle_index)
    scales = np.asarray(frozen_scales, dtype=np.float64)
    if matrix.ndim != 3 or matrix.shape[1:] != (8, 14):
        raise ValueError("v24 atoms must have shape [N,8,14]")
    if costs.shape != matrix.shape[:2] or valid.shape != matrix.shape[:2]:
        raise ValueError("v24 costs and source-valid mask must match [N,8]")
    if valid.dtype != np.bool_:
        raise ValueError("source-valid mask must contain strict booleans")
    if oracle.dtype.kind not in {"u", "i"} or oracle.shape != (matrix.shape[0],):
        raise ValueError("oracle index must be an integer vector matching snapshots")
    if scales.shape != (14,) or not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("frozen v24 scales must be finite positive 14D")
    if (
        not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not np.isfinite(costs).all()
        or np.any(costs < 0.0)
        or np.any(oracle < 0)
        or np.any(oracle >= 8)
        or not valid[np.arange(matrix.shape[0]), oracle].all()
        or not valid.any(axis=1).all()
    ):
        raise ValueError("v24 training arrays violate finite/source-valid authority")
    independent_oracle = np.argmin(np.where(valid, costs, np.inf), axis=1)
    if not np.array_equal(oracle.astype(np.int64), independent_oracle):
        raise ValueError("stored oracle differs from causal candidate costs")
    normalized = np.clip(matrix / scales.reshape(1, 1, 14), 0.0, 10.0)
    oracle_cost = costs[np.arange(costs.shape[0]), independent_oracle]
    margins = np.clip(
        MARGIN_SCALE * (costs - oracle_cost[:, None]), 0.0, MARGIN_CLIP
    )
    margins[~valid] = 0.0
    margins[np.arange(margins.shape[0]), independent_oracle] = 0.0
    return {
        "normalized_atoms": normalized,
        "candidate_cost": costs,
        "source_valid_mask": valid,
        "oracle_indices": independent_oracle.astype(np.int64),
        "margins": margins,
    }


def accepted_weights_and_gap(
    result: V24CuttingPlaneResult,
    normalized_atoms: np.ndarray,
    oracle: np.ndarray,
    margins: np.ndarray,
    feasible: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, dict[str, Any]]:
    history = list(result.history)
    if result.solver_name != SOLVER or result.solver_status != "optimal":
        raise RuntimeError("exact optimal CLARABEL status is required")
    if not result.converged or not history:
        raise RuntimeError("cutting-plane master must converge with history")
    if (
        len(history) > MAX_ITERATIONS
        or [row.get("iteration") for row in history]
        != list(range(1, len(history) + 1))
    ):
        raise RuntimeError("cutting-plane master exceeded the frozen iteration cap")
    if any(row.get("final_resolve") is not False for row in history):
        raise RuntimeError("post-cap final-resolve is forbidden for v24")
    if any(
        type(row.get("new_cuts")) is not int
        or row["new_cuts"] < 0
        or not np.isfinite(row.get("max_master_gap", np.nan))
        or not np.isfinite(row.get("raw_max_cut_gap", np.nan))
        or not np.isfinite(row.get("projected_max_cut_gap", np.nan))
        or not np.isfinite(row.get("max_separation_gap", np.nan))
        or row["raw_max_cut_gap"] < 0.0
        or row["projected_max_cut_gap"] < 0.0
        or row["max_separation_gap"] < 0.0
        for row in history
    ):
        raise RuntimeError("cutting-plane history receipt is invalid")
    if history[-1].get("new_cuts") != 0:
        raise RuntimeError("final cutting-plane iteration must add zero cuts")
    if result.registry_receipt.get("solvers_exposed_to_master") != [SOLVER] or result.registry_receipt.get(
        "fallback_solvers_exposed"
    ) != []:
        raise RuntimeError("CLARABEL-only solver registry receipt is invalid")
    if (
        not np.isfinite(result.final_master_gap)
        or result.final_master_gap < 0.0
        or result.final_master_gap > ACCEPTANCE_GAP
    ):
        raise RuntimeError("raw full-K master gap exceeds the frozen tolerance")
    if (
        not np.isfinite(result.final_projected_master_gap)
        or result.final_projected_master_gap < 0.0
        or result.final_projected_master_gap > ACCEPTANCE_GAP
    ):
        raise RuntimeError("projected full-K master gap exceeds the frozen tolerance")
    if (
        not np.isfinite(result.final_raw_cut_gap)
        or result.final_raw_cut_gap < 0.0
        or result.final_raw_cut_gap > ACCEPTANCE_GAP
    ):
        raise RuntimeError("raw full-K cut gap exceeds the frozen tolerance")
    if (
        not np.isfinite(result.final_projected_cut_gap)
        or result.final_projected_cut_gap < 0.0
        or result.final_projected_cut_gap > ACCEPTANCE_GAP
    ):
        raise RuntimeError("projected full-K cut gap exceeds the frozen tolerance")
    raw = np.asarray(result.raw_static_weights, dtype=np.float64).reshape(-1)
    if raw.shape != (14,) or not np.isfinite(raw).all():
        raise RuntimeError("static v24 weights have invalid shape or values")
    if np.any(raw < -1e-8) or not np.isclose(raw.sum(), 1.0, atol=1e-8, rtol=0.0):
        raise RuntimeError("static v24 weights violate the nonnegative simplex")
    weights = project_simplex_rows(raw)[0]
    full_losses, cut_losses, projected_gap, omitted = cut_and_full_losses(
        normalized_atoms,
        weights,
        oracle,
        margins,
        feasible,
        result.final_cut_mask,
    )
    if omitted != 0 or not np.isfinite(projected_gap) or projected_gap > ACCEPTANCE_GAP:
        raise RuntimeError("projected saved-weight full-K gap exceeds tolerance")
    if projected_gap != result.final_projected_cut_gap:
        raise RuntimeError("projected cut-gap receipt differs from full-K recomputation")
    if not np.array_equal(
        np.asarray(result.projected_train_violations, dtype=np.float64), full_losses
    ):
        raise RuntimeError(
            "projected CLARABEL weights fail independent full-K recomputation"
        )
    raw_full_losses, _, raw_cut_gap, raw_omitted = cut_and_full_losses(
        normalized_atoms,
        raw,
        oracle,
        margins,
        feasible,
        result.final_cut_mask,
    )
    if (
        raw_omitted != 0
        or raw_cut_gap > ACCEPTANCE_GAP
        or raw_cut_gap != result.final_raw_cut_gap
        or not np.array_equal(
            np.asarray(result.train_violations, dtype=np.float64), raw_full_losses
        )
    ):
        raise RuntimeError("raw CLARABEL weights fail independent full-K recomputation")
    cuts = np.sum(result.final_cut_mask, axis=1, dtype=np.int64)
    if cuts.shape != (normalized_atoms.shape[0],) or np.any(cuts < 1) or np.any(cuts > 8):
        raise RuntimeError("cut receipts must contain one through eight cuts per snapshot")
    receipt = {
        "raw_weights": raw.tolist(),
        "projected_weights": weights.tolist(),
        "simplex_projection_linf": float(np.max(np.abs(weights - raw))),
        "full_k_loss_mean": float(np.mean(full_losses)),
        "full_k_loss_maximum": float(np.max(full_losses)),
        "final_cut_loss_mean": float(np.mean(cut_losses)),
        "projected_saved_weight_full_k_gap": projected_gap,
        "raw_saved_weight_full_k_gap": raw_cut_gap,
        "raw_final_master_gap": result.final_master_gap,
        "projected_final_master_gap": result.final_projected_master_gap,
        "omitted_violating_snapshot_count": omitted,
        "cut_count_histogram": np.bincount(cuts, minlength=9).astype(int).tolist(),
        "total_cuts": int(cuts.sum()),
    }
    return weights, full_losses, projected_gap, receipt


def train_level(
    *,
    level_percent: int,
    atoms: np.ndarray,
    candidate_cost: np.ndarray,
    source_valid: np.ndarray,
    oracle_index: np.ndarray,
    frozen_scales: np.ndarray,
    snapshot_sha256: Sequence[str],
    route_membership_sha256: str,
    route_count: int,
    retained_route_seed_count: int,
    complete_route_seed_count: int,
    failed_route_seed_count: int,
    solver: Callable[..., Any] = solve_v24_cutting_plane,
) -> dict[str, Any]:
    digests = list(snapshot_sha256)
    if (
        level_percent not in EXPECTED_LEVELS
        or len(digests) != np.asarray(atoms).shape[0]
        or any(not _is_sha256(value) for value in digests)
        or not _is_sha256(route_membership_sha256)
    ):
        raise ValueError("learning-curve level identity or snapshot SHA drift")
    problem = prepare_training_problem(
        atoms,
        candidate_cost,
        source_valid,
        oracle_index,
        frozen_scales=frozen_scales,
    )
    config = RobustMarginConfig(
        mode="static",
        risk_type="cvar",
        alpha=CVAR_ALPHA,
        l2_reg=L2_REGULARIZATION,
        max_iter=MAX_ITERATIONS,
        tolerance=ACCEPTANCE_GAP,
        solver=SOLVER,
        static_weight_lower_bounds=tuple(np.zeros(14, dtype=np.float64)),
        solver_options=SOLVER_OPTIONS,
    )
    started = time.perf_counter()
    result = solver(
        problem["normalized_atoms"],
        problem["oracle_indices"],
        problem["margins"],
        problem["source_valid_mask"],
        config=config,
        features=None,
    )
    wall_clock = time.perf_counter() - started
    weights, violations, projected_gap, cut_receipt = accepted_weights_and_gap(
        result,
        problem["normalized_atoms"],
        problem["oracle_indices"],
        problem["margins"],
        problem["source_valid_mask"],
    )
    scores = np.einsum("nkr,r->nk", problem["normalized_atoms"], weights)
    selected = np.argmin(
        np.where(problem["source_valid_mask"], scores, np.inf), axis=1
    )
    rows = np.arange(selected.size)
    selected_cost = problem["candidate_cost"][rows, selected]
    histogram = np.bincount(selected, minlength=8).astype(int).tolist()
    return {
        "schema": "camp_dp_v24_static_affine_selector_model_v1",
        "level_percent": int(level_percent),
        "diagnostic_only": level_percent != 100,
        "primary_model": level_percent == 100,
        "snapshot_count": len(digests),
        "snapshot_sequence_sha256": hashlib.sha256(
            ("\n".join(digests) + "\n").encode("ascii")
        ).hexdigest(),
        "route_membership_sha256": route_membership_sha256,
        "route_count": int(route_count),
        "retained_route_seed_count": int(retained_route_seed_count),
        "complete_route_seed_count": int(complete_route_seed_count),
        "failed_route_seed_count": int(failed_route_seed_count),
        "atom_schema_version": "dp_camp_v10_14d",
        "atom_names": list(DP_CAMP_ATOM_NAMES_V10),
        "atom_scales": np.asarray(frozen_scales, dtype=np.float64).tolist(),
        "active_atom_mask": [True] * 14,
        "raw_weights": cut_receipt["raw_weights"],
        "weights": weights.tolist(),
        "simplex_sum": float(weights.sum()),
        "minimum_weight": float(weights.min()),
        "score_contract": "score_k(w)=a_k^T w",
        "atom_transform": "clip(raw_atom/frozen_v24_scale,0,10)",
        "oracle_eligibility": "source_valid_mask_only",
        "train_metrics": {
            "oracle_agreement_count": int(
                np.sum(selected == problem["oracle_indices"])
            ),
            "oracle_agreement_rate": float(
                np.mean(selected == problem["oracle_indices"])
            ),
            "selection_histogram": histogram,
            "candidate0_selection_count": histogram[0],
            "non_candidate0_selection_count": int(selected.size - histogram[0]),
            "selected_surrogate_cost_mean": float(np.mean(selected_cost)),
            "candidate0_surrogate_cost_mean": float(
                np.mean(problem["candidate_cost"][:, 0])
            ),
            "selected_minus_candidate0_surrogate_cost_mean": float(
                np.mean(selected_cost - problem["candidate_cost"][:, 0])
            ),
            "mean_ranking_violation": float(np.mean(violations)),
            "maximum_ranking_violation": float(np.max(violations)),
        },
        "solver": {
            "name": result.solver_name,
            "status": result.solver_status,
            "risk_type": "cvar",
            "cvar_alpha": CVAR_ALPHA,
            "l2_regularization": L2_REGULARIZATION,
            "l2_center": "uniform_over_frozen_active_atoms",
            "static_weight_lower_bounds": [0.0] * 14,
            "solver_options": dict(SOLVER_OPTIONS),
            "solver_default_initialization": True,
            "v18_v22_weights_loaded": False,
            "fallback_allowed": False,
            "registry_receipt": result.registry_receipt,
            "iterations": len(result.history),
            "history": list(result.history),
            "cut_count_histogram": cut_receipt["cut_count_histogram"],
            "total_cuts": cut_receipt["total_cuts"],
            "raw_full_k_gap": float(result.final_master_gap),
            "projected_full_k_gap": float(result.final_projected_master_gap),
            "raw_master_gap": float(result.final_master_gap),
            "projected_master_gap": float(result.final_projected_master_gap),
            "raw_cut_relative_gap": float(result.final_raw_cut_gap),
            "projected_cut_relative_gap": float(result.final_projected_cut_gap),
            "projected_saved_weight_full_k_gap": projected_gap,
            "final_new_cuts": int(result.history[-1]["new_cuts"]),
            "converged": bool(result.converged),
            "offline_wall_clock_s": float(wall_clock),
            "epoch_semantics": False,
        },
        "final_cut_receipt": cut_receipt,
        "_final_cut_mask": result.final_cut_mask,
        "actual_closed_loop_outcomes_read": False,
        "identity_fields_used_as_feature": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }


def _strict_u8(path: Path, shape: tuple[int, ...], *, boolean: bool) -> np.ndarray:
    array = np.fromfile(path, dtype=np.uint8)
    if array.size != int(np.prod(shape)):
        raise ValueError(f"v24 label column size mismatch: {path.name}")
    array = array.reshape(shape)
    if boolean and not np.isin(array, [0, 1]).all():
        raise ValueError(f"v24 boolean label column is not binary: {path.name}")
    return array


def _verify_label_payload_receipts(label: Mapping[str, Any]) -> None:
    expected_columns = {
        "candidate_cost": ("candidate_cost.f64le", "<f8", [EXPECTED_SNAPSHOTS, 8]),
        "oracle_index": ("oracle_index.u8", "u1", [EXPECTED_SNAPSHOTS]),
        "source_valid_mask": (
            "source_valid_mask.u8",
            "u1_bool",
            [EXPECTED_SNAPSHOTS, 8],
        ),
        "physical_feasible_mask": (
            "physical_feasible_mask.u8",
            "u1_bool",
            [EXPECTED_SNAPSHOTS, 8],
        ),
        "all_k_high_risk": (
            "all_k_high_risk.u8",
            "u1_bool",
            [EXPECTED_SNAPSHOTS],
        ),
    }
    expected_files = {
        "snapshot_sha256.txt",
        "snapshot_provenance.jsonl",
        *(value[0] for value in expected_columns.values()),
    }
    columns = label.get("columns")
    receipts = label.get("file_receipts")
    if not isinstance(columns, Mapping) or set(columns) != set(expected_columns):
        raise ValueError("v24 label column contract drift")
    if not isinstance(receipts, Mapping) or set(receipts) != expected_files:
        raise ValueError("v24 label file receipt inventory drift")
    for name, (filename, dtype, shape) in expected_columns.items():
        if columns.get(name) != {"file": filename, "dtype": dtype, "shape": shape}:
            raise ValueError(f"v24 label column metadata drift: {name}")
    for filename in sorted(expected_files):
        path = LABEL_ARTIFACT / filename
        receipt = receipts.get(filename)
        if (
            not isinstance(receipt, Mapping)
            or receipt.get("sha256") != _file_sha256(path)
            or receipt.get("bytes") != path.stat().st_size
        ):
            raise ValueError(f"v24 label payload receipt drift: {filename}")


def _validate_route_rows(
    routes: Sequence[Mapping[str, Any]],
) -> tuple[set[str], dict[str, Mapping[str, Any]]]:
    route_ids: set[str] = set()
    route_by_id: dict[str, Mapping[str, Any]] = {}
    for expected_rank, route in enumerate(routes, start=1):
        if not isinstance(route, Mapping):
            raise ValueError("v24 learning-curve route row is invalid")
        route_id = route.get("route_identity_sha256")
        included = route.get("included_learning_curve_percent")
        expected_included = [
            percent
            for percent, count in zip(EXPECTED_LEVELS, EXPECTED_LEVEL_ROUTES)
            if expected_rank <= count
        ]
        complete = route.get("complete_route_seed_count")
        failed = route.get("failed_route_seed_count")
        if (
            not _is_sha256(route_id)
            or route_id in route_ids
            or route.get("route_order_rank") != expected_rank
            or route.get("seeds") != list(EXPECTED_SEEDS)
            or route.get("retained_route_seed_count") != len(EXPECTED_SEEDS)
            or type(complete) is not int
            or type(failed) is not int
            or complete < 0
            or failed < 0
            or complete + failed != len(EXPECTED_SEEDS)
            or included != expected_included
            or not _is_sha256(route.get("route_order_key_sha256"))
            or not _is_sha256(route.get("logical_map_sha256"))
            or not _is_sha256(route.get("corridor_group_sha256"))
        ):
            raise ValueError("v24 learning-curve route provenance drift")
        route_ids.add(str(route_id))
        route_by_id[str(route_id)] = route
    return route_ids, route_by_id


def _valid_provenance_phase_seed(phase: Any, seed: Any) -> bool:
    return bool(
        type(seed) is int
        and seed in EXPECTED_SEEDS
        and (
            (seed == EXPECTED_SEEDS[0] and phase == "pilot")
            or (seed != EXPECTED_SEEDS[0] and phase == "remaining")
        )
    )


def load_training_inputs() -> dict[str, Any]:
    verify_complete_seal(PLAN_ARTIFACT, PLAN_ROOT_SHA256)
    verify_complete_seal(LABEL_ARTIFACT, LABEL_ROOT_SHA256)
    verify_complete_seal(LABEL_REVIEW_ARTIFACT, LABEL_REVIEW_ROOT_SHA256)
    verify_complete_seal(MERGED_ARTIFACT, MERGED_ROOT_SHA256)
    for root in (PLAN_ARTIFACT, LABEL_ARTIFACT, LABEL_REVIEW_ARTIFACT, MERGED_ARTIFACT):
        if (
            (root / "run.exit").read_text(encoding="ascii") != "0\n"
            or (root / "stderr.txt").read_text(encoding="utf-8") != ""
        ):
            raise ValueError("v24 training source execution receipt is not clean")
    plan = _read_json(PLAN_ARTIFACT / "training_plan_preflight.json")
    label = _read_json(LABEL_ARTIFACT / "label_manifest.json")
    review = _read_json(LABEL_REVIEW_ARTIFACT / "review.json")
    merged = _read_json(MERGED_ARTIFACT / "merged_summary.json")
    config_bytes = (ROOT / CONFIG_RELATIVE).read_bytes()
    _verify_label_payload_receipts(label)
    if (
        plan.get("schema") != "camp_dp_v24_convex_training_static_preflight_v1"
        or plan.get("status") != "passed"
        or plan.get("camp_head") != PLAN_SOURCE_HEAD
        or plan.get("fixed_dp_head") != FIXED_DP_HEAD
        or plan.get("config_sha256") != hashlib.sha256(config_bytes).hexdigest()
        or label.get("status") != "passed"
        or label.get("schema") != "camp_dp_v24_train_causal_label_manifest_v1"
        or label.get("camp_head") != LABEL_SOURCE_HEAD
        or label.get("fixed_dp_head") != FIXED_DP_HEAD
        or label.get("source_preflight_artifact") != str(PLAN_ARTIFACT)
        or label.get("source_preflight_root_sha256") != PLAN_ROOT_SHA256
        or label.get("route_plan_sha256") != plan.get("route_plan_sha256")
        or label.get("label_contract") != plan.get("label_contract")
        or label.get("snapshot_count") != EXPECTED_SNAPSHOTS
        or label.get("candidate_count") != EXPECTED_CANDIDATES
        or label.get("route_count") != EXPECTED_ROUTES
        or label.get("retained_route_seed_count") != EXPECTED_ROUTE_SEEDS
        or label.get("complete_route_seed_count") != 1054
        or label.get("failed_route_seed_count") != 821
        or label.get("train_seeds") != list(EXPECTED_SEEDS)
        or label.get("source_valid_candidate_count")
        != EXPECTED_SOURCE_VALID_CANDIDATES
        or label.get("source_invalid_candidate_count") != 0
        or label.get("physical_feasible_candidate_count")
        != EXPECTED_PHYSICAL_FEASIBLE_CANDIDATES
        or label.get("all_k_high_risk_snapshot_count") != EXPECTED_ALL_K_HIGH_RISK
        or label.get("active_atom_mask") != [True] * 14
        or label.get("scale_or_mask_recomputed") is not False
        or label.get("identity_fields_used_as_label_or_feature") is not False
        or label.get("actual_closed_loop_outcomes_read") is not False
        or label.get("future_outcome_fields_read") is not False
        or review.get("status") != "passed"
        or review.get("failed_count") != 0
        or review.get("source_label_root_sha256") != LABEL_ROOT_SHA256
        or review.get("decision", {}).get(
            "training_executor_tdd_static_preflight_authorized"
        )
        is not True
        or review.get("decision", {}).get("training_execution_authorized") is not False
        or merged.get("snapshot_count") != EXPECTED_SNAPSHOTS
    ):
        raise ValueError("v24 label or plan authority is not eligible for training")
    source_authority = plan.get("source_authority")
    if not isinstance(source_authority, Mapping) or set(source_authority) != {
        "merged_train_corpus",
        "merged_train_corpus_review",
        "atom_freeze",
        "atom_freeze_review",
    }:
        raise ValueError("Gate 36 source authority is incomplete")
    source_inventories: dict[str, int] = {}
    for name, spec in source_authority.items():
        if not isinstance(spec, Mapping):
            raise ValueError("Gate 36 source authority row is invalid")
        root = Path(str(spec.get("artifact")))
        digest = spec.get("artifact_root_sha256")
        if not _is_sha256(digest):
            raise ValueError("Gate 36 source root SHA is invalid")
        source_inventories[name] = len(verify_complete_seal(root, digest))
        if (
            (root / "run.exit").read_text(encoding="ascii") != "0\n"
            or (root / "stderr.txt").read_text(encoding="utf-8") != ""
        ):
            raise ValueError("Gate 36 source execution receipt is not clean")
    if (
        label.get("source_merged_root_sha256")
        != source_authority["merged_train_corpus"]["artifact_root_sha256"]
        or label.get("source_merged_review_root_sha256")
        != source_authority["merged_train_corpus_review"]["artifact_root_sha256"]
        or label.get("source_atom_freeze_root_sha256")
        != source_authority["atom_freeze"]["artifact_root_sha256"]
        or label.get("source_atom_freeze_review_root_sha256")
        != source_authority["atom_freeze_review"]["artifact_root_sha256"]
    ):
        raise ValueError("v24 label source-root closure drift")
    direct_source_inventories: dict[str, int] = {}
    for name in ("pilot", "pilot_review", "remaining", "remaining_review"):
        spec = merged.get("source_artifacts", {}).get(name)
        if not isinstance(spec, Mapping):
            raise ValueError("merged native source authority is missing")
        raw_path = spec.get("path")
        digest = spec.get("root_sha256")
        pure = PurePosixPath(raw_path) if isinstance(raw_path, str) else None
        if (
            pure is None
            or not pure.is_absolute()
            or pure.parts[:3] != ("/", "root", "autodl-tmp")
            or ".." in pure.parts
            or not _is_sha256(digest)
        ):
            raise ValueError("merged native source path or root is invalid")
        root = Path(raw_path)
        direct_source_inventories[name] = len(verify_complete_seal(root, digest))
        if (
            (root / "run.exit").read_text(encoding="ascii") != "0\n"
            or (root / "stderr.txt").read_text(encoding="utf-8") != ""
        ):
            raise ValueError("merged native source execution receipt is not clean")
    atoms, source_valid, physical, _source_inventories = _snapshot_arrays(
        merged_root=MERGED_ARTIFACT, summary=merged
    )
    costs = np.fromfile(LABEL_ARTIFACT / "candidate_cost.f64le", dtype="<f8")
    if costs.size != EXPECTED_CANDIDATES:
        raise ValueError("candidate cost column size mismatch")
    costs = costs.reshape(EXPECTED_SNAPSHOTS, 8)
    oracle = _strict_u8(
        LABEL_ARTIFACT / "oracle_index.u8", (EXPECTED_SNAPSHOTS,), boolean=False
    )
    stored_valid = _strict_u8(
        LABEL_ARTIFACT / "source_valid_mask.u8",
        (EXPECTED_SNAPSHOTS, 8),
        boolean=True,
    ).astype(bool)
    stored_physical = _strict_u8(
        LABEL_ARTIFACT / "physical_feasible_mask.u8",
        (EXPECTED_SNAPSHOTS, 8),
        boolean=True,
    ).astype(bool)
    stored_all_k = _strict_u8(
        LABEL_ARTIFACT / "all_k_high_risk.u8",
        (EXPECTED_SNAPSHOTS,),
        boolean=True,
    ).astype(bool)
    if not np.array_equal(stored_valid, source_valid) or not np.array_equal(
        stored_physical, physical
    ):
        raise ValueError("label masks differ from sealed snapshot sources")
    independent_all_k = source_valid.all(axis=1) & ~physical.any(axis=1)
    if (
        not np.array_equal(stored_all_k, independent_all_k)
        or int(stored_all_k.sum()) != EXPECTED_ALL_K_HIGH_RISK
        or int(stored_valid.sum()) != EXPECTED_SOURCE_VALID_CANDIDATES
        or int(stored_physical.sum()) != EXPECTED_PHYSICAL_FEASIBLE_CANDIDATES
    ):
        raise ValueError("all-K-high-risk stratum differs from frozen labels")
    digest_rows = (LABEL_ARTIFACT / "snapshot_sha256.txt").read_text(
        encoding="ascii"
    ).splitlines()
    provenance = _read_jsonl(LABEL_ARTIFACT / "snapshot_provenance.jsonl")
    merged_index = _read_jsonl(MERGED_ARTIFACT / "snapshot_index.jsonl")
    if (
        len(digest_rows) != EXPECTED_SNAPSHOTS
        or len(provenance) != EXPECTED_SNAPSHOTS
        or len(merged_index) != EXPECTED_SNAPSHOTS
        or len(set(digest_rows)) != EXPECTED_SNAPSHOTS
        or any(not _is_sha256(value) for value in digest_rows)
    ):
        raise ValueError("label snapshot/provenance count mismatch")
    if [row.get("sha256") for row in merged_index] != digest_rows:
        raise ValueError("label snapshot order differs from merged zero-copy index")
    routes = _read_jsonl(PLAN_ARTIFACT / "learning_curve_routes.jsonl")
    if len(routes) != EXPECTED_ROUTES:
        raise ValueError("v24 learning-curve route count drift")
    route_ids, _route_by_id = _validate_route_rows(routes)
    seen_snapshot_keys: set[tuple[str, int, int]] = set()
    for digest, row in zip(digest_rows, provenance):
        source_relative = row.get("source_relative_path")
        pure = PurePosixPath(source_relative) if isinstance(source_relative, str) else None
        key = (
            str(row.get("route_identity_sha256")),
            row.get("seed"),
            row.get("tick_index"),
        )
        if set(row) != {
            "snapshot_sha256",
            "route_identity_sha256",
            "seed",
            "phase",
            "source_relative_path",
            "tick_index",
        } or row["snapshot_sha256"] != digest:
            raise ValueError("label provenance schema or sequence mismatch")
        if (
            row.get("route_identity_sha256") not in route_ids
            or not _valid_provenance_phase_seed(row.get("phase"), row.get("seed"))
            or pure is None
            or pure.is_absolute()
            or ".." in pure.parts
            or type(row.get("tick_index")) is not int
            or row.get("tick_index") < 0
            or key in seen_snapshot_keys
        ):
            raise ValueError("label provenance identity boundary drift")
        seen_snapshot_keys.add(key)
    levels = plan.get("learning_curve_levels")
    if (
        not isinstance(levels, list)
        or len(levels) != len(EXPECTED_LEVELS)
        or label.get("learning_curve_levels") != levels
    ):
        raise ValueError("v24 learning-curve route authority is invalid")
    level_indices: dict[int, np.ndarray] = {}
    route_id_by_snapshot = np.asarray(
        [row["route_identity_sha256"] for row in provenance], dtype="U64"
    )
    for (
        percent,
        route_count,
        snapshot_count,
        retained_count,
        complete_count,
        failed_count,
        level,
    ) in zip(
        EXPECTED_LEVELS,
        EXPECTED_LEVEL_ROUTES,
        EXPECTED_LEVEL_SNAPSHOTS,
        EXPECTED_LEVEL_ROUTE_SEEDS,
        EXPECTED_LEVEL_COMPLETE,
        EXPECTED_LEVEL_FAILED,
        levels,
    ):
        route_ids = {row["route_identity_sha256"] for row in routes[:route_count]}
        indices = np.flatnonzero(np.isin(route_id_by_snapshot, list(route_ids)))
        membership_sha256 = hashlib.sha256(
            _canonical_json_bytes(
                [row["route_identity_sha256"] for row in routes[:route_count]]
            )
        ).hexdigest()
        if (
            level.get("percent") != percent
            or level.get("route_count") != route_count
            or level.get("snapshot_count") != snapshot_count
            or level.get("retained_route_seed_count") != retained_count
            or level.get("complete_route_seed_count") != complete_count
            or level.get("failed_route_seed_count") != failed_count
            or level.get("route_membership_sha256") != membership_sha256
            or level.get("primary_model") is not (percent == 100)
            or level.get("diagnostic_only") is not (percent != 100)
            or indices.size != snapshot_count
        ):
            raise ValueError("v24 whole-route learning-curve prefix drift")
        level_indices[percent] = indices
    if not all(
        set(level_indices[left]).issubset(set(level_indices[right]))
        for left, right in zip(EXPECTED_LEVELS, EXPECTED_LEVELS[1:])
    ):
        raise ValueError("v24 learning-curve snapshot prefixes are not nested")
    return {
        "atoms": atoms,
        "candidate_cost": costs,
        "source_valid_mask": stored_valid,
        "physical_feasible_mask": stored_physical,
        "all_k_high_risk": stored_all_k,
        "oracle_index": oracle,
        "atom_scales": np.asarray(label["atom_scales"], dtype=np.float64),
        "snapshot_sha256": digest_rows,
        "route_rows": routes,
        "levels": levels,
        "level_indices": level_indices,
        "failure_reason_counts": label["failure_reason_counts"],
        "source_verified_file_counts": source_inventories,
        "direct_source_verified_file_counts": direct_source_inventories,
    }


def train_learning_curve(
    inputs: Mapping[str, Any],
    *,
    solver: Callable[..., Any] = solve_v24_cutting_plane,
    progress_callback: Optional[Callable[[Mapping[str, Any]], None]] = None,
) -> dict[str, Any]:
    models: dict[str, dict[str, Any]] = {}
    for sequence, level in enumerate(inputs["levels"], start=1):
        percent = int(level["percent"])
        indices = np.asarray(inputs["level_indices"][percent], dtype=np.int64)
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "level_started",
                    "level_percent": percent,
                    "level_sequence": sequence,
                    "level_count": len(EXPECTED_LEVELS),
                    "completed_levels": list(models),
                }
            )
        models[str(percent)] = train_level(
            level_percent=percent,
            atoms=np.asarray(inputs["atoms"])[indices],
            candidate_cost=np.asarray(inputs["candidate_cost"])[indices],
            source_valid=np.asarray(inputs["source_valid_mask"])[indices],
            oracle_index=np.asarray(inputs["oracle_index"])[indices],
            frozen_scales=np.asarray(inputs["atom_scales"]),
            snapshot_sha256=[inputs["snapshot_sha256"][int(i)] for i in indices],
            route_membership_sha256=level["route_membership_sha256"],
            route_count=level["route_count"],
            retained_route_seed_count=level["retained_route_seed_count"],
            complete_route_seed_count=level["complete_route_seed_count"],
            failed_route_seed_count=level["failed_route_seed_count"],
            solver=solver,
        )
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "level_completed",
                    "level_percent": percent,
                    "level_sequence": sequence,
                    "level_count": len(EXPECTED_LEVELS),
                    "completed_levels": list(models),
                    "solver_iterations": models[str(percent)]["solver"]["iterations"],
                    "offline_wall_clock_s": models[str(percent)]["solver"][
                        "offline_wall_clock_s"
                    ],
                }
            )
    if list(models) != ["25", "50", "75", "100"]:
        raise RuntimeError("all four preregistered learning-curve levels must solve")
    return {
        "schema": "camp_dp_v24_convex_selector_training_execution_v1",
        "status": "passed",
        "models": models,
        "primary_model_level_percent": 100,
        "curve_models_used_for_model_selection": False,
        "full_train_model_frozen_for_later_calibration": True,
        "route_count": EXPECTED_ROUTES,
        "retained_route_seed_count": EXPECTED_ROUTE_SEEDS,
        "complete_route_seed_count": 1054,
        "failed_route_seed_count": 821,
        "failure_reason_counts": dict(inputs["failure_reason_counts"]),
        "source_verified_file_counts": dict(inputs["source_verified_file_counts"]),
        "direct_source_verified_file_counts": dict(
            inputs["direct_source_verified_file_counts"]
        ),
        "snapshot_count": EXPECTED_SNAPSHOTS,
        "candidate_count": EXPECTED_CANDIDATES,
        "source_valid_candidate_count": int(
            np.asarray(inputs["source_valid_mask"], dtype=bool).sum()
        ),
        "physical_feasible_candidate_count": int(
            np.asarray(inputs["physical_feasible_mask"], dtype=bool).sum()
        ),
        "all_k_high_risk_snapshot_count": int(
            np.asarray(inputs["all_k_high_risk"], dtype=bool).sum()
        ),
        "epoch_semantics": False,
        "v18_v22_weights_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "actual_closed_loop_outcomes_read": False,
        "identity_fields_used_as_feature": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "next_work_target": "v24_convex_selector_training_execution_independent_review_only",
    }


def _authorization_from_eof(
    *, repo: Path, artifact: Path, expected_root: str, expected_camp_head: str
) -> dict[str, Any]:
    text = (Path(repo) / AUDIT_RELATIVE).read_text(encoding="utf-8")
    lines = text.rstrip().splitlines()[-15:]
    expected = {
        "current_v24_status": (
            "v24_convex_training_cut_relative_gap_authorization_contract_"
            "repair_static_preflight_"
            "independent_review_passed"
        ),
        "current_v24_artifact_source_head": expected_camp_head,
        "current_v24_artifact": str(artifact),
        "current_v24_artifact_root_sha256": expected_root,
        "next_work_target": (
            "v24_convex_selector_training_cut_relative_gap_retry_execution_only"
        ),
    }
    parsed = dict(line.split("=", 1) for line in lines if "=" in line)
    if any(parsed.get(key) != value for key, value in expected.items()):
        raise ValueError("live v24 EOF does not authorize training execution")
    verify_complete_seal(artifact, expected_root)
    review = _read_json(Path(artifact) / "review.json")
    if (
        review.get("schema")
        != "camp_dp_v24_training_cut_relative_gap_authorization_contract_"
        "repair_static_preflight_"
        "independent_review_v1"
        or review.get("status") != "passed"
        or review.get("camp_head") != expected_camp_head
        or review.get("executor_source_sha256")
        != hashlib.sha256(
            (Path(repo) / EXECUTOR_PROVENANCE_FILES[0]).read_bytes()
        ).hexdigest()
        or review.get("decision", {}).get("training_execution_authorized") is not True
        or review.get("decision", {}).get("training_retry_authorized") is not True
        or review.get("outcome_accessed") is not False
        or review.get("calibration_accessed") is not False
        or review.get("holdout_opened") is not False
        or review.get("claim_authorized") is not False
    ):
        raise ValueError("v24 static preflight review does not authorize execution")
    return review


def write_training_outputs(
    result: Mapping[str, Any], output_dir: Path, *, precreated: bool = False
) -> None:
    output = Path(output_dir)
    if precreated:
        if not output.is_dir() or (output / "models").exists():
            raise ValueError("precreated v24 training artifact staging drift")
    else:
        output.mkdir(parents=True, exist_ok=False)
    models_dir = output / "models"
    models_dir.mkdir()
    model_receipts = {}
    for name, model in result["models"].items():
        payload = dict(model)
        cut_mask = np.asarray(payload.pop("_final_cut_mask"))
        if cut_mask.dtype != np.bool_ or cut_mask.shape[1:] != (8,):
            raise ValueError("final cut mask output is invalid")
        cut_relative = f"models/level_{name}_final_cut_mask.u8"
        (output / cut_relative).write_bytes(
            cut_mask.astype(np.uint8).tobytes(order="C")
        )
        payload["final_cut_mask"] = {
            "path": cut_relative,
            "dtype": "u1_bool",
            "shape": list(cut_mask.shape),
            "sha256": _file_sha256(output / cut_relative),
        }
        content = _canonical_json_bytes(payload)
        relative = f"models/level_{name}.json"
        (output / relative).write_bytes(content)
        weights = np.asarray(model["weights"], dtype="<f8")
        weights_relative = f"models/level_{name}_weights.f64le"
        (output / weights_relative).write_bytes(weights.tobytes(order="C"))
        model_receipts[name] = {
            "model": {"path": relative, "sha256": hashlib.sha256(content).hexdigest()},
            "weights": {
                "path": weights_relative,
                "sha256": _file_sha256(output / weights_relative),
            },
            "final_cut_mask": payload["final_cut_mask"],
        }
    manifest = {key: value for key, value in result.items() if key != "models"}
    manifest["model_receipts"] = model_receipts
    manifest["primary_model_receipt"] = model_receipts["100"]
    (output / "training_manifest.json").write_bytes(_canonical_json_bytes(manifest))


def _write_progress(output_dir: Path, payload: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    content = _canonical_json_bytes(
        {
            "schema": "camp_dp_v24_convex_training_progress_v1",
            "training_execution_active": payload.get("phase")
            not in {"training_completed", "training_failed"},
            **dict(payload),
        }
    )
    temporary = output / "progress.json.tmp"
    temporary.write_bytes(content)
    os.replace(temporary, output / "progress.json")


def seal_artifact(root: Path) -> str:
    source = Path(root)
    sums = source / "SHA256SUMS"
    receipt = source / "ROOT_SHA256SUMS"
    files: list[Path] = []
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("training artifact symlink is forbidden")
        if not path.is_file() or path in {sums, receipt}:
            continue
        if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            raise ValueError("nested training manifest name is forbidden")
        files.append(path)
    files.sort()
    sums.write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(source).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(sums)
    receipt.write_text(f"{digest}  SHA256SUMS\n", encoding="ascii")
    return digest


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--authorization-root", type=Path, required=True)
    parser.add_argument("--authorization-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--enable-training-execution", action="store_true")
    args = parser.parse_args(argv)
    if os.name != "posix":
        raise RuntimeError("v24 training execution requires the isolated AutoDL host")
    if not args.enable_training_execution:
        raise RuntimeError("v24 training execution enable flag is required")
    if args.output_dir.exists():
        raise FileExistsError("v24 training artifact target already exists")
    if shutil.disk_usage(args.output_dir.parent).free <= MINIMUM_FREE_BYTES:
        raise RuntimeError("10 GiB disk floor is not available")
    _require_clean_repo(args.repo, args.camp_head)
    _require_clean_repo(args.dp_repo, FIXED_DP_HEAD)
    source_provenance = tracked_source_provenance(
        repo=args.repo, current_head=args.camp_head
    )
    authorization = _authorization_from_eof(
        repo=args.repo,
        artifact=args.authorization_root,
        expected_root=args.authorization_root_sha256,
        expected_camp_head=args.camp_head,
    )
    import fcntl

    TRAINING_LOCK.parent.mkdir(parents=True, exist_ok=True)
    command = " ".join(sys.argv)
    with TRAINING_LOCK.open("a+") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("v24 convex training lock is held") from exc
        if not _lock_is_free(CORPUS_LOCK) or not _lock_is_free(LABEL_LOCK):
            raise RuntimeError("v24 upstream corpus or label lock is held")
        started = time.perf_counter()
        inputs = load_training_inputs()
        args.output_dir.mkdir(parents=True)
        _write_progress(
            args.output_dir,
            {
                "phase": "inputs_loaded",
                "level_count": len(EXPECTED_LEVELS),
                "completed_levels": [],
                "snapshot_count": EXPECTED_SNAPSHOTS,
                "candidate_count": EXPECTED_CANDIDATES,
            },
        )
        try:
            result = train_learning_curve(
                inputs,
                progress_callback=lambda payload: _write_progress(
                    args.output_dir, payload
                ),
            )
        except Exception as exc:
            failure = {
                "schema": "camp_dp_v24_convex_training_execution_failure_v1",
                "status": "failed",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "camp_head": args.camp_head,
                "fixed_dp_head": FIXED_DP_HEAD,
                "training_execution_attempted": True,
                "calibration_accessed": False,
                "holdout_opened": False,
                "actual_closed_loop_outcomes_read": False,
                "claim_authorized": False,
                "next_work_target": (
                    "v24_convex_selector_training_execution_failure_independent_review"
                ),
            }
            _write_progress(
                args.output_dir,
                {
                    "phase": "training_failed",
                    "failure_type": type(exc).__name__,
                    "completed_levels": _read_json(
                        args.output_dir / "progress.json"
                    ).get("completed_levels", []),
                },
            )
            (args.output_dir / "failure.json").write_bytes(
                _canonical_json_bytes(failure)
            )
            (args.output_dir / "failure.md").write_text(
                "# V24 Convex Selector Training Failure\n\n"
                f"- type: `{type(exc).__name__}`\n"
                "- calibration / holdout / outcomes: `not accessed`\n",
                encoding="utf-8",
            )
            (args.output_dir / "HEADS").write_text(
                f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n",
                encoding="ascii",
            )
            (args.output_dir / "COMMAND").write_text(
                command + "\n", encoding="utf-8"
            )
            (args.output_dir / "stdout.txt").write_text("", encoding="utf-8")
            (args.output_dir / "stderr.txt").write_text(
                f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
            )
            (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
            failure_root = seal_artifact(args.output_dir)
            print(
                json.dumps(
                    {"artifact_root_sha256": failure_root, "status": "failed"},
                    sort_keys=True,
                )
            )
            return 1
        result["total_offline_training_wall_clock_s"] = time.perf_counter() - started
        result["camp_head"] = args.camp_head
        result["fixed_dp_head"] = FIXED_DP_HEAD
        result["source_provenance"] = source_provenance
        result["source_authorization_artifact"] = str(args.authorization_root)
        result["source_authorization_root_sha256"] = args.authorization_root_sha256
        result["source_authorization_review_source_sha256"] = authorization.get(
            "executor_source_sha256"
        )
        result["source_label_artifact"] = str(LABEL_ARTIFACT)
        result["source_label_root_sha256"] = LABEL_ROOT_SHA256
        result["source_label_review_artifact"] = str(LABEL_REVIEW_ARTIFACT)
        result["source_label_review_root_sha256"] = LABEL_REVIEW_ROOT_SHA256
        result["source_training_plan_artifact"] = str(PLAN_ARTIFACT)
        result["source_training_plan_root_sha256"] = PLAN_ROOT_SHA256
        result["source_merged_artifact"] = str(MERGED_ARTIFACT)
        result["source_merged_root_sha256"] = MERGED_ROOT_SHA256
        _write_progress(
            args.output_dir,
            {
                "phase": "training_completed",
                "level_count": len(EXPECTED_LEVELS),
                "completed_levels": [str(level) for level in EXPECTED_LEVELS],
                "total_offline_training_wall_clock_s": result[
                    "total_offline_training_wall_clock_s"
                ],
            },
        )
        write_training_outputs(result, args.output_dir, precreated=True)
        (args.output_dir / "HEADS").write_text(
            f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(command + "\n", encoding="utf-8")
        (args.output_dir / "stdout.txt").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "levels": [25, 50, 75, 100],
                    "training_executed": True,
                    "next_work_target": result["next_work_target"],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        (args.output_dir / "training.md").write_text(
            "# V24 Convex Selector Training\n\n"
            "- status: `passed`\n"
            "- learning curve: `25 / 50 / 75 / 100%`\n"
            "- primary model: `100% full train`\n"
            "- calibration / holdout / outcomes: `not accessed`\n",
            encoding="utf-8",
        )
        root_sha256 = seal_artifact(args.output_dir)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    print(json.dumps({"artifact_root_sha256": root_sha256}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
