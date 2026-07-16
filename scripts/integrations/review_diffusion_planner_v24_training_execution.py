#!/usr/bin/env python3
"""Independently review the sealed v24 train-only convex selector result."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
from typing import Any, Mapping, Optional, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_CAMP_ATOM_NAMES_V10,
)
from scripts.integrations.preflight_diffusion_planner_v24_convex_training import (  # noqa: E402
    _canonical_json_bytes,
    _file_sha256,
    _require_clean_repo,
    verify_complete_seal,
)
from scripts.integrations import train_diffusion_planner_v24_selector as training_source  # noqa: E402


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
TRAINING_EXECUTION_HEAD = "9e9457d540a0af3398c8b17b37ab9032049c5b5b"
AUTHORIZATION_SOURCE_HEAD = "b6f9870f7b695cb7472b9a773f2e5aa25780c061"
TRAINING_EXECUTOR_RELATIVE = (
    "scripts/integrations/train_diffusion_planner_v24_selector.py"
)
REVIEWER_RELATIVE = (
    "scripts/integrations/review_diffusion_planner_v24_training_execution.py"
)
AUDIT_RELATIVE = Path("docs/diffusion_planner_v24_iteration_audit.md")
CURRENT_STATUS_RELATIVE = Path("docs/diffusion_planner_current_status.md")
EXPECTED_LEVELS = (25, 50, 75, 100)
EXPECTED_LEVEL_ROUTES = (94, 188, 281, 375)
EXPECTED_LEVEL_SNAPSHOTS = (16979, 35022, 50752, 67796)
EXPECTED_LEVEL_ROUTE_SEEDS = (470, 940, 1405, 1875)
EXPECTED_LEVEL_COMPLETE = (262, 550, 789, 1054)
EXPECTED_LEVEL_FAILED = (208, 390, 616, 821)
EXPECTED_PROVENANCE = {
    "scripts/integrations/train_diffusion_planner_v24_selector.py",
    "scripts/integrations/preflight_diffusion_planner_v24_training_executor.py",
    "scripts/integrations/review_diffusion_planner_v24_training_executor_preflight.py",
    "scripts/integrations/review_diffusion_planner_v24_training_execution_failure.py",
    "scripts/integrations/review_diffusion_planner_v24_training_retry_failure.py",
    "configs/integrations/diffusion_planner_v24_convex_training_plan.json",
    "camp_core/camp_core/outer_master/robust_margin_master.py",
    "scripts/integrations/preflight_diffusion_planner_v24_convex_training.py",
    "scripts/integrations/review_diffusion_planner_v24_atom_availability.py",
}
LOCKS = (
    Path("/root/autodl-tmp/.camp_dp_v24_convex_training.lock"),
    Path("/root/autodl-tmp/.camp_dp_v24_native_corpus_remaining.lock"),
    Path("/root/autodl-tmp/.camp_dp_v24_training_label_materialization.lock"),
)
MINIMUM_FREE_BYTES = 10 * 1024**3
ACCEPTANCE_GAP = 1e-6
NUMERIC_ATOL = 1e-12
REVIEW_SCHEMA = "camp_dp_v24_convex_selector_training_execution_independent_review_v1"


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _safe_autodl_path(path: Path) -> bool:
    pure = PurePosixPath(str(path))
    return bool(
        pure.is_absolute()
        and pure.parts[:3] == ("/", "root", "autodl-tmp")
        and ".." not in pure.parts
    )


def _verify_clean_seal(path: Path, root_sha256: str) -> int:
    if not _safe_autodl_path(path):
        raise ValueError("v24 training review artifact path is unsafe")
    files = verify_complete_seal(path, root_sha256)
    if (
        (path / "run.exit").read_text(encoding="ascii") != "0\n"
        or (path / "stderr.txt").read_text(encoding="utf-8") != ""
    ):
        raise ValueError("v24 training review source execution is not clean")
    return len(files)


def _git_blob(repo: Path, head: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _git_blob_id(repo: Path, head: str, relative: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _is_sha256(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and not set(value) - set("0123456789abcdef")
    )


def _close(actual: Any, expected: Any, name: str, *, atol: float = NUMERIC_ATOL) -> None:
    left = float(actual)
    right = float(expected)
    if not np.isfinite(left) or not np.isfinite(right) or not np.isclose(
        left, right, rtol=0.0, atol=atol
    ):
        raise ValueError(f"v24 training numeric receipt drift: {name}")


def _project_simplex_independent(values: np.ndarray) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (14,) or not np.isfinite(vector).all():
        raise ValueError("v24 raw weights are not finite 14D")
    ordered = np.sort(vector)[::-1]
    cumulative = np.cumsum(ordered, dtype=np.float64)
    support = np.flatnonzero(
        ordered - (cumulative - 1.0) / np.arange(1, vector.size + 1) > 0.0
    )
    if support.size == 0:
        raise ValueError("v24 simplex projection has empty support")
    rho = int(support[-1])
    theta = (cumulative[rho] - 1.0) / float(rho + 1)
    projected = np.maximum(vector - theta, 0.0)
    projected /= projected.sum()
    return projected


def _problem_independent(
    atoms: np.ndarray,
    candidate_cost: np.ndarray,
    source_valid: np.ndarray,
    stored_oracle: np.ndarray,
    scales: np.ndarray,
) -> dict[str, np.ndarray]:
    matrix = np.asarray(atoms, dtype=np.float64)
    costs = np.asarray(candidate_cost, dtype=np.float64)
    valid = np.asarray(source_valid)
    oracle = np.asarray(stored_oracle)
    frozen = np.asarray(scales, dtype=np.float64)
    if (
        matrix.ndim != 3
        or matrix.shape[1:] != (8, 14)
        or costs.shape != matrix.shape[:2]
        or valid.dtype != np.bool_
        or valid.shape != matrix.shape[:2]
        or oracle.shape != (matrix.shape[0],)
        or oracle.dtype.kind not in {"i", "u"}
        or frozen.shape != (14,)
        or not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not np.isfinite(costs).all()
        or np.any(costs < 0.0)
        or not np.isfinite(frozen).all()
        or np.any(frozen <= 0.0)
        or not valid.any(axis=1).all()
    ):
        raise ValueError("v24 independent training arrays are invalid")
    independent_oracle = np.argmin(np.where(valid, costs, np.inf), axis=1)
    if not np.array_equal(oracle.astype(np.int64), independent_oracle):
        raise ValueError("v24 independent oracle recomputation drift")
    normalized = np.clip(matrix / frozen.reshape(1, 1, 14), 0.0, 10.0)
    oracle_cost = costs[np.arange(costs.shape[0]), independent_oracle]
    margins = np.clip(
        0.1 * (costs - oracle_cost[:, None]), 0.0, 2.0
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


def _losses_independent(
    atoms: np.ndarray,
    weights: np.ndarray,
    oracle: np.ndarray,
    margins: np.ndarray,
    valid: np.ndarray,
    cut_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows = np.arange(atoms.shape[0])
    oracle_atoms = atoms[rows, oracle]
    values = margins + np.einsum(
        "nkr,r->nk", oracle_atoms[:, None, :] - atoms, weights
    )
    values[~valid] = -np.inf
    full = np.maximum(np.max(values, axis=1), 0.0)
    cut_values = np.where(cut_mask & valid, values, -np.inf)
    if not np.isfinite(np.max(cut_values, axis=1)).all():
        raise ValueError("v24 cut mask omits every valid candidate in a row")
    cut = np.maximum(np.max(cut_values, axis=1), 0.0)
    return full, cut, np.maximum(full - cut, 0.0)


def _empirical_cvar_independent(losses: np.ndarray, alpha: float = 0.9) -> float:
    values = np.sort(np.asarray(losses, dtype=np.float64).reshape(-1))
    candidates = np.unique(values)
    right = np.searchsorted(values, candidates, side="right")
    suffix = np.concatenate(
        [np.cumsum(values[::-1], dtype=np.float64)[::-1], np.asarray([0.0])]
    )
    counts = values.size - right
    objectives = candidates + (
        suffix[right] - candidates * counts
    ) / ((1.0 - alpha) * values.size)
    return float(np.min(objectives))


def _receipt_file(
    *, artifact: Path, receipt: Mapping[str, Any], expected_path: str
) -> Path:
    if receipt.get("path") != expected_path or not _is_sha256(receipt.get("sha256")):
        raise ValueError("v24 model receipt path or SHA drift")
    path = artifact / expected_path
    if _file_sha256(path) != receipt["sha256"]:
        raise ValueError("v24 model receipt file SHA drift")
    return path


def _verify_history(
    *, model: Mapping[str, Any], raw_full: np.ndarray, projected_full: np.ndarray,
    raw_cut_gap: float, projected_cut_gap: float, total_cuts: int,
) -> dict[str, Any]:
    solver = model.get("solver")
    if not isinstance(solver, Mapping):
        raise ValueError("v24 solver receipt is missing")
    history = solver.get("history")
    if (
        solver.get("name") != "CLARABEL"
        or solver.get("status") != "optimal"
        or solver.get("converged") is not True
        or solver.get("fallback_allowed") is not False
        or solver.get("epoch_semantics") is not False
        or solver.get("v18_v22_weights_loaded") is not False
        or solver.get("solver_default_initialization") is not True
        or solver.get("final_new_cuts") != 0
        or solver.get("iterations") != len(history or [])
        or not isinstance(history, list)
        or not 1 <= len(history) <= 20
        or solver.get("registry_receipt", {}).get("solvers_exposed_to_master")
        != ["CLARABEL"]
        or solver.get("registry_receipt", {}).get("fallback_solvers_exposed") != []
    ):
        raise ValueError("v24 exact CLARABEL convergence receipt drift")
    prior_cuts = int(model["snapshot_count"])
    for iteration, row in enumerate(history, start=1):
        if (
            row.get("iteration") != iteration
            or row.get("final_resolve") is not False
            or type(row.get("new_cuts")) is not int
            or row["new_cuts"] < 0
            or row.get("total_cuts") != prior_cuts + row["new_cuts"]
        ):
            raise ValueError("v24 cutting-plane iteration receipt drift")
        prior_cuts = row["total_cuts"]
    final = history[-1]
    if final.get("new_cuts") != 0 or prior_cuts != total_cuts:
        raise ValueError("v24 final cut count or zero-cut convergence drift")
    four_reported = {
        "raw_master_gap": solver.get("raw_master_gap"),
        "projected_master_gap": solver.get("projected_master_gap"),
        "raw_cut_relative_gap": solver.get("raw_cut_relative_gap"),
        "projected_cut_relative_gap": solver.get("projected_cut_relative_gap"),
    }
    if any(
        not np.isfinite(float(value)) or float(value) < 0.0 or float(value) > ACCEPTANCE_GAP
        for value in four_reported.values()
    ):
        raise ValueError("v24 reported four-gap acceptance drift")
    _close(final["raw_max_master_gap"], four_reported["raw_master_gap"], "raw master")
    _close(
        final["projected_max_master_gap"],
        four_reported["projected_master_gap"],
        "projected master",
    )
    _close(final["raw_max_cut_gap"], raw_cut_gap, "raw cut gap")
    _close(final["projected_max_cut_gap"], projected_cut_gap, "projected cut gap")
    _close(four_reported["raw_cut_relative_gap"], raw_cut_gap, "raw saved cut gap")
    _close(
        four_reported["projected_cut_relative_gap"],
        projected_cut_gap,
        "projected saved cut gap",
    )
    _close(final["raw_mean_violation"], np.mean(raw_full), "raw mean violation")
    _close(final["raw_max_violation"], np.max(raw_full), "raw max violation")
    _close(
        final["projected_mean_violation"],
        np.mean(projected_full),
        "projected mean violation",
    )
    _close(
        final["projected_max_violation"],
        np.max(projected_full),
        "projected max violation",
    )
    _close(
        final["exact_cvar"],
        _empirical_cvar_independent(projected_full),
        "final exact CVaR",
    )
    _close(
        final["max_separation_gap"],
        max(float(value) for value in four_reported.values()),
        "final maximum separation gap",
    )
    return {
        "iterations": len(history),
        "total_cuts": total_cuts,
        "reported_four_gaps": {key: float(value) for key, value in four_reported.items()},
        "offline_wall_clock_s": float(solver["offline_wall_clock_s"]),
        "exact_cvar": float(final["exact_cvar"]),
    }


def _review_level(
    *, artifact: Path, manifest_receipt: Mapping[str, Any], model: Mapping[str, Any],
    inputs: Mapping[str, Any], level: Mapping[str, Any],
) -> dict[str, Any]:
    percent = int(level["percent"])
    expected_index = EXPECTED_LEVELS.index(percent)
    indices = np.asarray(inputs["level_indices"][percent], dtype=np.int64)
    expected_snapshot_count = EXPECTED_LEVEL_SNAPSHOTS[expected_index]
    if indices.size != expected_snapshot_count:
        raise ValueError("v24 learning-curve level index count drift")
    expected_model_path = f"models/level_{percent}.json"
    expected_weights_path = f"models/level_{percent}_weights.f64le"
    expected_cut_path = f"models/level_{percent}_final_cut_mask.u8"
    if not isinstance(manifest_receipt, Mapping) or set(manifest_receipt) != {
        "model", "weights", "final_cut_mask"
    }:
        raise ValueError("v24 learning-curve model receipt inventory drift")
    model_path = _receipt_file(
        artifact=artifact,
        receipt=manifest_receipt["model"],
        expected_path=expected_model_path,
    )
    if _read_json(model_path) != model:
        raise ValueError("v24 model JSON reread drift")
    weights_path = _receipt_file(
        artifact=artifact,
        receipt=manifest_receipt["weights"],
        expected_path=expected_weights_path,
    )
    cut_path = _receipt_file(
        artifact=artifact,
        receipt=manifest_receipt["final_cut_mask"],
        expected_path=expected_cut_path,
    )
    weights_blob = np.fromfile(weights_path, dtype="<f8")
    stored_weights = np.asarray(model.get("weights"), dtype=np.float64)
    raw_weights = np.asarray(model.get("raw_weights"), dtype=np.float64)
    independently_projected = _project_simplex_independent(raw_weights)
    if (
        weights_blob.shape != (14,)
        or stored_weights.shape != (14,)
        or raw_weights.shape != (14,)
        or not np.array_equal(weights_blob, stored_weights)
        or np.max(np.abs(independently_projected - stored_weights)) > 1e-14
        or np.any(raw_weights < -1e-8)
        or not np.isclose(raw_weights.sum(), 1.0, rtol=0.0, atol=1e-8)
        or np.any(stored_weights < 0.0)
        or not np.isclose(stored_weights.sum(), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("v24 independent simplex or weight-file review failed")
    cut_bytes = np.fromfile(cut_path, dtype=np.uint8)
    if cut_bytes.size != expected_snapshot_count * 8 or not np.isin(
        cut_bytes, [0, 1]
    ).all():
        raise ValueError("v24 final cut mask byte contract drift")
    cut_mask = cut_bytes.reshape(expected_snapshot_count, 8).astype(bool)
    cut_receipt = model.get("final_cut_mask")
    if (
        not isinstance(cut_receipt, Mapping)
        or cut_receipt != manifest_receipt["final_cut_mask"]
        or cut_receipt.get("shape") != [expected_snapshot_count, 8]
        or cut_receipt.get("dtype") != "u1_bool"
    ):
        raise ValueError("v24 final cut mask metadata drift")
    problem = _problem_independent(
        np.asarray(inputs["atoms"])[indices],
        np.asarray(inputs["candidate_cost"])[indices],
        np.asarray(inputs["source_valid_mask"])[indices],
        np.asarray(inputs["oracle_index"])[indices],
        np.asarray(inputs["atom_scales"]),
    )
    raw_full, raw_cut, raw_gap_rows = _losses_independent(
        problem["normalized_atoms"],
        raw_weights,
        problem["oracle_indices"],
        problem["margins"],
        problem["source_valid_mask"],
        cut_mask,
    )
    projected_full, projected_cut, projected_gap_rows = _losses_independent(
        problem["normalized_atoms"],
        stored_weights,
        problem["oracle_indices"],
        problem["margins"],
        problem["source_valid_mask"],
        cut_mask,
    )
    raw_cut_gap = float(np.max(raw_gap_rows))
    projected_cut_gap = float(np.max(projected_gap_rows))
    # The final per-snapshot master variables are not serialized. The raw final-cut
    # envelope is an independently reconstructable conservative substitute for
    # those master losses and must still close both master-envelope gaps.
    raw_master_envelope_gap = float(np.max(np.maximum(raw_full - raw_cut, 0.0)))
    projected_master_envelope_gap = float(
        np.max(np.maximum(projected_full - raw_cut, 0.0))
    )
    independent_four_gaps = {
        "raw_master_envelope_gap": raw_master_envelope_gap,
        "projected_master_envelope_gap": projected_master_envelope_gap,
        "raw_cut_relative_gap": raw_cut_gap,
        "projected_cut_relative_gap": projected_cut_gap,
    }
    if any(value > ACCEPTANCE_GAP for value in independent_four_gaps.values()):
        raise ValueError("v24 independent four-gap recomputation failed")
    cut_counts = cut_mask.sum(axis=1, dtype=np.int64)
    if np.any(cut_counts < 1) or np.any(cut_counts > 8):
        raise ValueError("v24 per-snapshot final cut count drift")
    histogram = np.bincount(cut_counts, minlength=9).astype(int).tolist()
    total_cuts = int(cut_counts.sum())
    solver_review = _verify_history(
        model=model,
        raw_full=raw_full,
        projected_full=projected_full,
        raw_cut_gap=raw_cut_gap,
        projected_cut_gap=projected_cut_gap,
        total_cuts=total_cuts,
    )
    final_receipt = model.get("final_cut_receipt")
    if not isinstance(final_receipt, Mapping):
        raise ValueError("v24 final cut receipt is missing")
    for name, actual in (
        ("full_k_loss_mean", np.mean(projected_full)),
        ("full_k_loss_maximum", np.max(projected_full)),
        ("final_cut_loss_mean", np.mean(projected_cut)),
        ("projected_saved_weight_full_k_gap", projected_cut_gap),
        ("raw_saved_weight_full_k_gap", raw_cut_gap),
        ("simplex_projection_linf", np.max(np.abs(stored_weights - raw_weights))),
    ):
        _close(final_receipt[name], actual, name)
    if (
        final_receipt.get("omitted_violating_snapshot_count") != 0
        or final_receipt.get("cut_count_histogram") != histogram
        or final_receipt.get("total_cuts") != total_cuts
        or final_receipt.get("projected_weights") != model.get("weights")
        or final_receipt.get("raw_weights") != model.get("raw_weights")
    ):
        raise ValueError("v24 final cut receipt recomputation drift")
    scores = np.einsum("nkr,r->nk", problem["normalized_atoms"], stored_weights)
    selected = np.argmin(
        np.where(problem["source_valid_mask"], scores, np.inf), axis=1
    )
    rows = np.arange(selected.size)
    selected_cost = problem["candidate_cost"][rows, selected]
    selection_histogram = np.bincount(selected, minlength=8).astype(int).tolist()
    independent_metrics = {
        "oracle_agreement_count": int(np.sum(selected == problem["oracle_indices"])),
        "oracle_agreement_rate": float(np.mean(selected == problem["oracle_indices"])),
        "selection_histogram": selection_histogram,
        "candidate0_selection_count": selection_histogram[0],
        "non_candidate0_selection_count": int(selected.size - selection_histogram[0]),
        "selected_surrogate_cost_mean": float(np.mean(selected_cost)),
        "candidate0_surrogate_cost_mean": float(np.mean(problem["candidate_cost"][:, 0])),
        "selected_minus_candidate0_surrogate_cost_mean": float(
            np.mean(selected_cost - problem["candidate_cost"][:, 0])
        ),
        "mean_ranking_violation": float(np.mean(projected_full)),
        "maximum_ranking_violation": float(np.max(projected_full)),
    }
    reported_metrics = model.get("train_metrics")
    if not isinstance(reported_metrics, Mapping) or set(reported_metrics) != set(
        independent_metrics
    ):
        raise ValueError("v24 train metric inventory drift")
    for name, actual in independent_metrics.items():
        if isinstance(actual, list):
            if reported_metrics.get(name) != actual:
                raise ValueError(f"v24 train metric recomputation drift: {name}")
        elif isinstance(actual, int):
            if reported_metrics.get(name) != actual:
                raise ValueError(f"v24 train metric recomputation drift: {name}")
        else:
            _close(reported_metrics[name], actual, name)
    digests = [inputs["snapshot_sha256"][index] for index in indices]
    snapshot_sequence_sha256 = hashlib.sha256(
        ("\n".join(digests) + "\n").encode("ascii")
    ).hexdigest()
    expected_common = {
        "schema": "camp_dp_v24_static_affine_selector_model_v1",
        "level_percent": percent,
        "diagnostic_only": percent != 100,
        "primary_model": percent == 100,
        "snapshot_count": expected_snapshot_count,
        "snapshot_sequence_sha256": snapshot_sequence_sha256,
        "route_membership_sha256": level["route_membership_sha256"],
        "route_count": EXPECTED_LEVEL_ROUTES[expected_index],
        "retained_route_seed_count": EXPECTED_LEVEL_ROUTE_SEEDS[expected_index],
        "complete_route_seed_count": EXPECTED_LEVEL_COMPLETE[expected_index],
        "failed_route_seed_count": EXPECTED_LEVEL_FAILED[expected_index],
        "atom_schema_version": "dp_camp_v10_14d",
        "atom_names": list(DP_CAMP_ATOM_NAMES_V10),
        "active_atom_mask": [True] * 14,
        "score_contract": "score_k(w)=a_k^T w",
        "atom_transform": "clip(raw_atom/frozen_v24_scale,0,10)",
        "oracle_eligibility": "source_valid_mask_only",
        "actual_closed_loop_outcomes_read": False,
        "identity_fields_used_as_feature": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    if any(model.get(key) != value for key, value in expected_common.items()):
        raise ValueError("v24 model identity or closed-boundary receipt drift")
    if model.get("atom_scales") != np.asarray(inputs["atom_scales"]).tolist():
        raise ValueError("v24 frozen atom scale receipt drift")
    _close(model.get("simplex_sum"), stored_weights.sum(), "simplex sum")
    _close(model.get("minimum_weight"), stored_weights.min(), "minimum weight")
    return {
        "level_percent": percent,
        "primary_model": percent == 100,
        "diagnostic_only": percent != 100,
        "route_count": int(model["route_count"]),
        "retained_route_seed_count": int(model["retained_route_seed_count"]),
        "complete_route_seed_count": int(model["complete_route_seed_count"]),
        "failed_route_seed_count": int(model["failed_route_seed_count"]),
        "snapshot_count": expected_snapshot_count,
        "weights": stored_weights.tolist(),
        "raw_weights": raw_weights.tolist(),
        "weights_sha256": _file_sha256(weights_path),
        "cut_mask_sha256": _file_sha256(cut_path),
        "model_sha256": _file_sha256(model_path),
        "independent_four_gaps": independent_four_gaps,
        "solver": solver_review,
        "train_metrics": independent_metrics,
    }


def _verify_source_provenance(
    *, repo: Path, current_head: str, manifest: Mapping[str, Any]
) -> dict[str, str]:
    reported = manifest.get("source_provenance")
    if not isinstance(reported, Mapping) or set(reported) != EXPECTED_PROVENANCE:
        raise ValueError("v24 training source provenance inventory drift")
    digests: dict[str, str] = {}
    for relative in sorted(EXPECTED_PROVENANCE):
        live = (repo / relative).read_bytes()
        current = _git_blob(repo, current_head, relative)
        executed = _git_blob(repo, TRAINING_EXECUTION_HEAD, relative)
        receipt = reported[relative]
        digest = hashlib.sha256(executed).hexdigest()
        if (
            live != current
            or current != executed
            or not isinstance(receipt, Mapping)
            or receipt.get("sha256") != digest
            or receipt.get("git_blob")
            != _git_blob_id(repo, TRAINING_EXECUTION_HEAD, relative)
            or receipt.get("matches_current_head") is not True
        ):
            raise ValueError(f"v24 training execution source drift: {relative}")
        digests[relative] = digest
    reviewer_live = (repo / REVIEWER_RELATIVE).read_bytes()
    if reviewer_live != _git_blob(repo, current_head, REVIEWER_RELATIVE):
        raise ValueError("v24 result reviewer is not tracked at current HEAD")
    digests[REVIEWER_RELATIVE] = hashlib.sha256(reviewer_live).hexdigest()
    return digests


def _verify_upstream_closure(manifest: Mapping[str, Any]) -> dict[str, int]:
    top = {
        "source_authorization": (
            Path(str(manifest.get("source_authorization_artifact"))),
            str(manifest.get("source_authorization_root_sha256")),
        ),
        "training_plan": (
            Path(str(manifest.get("source_training_plan_artifact"))),
            str(manifest.get("source_training_plan_root_sha256")),
        ),
        "causal_labels": (
            Path(str(manifest.get("source_label_artifact"))),
            str(manifest.get("source_label_root_sha256")),
        ),
        "causal_label_review": (
            Path(str(manifest.get("source_label_review_artifact"))),
            str(manifest.get("source_label_review_root_sha256")),
        ),
        "merged_train_corpus": (
            Path(str(manifest.get("source_merged_artifact"))),
            str(manifest.get("source_merged_root_sha256")),
        ),
    }
    counts = {
        f"top_{name}": _verify_clean_seal(path, digest)
        for name, (path, digest) in top.items()
    }
    authorization = _read_json(top["source_authorization"][0] / "review.json")
    if (
        authorization.get("status") != "passed"
        or authorization.get("camp_head") != AUTHORIZATION_SOURCE_HEAD
        or authorization.get("executor_source_sha256")
        != manifest.get("source_authorization_review_source_sha256")
        or authorization.get("decision", {}).get("training_execution_authorized")
        is not True
        or authorization.get("outcome_accessed") is not False
        or authorization.get("calibration_accessed") is not False
        or authorization.get("holdout_opened") is not False
        or authorization.get("claim_authorized") is not False
    ):
        raise ValueError("v24 source authorization review drift")
    plan = _read_json(top["training_plan"][0] / "training_plan_preflight.json")
    source_authority = plan.get("source_authority")
    if not isinstance(source_authority, Mapping) or set(source_authority) != {
        "merged_train_corpus", "merged_train_corpus_review", "atom_freeze", "atom_freeze_review"
    }:
        raise ValueError("v24 training plan source authority drift")
    for name, spec in source_authority.items():
        counts[f"plan_{name}"] = _verify_clean_seal(
            Path(str(spec.get("artifact"))), str(spec.get("artifact_root_sha256"))
        )
    merged = _read_json(top["merged_train_corpus"][0] / "merged_summary.json")
    for name in ("pilot", "pilot_review", "remaining", "remaining_review"):
        spec = merged.get("source_artifacts", {}).get(name)
        if not isinstance(spec, Mapping):
            raise ValueError("v24 direct corpus source authority drift")
        counts[f"direct_{name}"] = _verify_clean_seal(
            Path(str(spec.get("path"))), str(spec.get("root_sha256"))
        )
    return counts


def _live_eof(
    *, repo: Path, artifact: Path, root_sha256: str
) -> dict[str, str]:
    lines = (repo / AUDIT_RELATIVE).read_text(encoding="utf-8").rstrip().splitlines()
    eof = dict(line.split("=", 1) for line in lines[-20:] if "=" in line)
    expected = {
        "current_v24_status": (
            "v24_convex_selector_training_execution_complete_sealed_"
            "independent_review_pending"
        ),
        "current_v24_artifact_source_head": TRAINING_EXECUTION_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "current_v24_artifact": str(artifact),
        "current_v24_artifact_root_sha256": root_sha256,
        "global_stop_authorized": "false",
        "next_work_target": (
            "v24_convex_selector_training_execution_independent_review_only"
        ),
    }
    if any(eof.get(key) != value for key, value in expected.items()):
        raise ValueError("live v24 EOF does not authorize result review")
    current = (repo / CURRENT_STATUS_RELATIVE).read_text(encoding="utf-8")
    if any(f"{key}={value}" not in current for key, value in expected.items()):
        raise ValueError("live current-status v24 pointer drift")
    return eof


def _lock_free(path: Path) -> bool:
    import fcntl

    with path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _running_executor_pids() -> list[int]:
    pids = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            argv = (item / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        values = [part.decode("utf-8", errors="replace") for part in argv if part]
        if any(
            value == TRAINING_EXECUTOR_RELATIVE
            or value.endswith("/" + TRAINING_EXECUTOR_RELATIVE)
            for value in values
        ):
            pids.append(int(item.name))
    return sorted(pids)


def _static_reviewer_review(source: str) -> list[str]:
    tree = ast.parse(source)
    forbidden_names = {
        "solve_v24_cutting_plane",
        "train_learning_curve",
        "train_level",
        "_solve_master",
        "clarabel_only_solver_registry",
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    if (
        forbidden_names & (calls | attributes | imports)
        or "cvxpy" in imports
        or "torch" in imports
        or "_project_simplex_independent" not in source
        or "_losses_independent" not in source
        or "_empirical_cvar_independent" not in source
        or "training_source.load_training_inputs()" not in source
    ):
        raise ValueError("v24 result reviewer static no-solver contract drift")
    return [
        "reviewer_no_solver_call",
        "reviewer_no_training_call",
        "independent_simplex_projection",
        "independent_full_k_loss_recomputation",
        "independent_cvar_recomputation",
    ]


def _seal_artifact(root: Path) -> str:
    sums = root / "SHA256SUMS"
    receipt = root / "ROOT_SHA256SUMS"
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("v24 result review symlink is forbidden")
        if path.is_file() and path not in {sums, receipt}:
            if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
                raise ValueError("nested v24 review manifest is forbidden")
            files.append(path)
    files.sort()
    sums.write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(sums)
    receipt.write_text(f"{digest}  SHA256SUMS\n", encoding="ascii")
    return digest


def review_training_execution(
    *, repo: Path, dp_repo: Path, camp_head: str, artifact: Path,
    root_sha256: str,
) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("v24 training result review requires AutoDL")
    _require_clean_repo(repo, camp_head)
    _require_clean_repo(dp_repo, FIXED_DP_HEAD)
    eof = _live_eof(repo=repo, artifact=artifact, root_sha256=root_sha256)
    verified_training_files = _verify_clean_seal(artifact, root_sha256)
    manifest = _read_json(artifact / "training_manifest.json")
    progress = _read_json(artifact / "progress.json")
    expected_manifest = {
        "schema": "camp_dp_v24_convex_selector_training_execution_v1",
        "status": "passed",
        "camp_head": TRAINING_EXECUTION_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "route_count": 375,
        "retained_route_seed_count": 1875,
        "complete_route_seed_count": 1054,
        "failed_route_seed_count": 821,
        "snapshot_count": 67796,
        "candidate_count": 542368,
        "source_valid_candidate_count": 542368,
        "physical_feasible_candidate_count": 470138,
        "all_k_high_risk_snapshot_count": 7783,
        "primary_model_level_percent": 100,
        "full_train_model_frozen_for_later_calibration": True,
        "curve_models_used_for_model_selection": False,
        "v18_v22_weights_loaded": False,
        "candidate_generation_started": False,
        "simulator_executed": False,
        "actual_closed_loop_outcomes_read": False,
        "identity_fields_used_as_feature": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "epoch_semantics": False,
        "next_work_target": "v24_convex_selector_training_execution_independent_review_only",
    }
    if any(manifest.get(key) != value for key, value in expected_manifest.items()):
        raise ValueError("v24 training manifest identity or closed-boundary drift")
    if progress != {
        "schema": "camp_dp_v24_convex_training_progress_v1",
        "phase": "training_completed",
        "level_count": 4,
        "completed_levels": ["25", "50", "75", "100"],
        "total_offline_training_wall_clock_s": manifest.get(
            "total_offline_training_wall_clock_s"
        ),
        "training_execution_active": False,
    }:
        raise ValueError("v24 terminal training progress receipt drift")
    source_digests = _verify_source_provenance(
        repo=repo, current_head=camp_head, manifest=manifest
    )
    if (
        manifest.get("source_authorization_review_source_sha256")
        != source_digests[TRAINING_EXECUTOR_RELATIVE]
    ):
        raise ValueError("v24 training executor authorization SHA drift")
    upstream_counts = _verify_upstream_closure(manifest)
    inputs = training_source.load_training_inputs()
    if (
        manifest.get("source_verified_file_counts")
        != inputs.get("source_verified_file_counts")
        or manifest.get("direct_source_verified_file_counts")
        != inputs.get("direct_source_verified_file_counts")
        or manifest.get("failure_reason_counts")
        != inputs.get("failure_reason_counts")
    ):
        raise ValueError("v24 training input closure receipt drift")
    receipts = manifest.get("model_receipts")
    if not isinstance(receipts, Mapping) or set(receipts) != {"25", "50", "75", "100"}:
        raise ValueError("v24 four-level model receipt order drift")
    if manifest.get("primary_model_receipt") != receipts["100"]:
        raise ValueError("v24 full-train primary model receipt drift")
    models = {
        str(percent): _read_json(artifact / f"models/level_{percent}.json")
        for percent in EXPECTED_LEVELS
    }
    level_rows = []
    for level in inputs["levels"]:
        percent = int(level["percent"])
        level_rows.append(
            _review_level(
                artifact=artifact,
                manifest_receipt=receipts[str(percent)],
                model=models[str(percent)],
                inputs=inputs,
                level=level,
            )
        )
    per_level_wall_clock = sum(row["solver"]["offline_wall_clock_s"] for row in level_rows)
    total_wall_clock = float(manifest["total_offline_training_wall_clock_s"])
    if (
        total_wall_clock < per_level_wall_clock
        or total_wall_clock - per_level_wall_clock > 600.0
    ):
        raise ValueError("v24 total offline wall-clock receipt drift")
    running = _running_executor_pids()
    lock_free = [_lock_free(path) for path in LOCKS]
    free_bytes = shutil.disk_usage(artifact.parent).free
    if running or not all(lock_free) or free_bytes <= MINIMUM_FREE_BYTES:
        raise RuntimeError("v24 result review process/lock/disk gate failed")
    static_checks = _static_reviewer_review(
        (repo / REVIEWER_RELATIVE).read_text(encoding="utf-8")
    )
    checks = static_checks + [
        "training_complete_seal",
        "clean_zero_exit",
        "live_eof_result_review_authority",
        "current_and_execution_source_blobs",
        "fixed_dp_clean",
        "full_upstream_root_closure",
        "exact_denominator_counts",
        "four_fresh_learning_curve_levels",
        "full_train_primary_only",
        "weights_binary_sha_and_simplex",
        "cut_mask_binary_sha_and_membership",
        "raw_and_projected_four_gap_acceptance",
        "iterations_cuts_and_convergence",
        "training_metrics_recomputed",
        "learning_curve_metrics_recomputed",
        "no_curve_model_selection",
        "outcome_calibration_holdout_closed",
        "no_training_process",
        "all_locks_free",
        "disk_floor_passed",
    ]
    return {
        "schema": REVIEW_SCHEMA,
        "status": "passed",
        "camp_head": camp_head,
        "training_execution_head": TRAINING_EXECUTION_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_training_artifact": str(artifact),
        "source_training_root_sha256": root_sha256,
        "source_training_verified_file_count": verified_training_files,
        "source_digests": source_digests,
        "upstream_verified_file_counts": upstream_counts,
        "live_eof": eof,
        "input_counts": {
            "routes": 375,
            "retained_route_seeds": 1875,
            "complete_route_seeds": 1054,
            "failed_route_seeds": 821,
            "snapshots": 67796,
            "candidates": 542368,
            "source_valid_candidates": 542368,
            "physical_feasible_candidates": 470138,
            "all_k_high_risk_snapshots": 7783,
        },
        "atom_schema_version": "dp_camp_v10_14d",
        "active_atom_names": list(DP_CAMP_ATOM_NAMES_V10),
        "learning_curve": level_rows,
        "primary_level_percent": 100,
        "total_offline_training_wall_clock_s": total_wall_clock,
        "per_level_offline_training_wall_clock_s": per_level_wall_clock,
        "wall_clock_overhead_s": total_wall_clock - per_level_wall_clock,
        "passed_checks": checks,
        "passed_count": len(checks),
        "failed_count": 0,
        "running_executor_pids": running,
        "lock_free": lock_free,
        "free_bytes": free_bytes,
        "minimum_free_bytes": MINIMUM_FREE_BYTES,
        "training_reexecuted": False,
        "solver_called": False,
        "candidate_generation_started": False,
        "simulator_executed": False,
        "actual_closed_loop_outcomes_read": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "decision": {
            "training_result_accepted": True,
            "full_train_model_frozen": True,
            "paired_evaluation_plan_tdd_static_preflight_authorized": True,
            "calibration_execution_authorized": False,
            "holdout_authorized": False,
            "claim_authorized": False,
        },
        "next_work_target": "v24_paired_evaluation_plan_tdd_static_preflight_only",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--enable-independent-review", action="store_true")
    args = parser.parse_args(argv)
    if not args.enable_independent_review:
        raise RuntimeError("explicit v24 independent result review enable is required")
    if args.output_dir.exists() or not _safe_autodl_path(args.output_dir):
        raise FileExistsError("v24 result review output target is unsafe or exists")
    result = review_training_execution(
        repo=args.repo,
        dp_repo=args.dp_repo,
        camp_head=args.camp_head,
        artifact=args.artifact,
        root_sha256=args.artifact_root_sha256,
    )
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "review.json").write_bytes(_canonical_json_bytes(result))
    primary = result["learning_curve"][-1]
    weights = primary["weights"]
    (args.output_dir / "review.md").write_text(
        "# V24 Convex Selector Training Execution Independent Review\n\n"
        "- status: `passed`\n"
        "- training rerun / solver call: `false / false`\n"
        "- levels: `25 / 50 / 75 / 100`\n"
        f"- primary weights: `{json.dumps(weights, separators=(',', ':'))}`\n"
        f"- total offline training wall-clock: `{result['total_offline_training_wall_clock_s']}` seconds\n"
        "- calibration / holdout / outcomes / claims: `closed`\n"
        "- next: `paired-evaluation plan TDD/static preflight only`\n",
        encoding="utf-8",
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"TRAINING_EXECUTION_HEAD={TRAINING_EXECUTION_HEAD}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(
            {
                "status": "passed",
                "passed_count": result["passed_count"],
                "primary_weights_sha256": primary["weights_sha256"],
                "next_work_target": result["next_work_target"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root_sha256 = _seal_artifact(args.output_dir)
    print(json.dumps({"artifact_root_sha256": root_sha256}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
