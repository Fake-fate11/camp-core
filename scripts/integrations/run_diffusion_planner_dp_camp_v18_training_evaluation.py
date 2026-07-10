#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Mapping

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
    candidate_ranking_violations,
    project_simplex_rows,
    solve_robust_margin_cutting_plane,
)
from camp_core.integrations.nuplan_causal_adapter import (  # noqa: E402
    load_nuplan_expert_ego_future,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (  # noqa: E402
    FEASIBILITY_SCOPE,
    _verified_candidate_source,
    read_v18_status_pointer,
)


TRAINING_SEED = 3408
TIE_SEED = 3409
BOOTSTRAP_SEED = 3410
FORBIDDEN_SEEDS = (11, 12, 13)

SCALE_PERCENTILE = 95.0
MARGIN_SCALE = 0.1
MARGIN_CLIP = 2.0
CVAR_ALPHA = 0.9
L2_REG = 1e-4
MAX_ITER = 20
TOLERANCE = 1e-6
SOLVER = "CLARABEL"

MISS_THRESHOLD_M = 2.0
ADE_TIE_TOLERANCE_M = 1e-9
SCORE_TIE_TOLERANCE = 1e-12
BOOTSTRAP_REPLICATES = 10_000

BASELINE_INDEX = 0
BASELINE_SEMANTICS = "fixed_dp_deterministic_map_baseline"
NATIVE_RANKED_TOP1 = False

EXPECTED_TRAIN_COUNT = 214
EXPECTED_CALIBRATION_COUNT = 65
EXPECTED_HOLDOUT_COUNT = 71
EXPECTED_CANDIDATES = 8
EXPECTED_ATOMS = 14


@dataclass(frozen=True)
class SplitData:
    split: str
    rows: tuple[dict[str, Any], ...]
    atoms: np.ndarray
    feasible_mask: np.ndarray
    candidates: np.ndarray
    labels: np.ndarray | None


def tie_priority(candidate_count: int, *, seed: int = TIE_SEED) -> np.ndarray:
    if candidate_count <= 0:
        raise ValueError("candidate_count must be positive")
    if seed in FORBIDDEN_SEEDS:
        raise ValueError("formal seeds 11/12/13 are forbidden")
    order = np.random.default_rng(seed).permutation(candidate_count)
    priority = np.empty(candidate_count, dtype=np.int64)
    priority[order] = np.arange(candidate_count, dtype=np.int64)
    return priority


def candidate_ade_fde(
    candidates: np.ndarray, expert_future_xyh: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    expert = np.asarray(expert_future_xyh, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[2] < 2:
        raise ValueError("candidates must have shape [K,T,D>=2]")
    if expert.shape != (trajectories.shape[1], 3):
        raise ValueError("expert future must have shape [T,3]")
    if not np.all(np.isfinite(trajectories)) or not np.all(np.isfinite(expert)):
        raise ValueError("candidate and expert trajectories must be finite")
    distances = np.linalg.norm(
        trajectories[:, :, :2] - expert[None, :, :2], axis=2
    )
    return distances.mean(axis=1), distances[:, -1]


def _validate_metric_matrices(
    ade: np.ndarray, fde: np.ndarray, feasible_mask: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ade_values = np.asarray(ade, dtype=np.float64)
    fde_values = np.asarray(fde, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    if ade_values.ndim != 2 or fde_values.shape != ade_values.shape:
        raise ValueError("ADE and FDE must have matching shape [N,K]")
    if feasible.shape != ade_values.shape:
        raise ValueError("feasible mask must match ADE/FDE [N,K]")
    finite_feasible = feasible & np.isfinite(ade_values) & np.isfinite(fde_values)
    if not finite_feasible.any(axis=1).all():
        raise ValueError("each record must contain a finite feasible candidate")
    return ade_values, fde_values, finite_feasible


def oracle_indices(
    ade: np.ndarray,
    fde: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    priority: np.ndarray,
    ade_tolerance_m: float = ADE_TIE_TOLERANCE_M,
) -> np.ndarray:
    ade_values, fde_values, feasible = _validate_metric_matrices(
        ade, fde, feasible_mask
    )
    priority_values = np.asarray(priority, dtype=np.int64).reshape(-1)
    if priority_values.shape != (ade_values.shape[1],):
        raise ValueError("priority must match candidate count")
    if ade_tolerance_m < 0.0:
        raise ValueError("ADE tie tolerance must be nonnegative")
    result = np.empty(ade_values.shape[0], dtype=np.int64)
    for row_index in range(ade_values.shape[0]):
        indices = np.flatnonzero(feasible[row_index])
        minimum_ade = float(np.min(ade_values[row_index, indices]))
        indices = indices[
            ade_values[row_index, indices] <= minimum_ade + ade_tolerance_m
        ]
        minimum_fde = float(np.min(fde_values[row_index, indices]))
        indices = indices[
            fde_values[row_index, indices] <= minimum_fde + ade_tolerance_m
        ]
        result[row_index] = min(indices, key=lambda item: priority_values[item])
    return result


def train_atom_scales(
    atoms: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    percentile: float = SCALE_PERCENTILE,
) -> np.ndarray:
    atom_values = np.asarray(atoms, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    if atom_values.ndim != 3 or feasible.shape != atom_values.shape[:2]:
        raise ValueError("atoms [N,K,R] and feasible mask [N,K] must match")
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("percentile must be in [0,100]")
    rows = atom_values[feasible]
    if rows.size == 0 or not np.all(np.isfinite(rows)) or np.any(rows < 0.0):
        raise ValueError("feasible train atoms must be finite and nonnegative")
    scales = np.percentile(rows, percentile, axis=0)
    return np.maximum(scales, 1e-6)


def select_indices(
    scaled_atoms: np.ndarray,
    weights: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    priority: np.ndarray,
    score_tolerance: float = SCORE_TIE_TOLERANCE,
) -> tuple[np.ndarray, np.ndarray]:
    atoms = np.asarray(scaled_atoms, dtype=np.float64)
    weight_values = np.asarray(weights, dtype=np.float64).reshape(-1)
    feasible = np.asarray(feasible_mask, dtype=bool)
    priority_values = np.asarray(priority, dtype=np.int64).reshape(-1)
    if atoms.ndim != 3 or feasible.shape != atoms.shape[:2]:
        raise ValueError("scaled atoms [N,K,R] and feasible mask [N,K] must match")
    if weight_values.shape != (atoms.shape[2],):
        raise ValueError("weights must match atom dimension")
    if priority_values.shape != (atoms.shape[1],):
        raise ValueError("priority must match candidate count")
    if not np.all(np.isfinite(atoms)) or not np.all(np.isfinite(weight_values)):
        raise ValueError("atoms and weights must be finite")
    if np.any(atoms < 0.0) or np.any(weight_values < 0.0):
        raise ValueError("atoms and weights must be nonnegative")
    if not np.isclose(weight_values.sum(), 1.0, atol=1e-8, rtol=0.0):
        raise ValueError("weights must sum to one")
    if not feasible.any(axis=1).all():
        raise ValueError("each record must contain a finite feasible candidate")
    if score_tolerance < 0.0:
        raise ValueError("score tolerance must be nonnegative")
    scores = np.einsum("nkr,r->nk", atoms, weight_values)
    scores = np.where(feasible, scores, np.inf)
    selected = np.empty(atoms.shape[0], dtype=np.int64)
    for row_index in range(atoms.shape[0]):
        minimum = float(np.min(scores[row_index]))
        indices = np.flatnonzero(
            feasible[row_index]
            & (scores[row_index] <= minimum + score_tolerance)
        )
        selected[row_index] = min(
            indices, key=lambda item: priority_values[item]
        )
    return selected, scores


def ade_margins(
    ade: np.ndarray,
    oracle: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    margin_scale: float = MARGIN_SCALE,
    margin_clip: float = MARGIN_CLIP,
) -> np.ndarray:
    ade_values = np.asarray(ade, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    oracle_values = np.asarray(oracle, dtype=np.int64).reshape(-1)
    if ade_values.ndim != 2 or feasible.shape != ade_values.shape:
        raise ValueError("ADE and feasible mask must have shape [N,K]")
    if oracle_values.shape != (ade_values.shape[0],):
        raise ValueError("oracle must match record count")
    if margin_scale < 0.0 or margin_clip < 0.0:
        raise ValueError("margin scale and clip must be nonnegative")
    if not feasible[np.arange(ade_values.shape[0]), oracle_values].all():
        raise ValueError("each oracle candidate must be feasible")
    oracle_ade = ade_values[np.arange(ade_values.shape[0]), oracle_values]
    margins = np.clip(
        margin_scale * np.maximum(ade_values - oracle_ade[:, None], 0.0),
        0.0,
        margin_clip,
    )
    margins[~feasible] = 0.0
    margins[np.arange(ade_values.shape[0]), oracle_values] = 0.0
    return margins


def _bootstrap_intervals(
    deltas: Mapping[str, np.ndarray],
    groups: np.ndarray,
    *,
    replicates: int,
    rng: np.random.Generator,
) -> dict[str, list[float]]:
    group_values = np.asarray(groups)
    unique_groups = np.unique(group_values)
    if unique_groups.size == 0 or replicates <= 0:
        raise ValueError("bootstrap requires groups and positive replicates")
    samples = {name: np.empty(replicates, dtype=np.float64) for name in deltas}
    group_indices = {
        group: np.flatnonzero(group_values == group) for group in unique_groups
    }
    for replicate in range(replicates):
        drawn = rng.choice(unique_groups, size=unique_groups.size, replace=True)
        indices = np.concatenate([group_indices[group] for group in drawn])
        for name, values in deltas.items():
            samples[name][replicate] = float(np.mean(values[indices]))
    return {
        name: [
            float(np.percentile(values, 2.5)),
            float(np.percentile(values, 97.5)),
        ]
        for name, values in samples.items()
    }


def paired_cluster_bootstrap(
    deltas: Mapping[str, np.ndarray],
    *,
    log_ids: np.ndarray,
    scene_ids: np.ndarray,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict[str, list[float]]]:
    if seed in FORBIDDEN_SEEDS:
        raise ValueError("formal seeds 11/12/13 are forbidden")
    arrays = {
        name: np.asarray(values, dtype=np.float64).reshape(-1)
        for name, values in deltas.items()
    }
    if set(arrays) != {"ade", "fde", "miss"}:
        raise ValueError("paired deltas must contain ADE, FDE, and miss")
    size = next(iter(arrays.values())).size
    if any(values.size != size or not np.all(np.isfinite(values)) for values in arrays.values()):
        raise ValueError("paired deltas must be finite and share one length")
    logs = np.asarray(log_ids).reshape(-1)
    scenes = np.asarray(scene_ids).reshape(-1)
    if logs.size != size or scenes.size != size:
        raise ValueError("cluster ids must match paired deltas")
    log_seed, scene_seed = np.random.SeedSequence(seed).spawn(2)
    return {
        "log_cluster": _bootstrap_intervals(
            arrays,
            logs,
            replicates=replicates,
            rng=np.random.default_rng(log_seed),
        ),
        "scene_cluster": _bootstrap_intervals(
            arrays,
            scenes,
            replicates=replicates,
            rng=np.random.default_rng(scene_seed),
        ),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_sha_list(root: Path, sha256s: Path, expected_root: str) -> int:
    if _sha256(sha256s) != expected_root:
        raise ValueError("SHA256 list root mismatch")
    count = 0
    for line in sha256s.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(None, 1)
        path = root / relative.strip().removeprefix("./")
        if _sha256(path) != digest:
            raise ValueError(f"SHA256 mismatch: {path}")
        count += 1
    if count == 0:
        raise ValueError("SHA256 list is empty")
    return count


def _verify_artifact_root(root: Path, expected_root: str) -> dict[str, Any]:
    manifest = root / "SHA256SUMS"
    if _sha256(manifest) != expected_root:
        raise ValueError(f"artifact root SHA256 mismatch: {root}")
    _verify_sha_list(root, manifest, expected_root)
    summary_path = root / "summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _verify_training_inputs(args: Any) -> dict[str, Any]:
    canonical_entries = _verify_sha_list(
        args.canonical_root,
        args.canonical_sha256s,
        args.expected_canonical_root_sha256,
    )
    candidate_records, source_rows, _, _ = _verified_candidate_source(
        args.candidate_root,
        args.expected_candidate_root_sha256,
    )
    equivalence = _verify_artifact_root(
        args.equivalence_review,
        args.expected_equivalence_review_root_sha256,
    )
    review = equivalence.get("review") or {}
    if not (
        equivalence.get("status") == "passed"
        and review.get("equivalence_verified") is True
        and review.get("native_ranked_top1") is False
        and review.get("record_count") == 367
    ):
        raise ValueError("fixed-DP deterministic/MAP equivalence review failed")
    return {
        "canonical_manifest_entries": canonical_entries,
        "candidate_record_count": len(candidate_records),
        "candidate_source_count": len(source_rows),
        "equivalence_verified": True,
    }


def _canonical_rows(canonical_root: Path) -> list[dict[str, Any]]:
    path = canonical_root / "records.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def load_materialized_split(
    canonical_root: Path,
    candidate_root: Path,
    split: str,
    *,
    labels_required: bool,
) -> SplitData:
    rows = [
        row
        for row in _canonical_rows(canonical_root)
        if row["split"] == split and row["canonical_output_npz"] is not None
    ]
    atoms: list[np.ndarray] = []
    feasible_masks: list[np.ndarray] = []
    candidates: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    for row in rows:
        canonical_path = canonical_root / row["canonical_output_npz"]
        if _sha256(canonical_path) != row["canonical_output_npz_sha256"]:
            raise ValueError("canonical NPZ SHA256 mismatch")
        with np.load(canonical_path, allow_pickle=False) as archive:
            required = {
                "atom_matrix",
                "atom_names",
                "physical_feasible_mask",
                "schema_version",
                "source_candidate_npz",
                "source_candidate_npz_sha256",
                "baseline_index",
                "baseline_semantics",
                "native_ranked_top1",
                "feasibility_scope",
                "closed_loop_safety_claim",
            }
            missing = required - set(archive.files)
            if missing:
                raise ValueError(f"canonical NPZ missing fields: {sorted(missing)}")
            atom_matrix = np.array(archive["atom_matrix"], dtype=np.float64)
            feasible = np.array(archive["physical_feasible_mask"], dtype=bool)
            atom_names = tuple(str(value) for value in archive["atom_names"].tolist())
            source_relative = str(archive["source_candidate_npz"].item())
            source_sha = str(archive["source_candidate_npz_sha256"].item())
            has_label = "expert_ego_future_xyh" in archive.files
            if labels_required != has_label:
                boundary = "required" if labels_required else "forbidden"
                raise ValueError(f"expert label is {boundary} for split {split}")
            label = (
                None
                if not has_label
                else np.array(archive["expert_ego_future_xyh"], dtype=np.float64)
            )
            if (
                atom_matrix.shape != (EXPECTED_CANDIDATES, EXPECTED_ATOMS)
                or feasible.shape != (EXPECTED_CANDIDATES,)
                or not feasible.any()
                or not np.all(np.isfinite(atom_matrix))
                or np.any(atom_matrix < 0.0)
            ):
                raise ValueError("canonical atoms/feasibility contract mismatch")
            if atom_names != tuple(DP_CAMP_ATOM_NAMES_V10):
                raise ValueError("canonical 14D atom schema mismatch")
            if (
                str(archive["schema_version"].item()) != "dp_camp_v10_14d"
                or int(archive["baseline_index"].item()) != BASELINE_INDEX
                or str(archive["baseline_semantics"].item())
                != BASELINE_SEMANTICS
                or bool(archive["native_ranked_top1"].item())
                or str(archive["feasibility_scope"].item()) != FEASIBILITY_SCOPE
                or bool(archive["closed_loop_safety_claim"].item())
            ):
                raise ValueError("canonical baseline/scope contract mismatch")
        candidate_path = candidate_root / source_relative
        if _sha256(candidate_path) != source_sha:
            raise ValueError("source candidate NPZ SHA256 mismatch")
        with np.load(candidate_path, allow_pickle=False) as archive:
            candidate_tensor = np.array(
                archive["candidate_tensor"], dtype=np.float64
            )
        if candidate_tensor.shape != (EXPECTED_CANDIDATES, 80, 4):
            raise ValueError("candidate tensor must have shape [8,80,4]")
        if label is not None and (
            label.shape != (80, 3) or not np.all(np.isfinite(label))
        ):
            raise ValueError("expert future must be finite [80,3]")
        atoms.append(atom_matrix)
        feasible_masks.append(feasible)
        candidates.append(candidate_tensor)
        if label is not None:
            labels.append(label)
    if not rows:
        raise ValueError(f"no materialized {split} records")
    return SplitData(
        split=split,
        rows=tuple(rows),
        atoms=np.stack(atoms),
        feasible_mask=np.stack(feasible_masks),
        candidates=np.stack(candidates),
        labels=None if not labels_required else np.stack(labels),
    )


def _split_errors(data: SplitData) -> tuple[np.ndarray, np.ndarray]:
    if data.labels is None:
        raise ValueError(f"{data.split} labels are sealed")
    ade = np.empty(data.atoms.shape[:2], dtype=np.float64)
    fde = np.empty_like(ade)
    for index in range(data.atoms.shape[0]):
        ade[index], fde[index] = candidate_ade_fde(
            data.candidates[index], data.labels[index]
        )
    return ade, fde


def _paired_metric_summary(
    ade: np.ndarray,
    fde: np.ndarray,
    feasible_mask: np.ndarray,
    selected: np.ndarray,
    *,
    priority: np.ndarray,
) -> dict[str, Any]:
    oracle = oracle_indices(ade, fde, feasible_mask, priority=priority)
    rows = np.arange(ade.shape[0])
    selected_ade = ade[rows, selected]
    selected_fde = fde[rows, selected]
    baseline_ade = ade[:, BASELINE_INDEX]
    baseline_fde = fde[:, BASELINE_INDEX]
    oracle_ade = ade[rows, oracle]
    delta_ade = selected_ade - baseline_ade
    delta_fde = selected_fde - baseline_fde
    selected_miss = selected_fde > MISS_THRESHOLD_M
    baseline_miss = baseline_fde > MISS_THRESHOLD_M
    return {
        "records": int(ade.shape[0]),
        "camp": {
            "mean_ade_m": float(np.mean(selected_ade)),
            "mean_fde_m": float(np.mean(selected_fde)),
            "miss_rate": float(np.mean(selected_miss)),
        },
        "baseline": {
            "semantics": BASELINE_SEMANTICS,
            "mean_ade_m": float(np.mean(baseline_ade)),
            "mean_fde_m": float(np.mean(baseline_fde)),
            "miss_rate": float(np.mean(baseline_miss)),
        },
        "paired_delta_camp_minus_baseline": {
            "mean_ade_m": float(np.mean(delta_ade)),
            "mean_fde_m": float(np.mean(delta_fde)),
            "miss_rate": float(np.mean(selected_miss.astype(float) - baseline_miss)),
        },
        "better_tie_worse_by_ade": {
            "better": int(np.sum(delta_ade < -ADE_TIE_TOLERANCE_M)),
            "tie": int(np.sum(np.abs(delta_ade) <= ADE_TIE_TOLERANCE_M)),
            "worse": int(np.sum(delta_ade > ADE_TIE_TOLERANCE_M)),
        },
        "selection_oracle_gap_mean_ade_m": float(
            np.mean(selected_ade - oracle_ade)
        ),
        "baseline_oracle_gap_mean_ade_m": float(
            np.mean(baseline_ade - oracle_ade)
        ),
        "selected_baseline_index_count": int(np.sum(selected == BASELINE_INDEX)),
        "fallback_count": 0,
        "fallback_policy": "none_all_k_infeasible_records_excluded_fail_closed",
        "native_ranked_top1": False,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_root_manifest(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{_sha256(path)}  ./{path.relative_to(root).as_posix()}" for path in files
    ]
    manifest = root / "SHA256SUMS"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_sha = _sha256(manifest)
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha}  SHA256SUMS\n", encoding="utf-8"
    )
    return root_sha


def _accepted_weights_and_violations(
    result: Any,
    normalized_atoms: np.ndarray,
    oracle: np.ndarray,
    margins: np.ndarray,
    feasible: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if result.solver_name != SOLVER:
        raise RuntimeError(f"the frozen {SOLVER} solver is required")
    if result.solver_status != "optimal":
        raise RuntimeError("exact optimal solver status is required")
    if not result.converged:
        raise RuntimeError("cutting-plane master must be converged")
    if result.final_master_gap > TOLERANCE:
        raise RuntimeError("final master gap exceeds tolerance")
    if not result.history or result.history[-1].get("new_cuts") != 0:
        raise RuntimeError("final master has new cuts")
    raw = np.asarray(result.static_weights, dtype=np.float64).reshape(-1)
    if raw.shape != (EXPECTED_ATOMS,) or not np.all(np.isfinite(raw)):
        raise RuntimeError("static weights have invalid shape or values")
    if np.any(raw < -1e-8) or not np.isclose(raw.sum(), 1.0, atol=1e-8, rtol=0.0):
        raise RuntimeError("static weights violate nonnegative simplex")
    weights = project_simplex_rows(raw)[0]
    _, violations, _ = candidate_ranking_violations(
        normalized_atoms, weights, oracle, margins, feasible
    )
    recorded = np.asarray(result.train_violations, dtype=np.float64).reshape(-1)
    if recorded.shape != violations.shape or not np.allclose(
        recorded, violations, atol=TOLERANCE, rtol=0.0
    ):
        raise RuntimeError("independent complete-master violation review failed")
    return weights, violations


def run_train_calibrate(args: Any) -> dict[str, Any]:
    output = Path(args.output_dir)
    staging = output.with_name(output.name + ".tmp")
    if output.exists() or staging.exists():
        raise FileExistsError(output if output.exists() else staging)
    input_review = _verify_training_inputs(args)
    pointer = read_v18_status_pointer(args.current_status, args.v18_audit)
    train = load_materialized_split(
        args.canonical_root, args.candidate_root, "train", labels_required=True
    )
    calibration = load_materialized_split(
        args.canonical_root,
        args.candidate_root,
        "calibration",
        labels_required=True,
    )
    if train.atoms.shape[0] != EXPECTED_TRAIN_COUNT:
        raise ValueError("unexpected materialized train count")
    if calibration.atoms.shape[0] != EXPECTED_CALIBRATION_COUNT:
        raise ValueError("unexpected materialized calibration count")

    priority = tie_priority(EXPECTED_CANDIDATES)
    train_ade, train_fde = _split_errors(train)
    train_oracle = oracle_indices(
        train_ade, train_fde, train.feasible_mask, priority=priority
    )
    margins = ade_margins(train_ade, train_oracle, train.feasible_mask)
    scales = train_atom_scales(train.atoms, train.feasible_mask)
    normalized_train = train.atoms / scales.reshape(1, 1, -1)
    config = RobustMarginConfig(
        mode="static",
        risk_type="cvar",
        alpha=CVAR_ALPHA,
        l2_reg=L2_REG,
        max_iter=MAX_ITER,
        tolerance=TOLERANCE,
        solver=SOLVER,
        static_weight_lower_bounds=tuple(np.zeros(EXPECTED_ATOMS).tolist()),
    )
    np.random.seed(TRAINING_SEED)
    result = solve_robust_margin_cutting_plane(
        normalized_train,
        train_oracle,
        margins,
        train.feasible_mask,
        config=config,
        features=None,
    )
    weights, independent_violations = _accepted_weights_and_violations(
        result,
        normalized_train,
        train_oracle,
        margins,
        train.feasible_mask,
    )
    train_selected, _ = select_indices(
        normalized_train, weights, train.feasible_mask, priority=priority
    )
    calibration_ade, calibration_fde = _split_errors(calibration)
    calibration_selected, _ = select_indices(
        calibration.atoms / scales.reshape(1, 1, -1),
        weights,
        calibration.feasible_mask,
        priority=priority,
    )
    train_metrics = _paired_metric_summary(
        train_ade,
        train_fde,
        train.feasible_mask,
        train_selected,
        priority=priority,
    )
    calibration_metrics = _paired_metric_summary(
        calibration_ade,
        calibration_fde,
        calibration.feasible_mask,
        calibration_selected,
        priority=priority,
    )

    staging.mkdir(parents=True)
    np.save(staging / "static_weights.npy", weights)
    _write_json(
        staging / "atom_scales.json",
        {
            "schema_version": "dp_camp_v10_14d",
            "atom_names": list(DP_CAMP_ATOM_NAMES_V10),
            "fit_scope": "train_feasible_candidate_rows_only",
            "percentile": SCALE_PERCENTILE,
            "scales": scales.tolist(),
        },
    )
    calibration_summary = {
        "status": "passed",
        "mode": "tuning_free_diagnostics_only",
        "model_or_scale_updates": 0,
        "records": EXPECTED_CALIBRATION_COUNT,
        "metrics": calibration_metrics,
    }
    _write_json(staging / "calibration_summary.json", calibration_summary)
    protocol = {
        "status": "frozen",
        "baseline_semantics": BASELINE_SEMANTICS,
        "equivalence_verified": True,
        "native_ranked_top1": False,
        "feasibility_scope": FEASIBILITY_SCOPE,
        "closed_loop_safety_claim": False,
        "holdout_label_reads": 0,
        "training_seed": TRAINING_SEED,
        "tie_seed": TIE_SEED,
        "tie_priority": priority.tolist(),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "ci_level": 0.95,
        "miss_threshold_m": MISS_THRESHOLD_M,
        "ade_tie_tolerance_m": ADE_TIE_TOLERANCE_M,
        "score_tie_tolerance": SCORE_TIE_TOLERANCE,
        "non_regression_slack": 0.0,
        "latency_repetitions_per_record": 1000,
        "expected_holdout_records": EXPECTED_HOLDOUT_COUNT,
        "raw_holdout_labels_persisted": False,
        "claim_scope": "nuplan_mini_smoke_directional_only_no_performance_or_safety_claim",
        "canonical_root_sha256": args.expected_canonical_root_sha256,
        "candidate_root_sha256": args.expected_candidate_root_sha256,
        "equivalence_review_root_sha256": (
            args.expected_equivalence_review_root_sha256
        ),
        "weights_sha256": _sha256(staging / "static_weights.npy"),
        "atom_scales_sha256": _sha256(staging / "atom_scales.json"),
    }
    _write_json(staging / "paired_eval_protocol.json", protocol)
    summary = {
        "status": "passed",
        "schema_version": "dp_camp_v18_static_14d_train_calibrate_v1",
        "mode": "static",
        "score": "a_scaled_k_transpose_w",
        "train_records": EXPECTED_TRAIN_COUNT,
        "calibration_records": EXPECTED_CALIBRATION_COUNT,
        "holdout_label_reads": 0,
        "atom_scaling_scope": "train_feasible_candidate_rows_only",
        "label_primary": "expert_future_ade",
        "label_tie_break": "expert_future_fde_then_seeded_candidate_priority",
        "risk_type": "cvar",
        "alpha": CVAR_ALPHA,
        "l2_reg": L2_REG,
        "max_iter": MAX_ITER,
        "tolerance": TOLERANCE,
        "solver": SOLVER,
        "solver_name": result.solver_name,
        "solver_status": result.solver_status,
        "converged": bool(result.converged),
        "final_master_gap": float(result.final_master_gap),
        "final_new_cuts": int(result.history[-1]["new_cuts"]),
        "maximum_independent_violation": float(np.max(independent_violations)),
        "weights": weights.tolist(),
        "simplex_sum": float(weights.sum()),
        "minimum_weight": float(weights.min()),
        "train_metrics": train_metrics,
        "calibration_metrics": calibration_metrics,
        "history": result.history,
        "cuts_per_scene": list(result.cuts_per_scene),
        "controller_pointer": pointer,
        "input_review": input_review,
        "baseline_semantics": BASELINE_SEMANTICS,
        "equivalence_verified": True,
        "native_ranked_top1": False,
        "feasibility_scope": FEASIBILITY_SCOPE,
        "closed_loop_safety_claim": False,
        "candidate_generation_executed": False,
        "candidate_tensor_mutation": False,
        "mini_evidence_scope": "smoke_directional_only",
    }
    _write_json(staging / "training_summary.json", summary)
    _write_root_manifest(staging)
    os.replace(staging, output)
    return summary


def load_frozen_selector(root: Path, expected_root: str) -> dict[str, Any]:
    manifest = root / "SHA256SUMS"
    _verify_sha_list(root, manifest, expected_root)
    protocol = json.loads(
        (root / "paired_eval_protocol.json").read_text(encoding="utf-8")
    )
    training = json.loads(
        (root / "training_summary.json").read_text(encoding="utf-8")
    )
    weights = np.asarray(np.load(root / "static_weights.npy"), dtype=np.float64)
    scales_payload = json.loads(
        (root / "atom_scales.json").read_text(encoding="utf-8")
    )
    scales = np.asarray(scales_payload["scales"], dtype=np.float64)
    if (
        training.get("status") != "passed"
        or training.get("holdout_label_reads") != 0
        or protocol.get("status") != "frozen"
        or protocol.get("equivalence_verified") is not True
        or protocol.get("native_ranked_top1") is not False
        or protocol.get("baseline_semantics") != BASELINE_SEMANTICS
        or protocol.get("feasibility_scope") != FEASIBILITY_SCOPE
        or protocol.get("closed_loop_safety_claim") is not False
        or protocol.get("holdout_label_reads") != 0
        or protocol.get("raw_holdout_labels_persisted") is not False
    ):
        raise ValueError("frozen selector/protocol contract mismatch")
    if (
        weights.shape != (EXPECTED_ATOMS,)
        or scales.shape != (EXPECTED_ATOMS,)
        or not np.all(np.isfinite(weights))
        or not np.all(np.isfinite(scales))
        or np.any(weights < 0.0)
        or np.any(scales <= 0.0)
        or not np.isclose(weights.sum(), 1.0, atol=1e-8, rtol=0.0)
    ):
        raise ValueError("frozen selector weights/scales contract mismatch")
    if (
        _sha256(root / "static_weights.npy") != protocol["weights_sha256"]
        or _sha256(root / "atom_scales.json")
        != protocol["atom_scales_sha256"]
    ):
        raise ValueError("frozen selector SHA256 mismatch")
    return {
        "weights": weights,
        "scales": scales,
        "protocol": protocol,
        "training": training,
        "root_sha256": expected_root,
    }


def verify_freeze_review(
    root: Path, expected_root: str, expected_freeze_root: str
) -> dict[str, Any]:
    summary = _verify_artifact_root(root, expected_root)
    review = summary.get("review") or {}
    if not (
        summary.get("status") == "passed"
        and summary.get("run_exit") == 0
        and summary.get("stderr_empty") is True
        and review.get("status") == "passed"
        and review.get("freeze_root_sha256") == expected_freeze_root
        and review.get("holdout_label_reads") == 0
        and review.get("native_ranked_top1") is False
    ):
        raise ValueError("freeze result review is missing, failed, or mismatched")
    return review


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["log_token"]),
        str(row["scene_token"]),
        str(row["decision_token"]),
    )


def _verify_evaluation_inputs(args: Any) -> dict[str, Any]:
    training_inputs = _verify_training_inputs(args)
    selector = load_frozen_selector(
        args.freeze_root, args.expected_freeze_root_sha256
    )
    freeze_review = verify_freeze_review(
        args.freeze_review,
        args.expected_freeze_review_root_sha256,
        args.expected_freeze_root_sha256,
    )
    _, source_rows, _, _ = _verified_candidate_source(
        args.candidate_root, args.expected_candidate_root_sha256
    )
    source_by_identity = {_identity(row): row for row in source_rows}
    if len(source_by_identity) != len(source_rows):
        raise ValueError("candidate source identities are not unique")
    return {
        "training_inputs": training_inputs,
        "freeze": selector["training"],
        "freeze_review": freeze_review,
        "selector": selector,
        "source_by_identity": source_by_identity,
    }


def _materialized_identity_sets(
    canonical_root: Path,
) -> tuple[dict[str, set[tuple[str, str, str]]], int]:
    by_split: dict[str, set[tuple[str, str, str]]] = {
        "train": set(),
        "calibration": set(),
        "holdout": set(),
    }
    excluded_holdout = 0
    for row in _canonical_rows(canonical_root):
        split = str(row["split"])
        if split == "holdout" and row.get("canonical_output_npz") is None:
            excluded_holdout += 1
        if row.get("canonical_output_npz", True) is not None:
            by_split.setdefault(split, set()).add(_identity(row))
    if (
        by_split["train"] & by_split["calibration"]
        or by_split["train"] & by_split["holdout"]
        or by_split["calibration"] & by_split["holdout"]
    ):
        raise ValueError("materialized split overlap detected")
    return by_split, excluded_holdout


def _evaluation_paths(args: Any) -> tuple[Path, Path]:
    output = Path(args.output_dir)
    return output, output.with_name(output.name + ".tmp")


def run_paired_eval_preflight(args: Any) -> dict[str, Any]:
    output, staging = _evaluation_paths(args)
    if output.exists() or staging.exists():
        raise FileExistsError(output if output.exists() else staging)
    context = _verify_evaluation_inputs(args)
    pointer = read_v18_status_pointer(args.current_status, args.v18_audit)
    holdout = load_materialized_split(
        args.canonical_root,
        args.candidate_root,
        "holdout",
        labels_required=False,
    )
    if holdout.atoms.shape[0] != EXPECTED_HOLDOUT_COUNT:
        raise ValueError("unexpected materialized holdout count")
    if holdout.labels is not None:
        raise RuntimeError("holdout labels were opened during preflight")
    by_split, excluded_holdout = _materialized_identity_sets(args.canonical_root)
    if len(by_split["holdout"]) != EXPECTED_HOLDOUT_COUNT:
        raise ValueError("holdout identity count mismatch")
    missing_sources = [
        _identity(row)
        for row in holdout.rows
        if _identity(row) not in context["source_by_identity"]
    ]
    if missing_sources:
        raise ValueError("holdout source identity missing")
    return {
        "status": "passed",
        "holdout_records": EXPECTED_HOLDOUT_COUNT,
        "excluded_holdout_source_rows": excluded_holdout,
        "holdout_label_reads": 0,
        "raw_holdout_labels_persisted": False,
        "output_absent": True,
        "staging_absent": True,
        "split_overlap": 0,
        "equivalence_verified": True,
        "baseline_semantics": BASELINE_SEMANTICS,
        "native_ranked_top1": False,
        "feasibility_scope": FEASIBILITY_SCOPE,
        "closed_loop_safety_claim": False,
        "controller_pointer": pointer,
    }


def _array_sha256(array: np.ndarray) -> str:
    values = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(values.dtype).encode("utf-8"))
    digest.update(json.dumps(list(values.shape)).encode("utf-8"))
    digest.update(values.view(np.uint8))
    return digest.hexdigest()


def _measure_selector_latency_ms(
    atoms: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
    feasible: np.ndarray,
    priority: np.ndarray,
    *,
    repetitions_per_record: int,
) -> dict[str, float]:
    if repetitions_per_record <= 0:
        raise ValueError("latency repetitions must be positive")
    samples = np.empty(
        atoms.shape[0] * repetitions_per_record, dtype=np.float64
    )
    sample_index = 0
    for record_index in range(atoms.shape[0]):
        for _ in range(repetitions_per_record):
            started = time.perf_counter_ns()
            select_indices(
                atoms[record_index : record_index + 1]
                / scales.reshape(1, 1, -1),
                weights,
                feasible[record_index : record_index + 1],
                priority=priority,
            )
            samples[sample_index] = (time.perf_counter_ns() - started) / 1e6
            sample_index += 1
    return {
        "p50": float(np.percentile(samples, 50.0)),
        "p95": float(np.percentile(samples, 95.0)),
        "p99": float(np.percentile(samples, 99.0)),
        "max": float(np.max(samples)),
    }


def run_paired_eval(
    args: Any,
    *,
    label_loader=load_nuplan_expert_ego_future,
) -> dict[str, Any]:
    output, staging = _evaluation_paths(args)
    if output.exists() or staging.exists():
        raise FileExistsError(output if output.exists() else staging)
    preflight = run_paired_eval_preflight(args)
    context = _verify_evaluation_inputs(args)
    selector = context["selector"]
    holdout = load_materialized_split(
        args.canonical_root,
        args.candidate_root,
        "holdout",
        labels_required=False,
    )
    protocol = selector["protocol"]
    if int(protocol["expected_holdout_records"]) != EXPECTED_HOLDOUT_COUNT:
        raise ValueError("frozen protocol holdout count mismatch")
    priority = np.asarray(protocol["tie_priority"], dtype=np.int64)
    weights = selector["weights"]
    scales = selector["scales"]
    selected, scores = select_indices(
        holdout.atoms / scales.reshape(1, 1, -1),
        weights,
        holdout.feasible_mask,
        priority=priority,
        score_tolerance=float(protocol["score_tie_tolerance"]),
    )
    latency = _measure_selector_latency_ms(
        holdout.atoms,
        scales,
        weights,
        holdout.feasible_mask,
        priority,
        repetitions_per_record=int(protocol["latency_repetitions_per_record"]),
    )

    staging.mkdir(parents=True)
    records_path = staging / "records.jsonl"
    receipts_path = staging / "holdout_label_receipts.jsonl"
    evaluation_rows: list[dict[str, Any]] = []
    all_ade = np.empty((EXPECTED_HOLDOUT_COUNT, EXPECTED_CANDIDATES))
    all_fde = np.empty_like(all_ade)
    with records_path.open("w", encoding="utf-8") as records_stream, receipts_path.open(
        "w", encoding="utf-8"
    ) as receipt_stream:
        for index, row in enumerate(holdout.rows):
            identity = _identity(row)
            source = context["source_by_identity"][identity]
            label = np.asarray(
                label_loader(
                    source["db_path"],
                    source["decision_token"],
                    target_dt_s=0.1,
                    horizon_steps=80,
                ),
                dtype=np.float64,
            )
            if label.shape != (80, 3) or not np.all(np.isfinite(label)):
                raise ValueError("holdout expert future must be finite [80,3]")
            label_sha = _array_sha256(label)
            ade, fde = candidate_ade_fde(holdout.candidates[index], label)
            all_ade[index] = ade
            all_fde[index] = fde
            oracle = int(
                oracle_indices(
                    ade[None, :],
                    fde[None, :],
                    holdout.feasible_mask[index : index + 1],
                    priority=priority,
                    ade_tolerance_m=float(protocol["ade_tie_tolerance_m"]),
                )[0]
            )
            selected_index = int(selected[index])
            evidence = {
                "record_index": index,
                "split": "holdout",
                "log_token": identity[0],
                "scene_token": identity[1],
                "decision_token": identity[2],
                "expert_future_sha256": label_sha,
                "candidate_ade_m": ade.tolist(),
                "candidate_fde_m": fde.tolist(),
                "physical_feasible_mask": holdout.feasible_mask[index].tolist(),
                "candidate_scores": [
                    float(scores[index, candidate_index])
                    if holdout.feasible_mask[index, candidate_index]
                    else None
                    for candidate_index in range(EXPECTED_CANDIDATES)
                ],
                "selected_index": selected_index,
                "baseline_index": BASELINE_INDEX,
                "oracle_index": oracle,
                "selected_ade_m": float(ade[selected_index]),
                "baseline_ade_m": float(ade[BASELINE_INDEX]),
                "oracle_ade_m": float(ade[oracle]),
                "selected_fde_m": float(fde[selected_index]),
                "baseline_fde_m": float(fde[BASELINE_INDEX]),
                "baseline_semantics": BASELINE_SEMANTICS,
                "native_ranked_top1": False,
            }
            receipt = {
                key: evidence[key]
                for key in (
                    "record_index",
                    "log_token",
                    "scene_token",
                    "decision_token",
                    "expert_future_sha256",
                )
            }
            evaluation_rows.append(evidence)
            records_stream.write(json.dumps(evidence, sort_keys=True) + "\n")
            records_stream.flush()
            receipt_stream.write(json.dumps(receipt, sort_keys=True) + "\n")
            receipt_stream.flush()

    aggregate = _paired_metric_summary(
        all_ade,
        all_fde,
        holdout.feasible_mask,
        selected,
        priority=priority,
    )
    rows = np.arange(EXPECTED_HOLDOUT_COUNT)
    selected_ade = all_ade[rows, selected]
    selected_fde = all_fde[rows, selected]
    baseline_ade = all_ade[:, BASELINE_INDEX]
    baseline_fde = all_fde[:, BASELINE_INDEX]
    deltas = {
        "ade": selected_ade - baseline_ade,
        "fde": selected_fde - baseline_fde,
        "miss": (selected_fde > MISS_THRESHOLD_M).astype(float)
        - (baseline_fde > MISS_THRESHOLD_M).astype(float),
    }
    ci95 = paired_cluster_bootstrap(
        deltas,
        log_ids=np.asarray([row["log_token"] for row in holdout.rows]),
        scene_ids=np.asarray([row["scene_token"] for row in holdout.rows]),
        replicates=int(protocol["bootstrap_replicates"]),
        seed=int(protocol["bootstrap_seed"]),
    )
    paired_delta = aggregate["paired_delta_camp_minus_baseline"]
    summary = {
        "status": "passed",
        "schema_version": "dp_camp_v18_nuplan_mini_one_shot_paired_eval_v1",
        "holdout_records": EXPECTED_HOLDOUT_COUNT,
        "holdout_label_reads": EXPECTED_HOLDOUT_COUNT,
        "holdout_label_receipts": len(evaluation_rows),
        "distinct_holdout_label_sha256": len(
            {row["expert_future_sha256"] for row in evaluation_rows}
        ),
        "raw_holdout_labels_persisted": False,
        "aggregate": aggregate,
        "paired_ci95": ci95,
        "non_regression": {
            "fde": bool(paired_delta["mean_fde_m"] <= 0.0),
            "miss": bool(paired_delta["miss_rate"] <= 0.0),
            "slack": 0.0,
        },
        "selector_latency_ms": latency,
        "fallback_count": int(aggregate["fallback_count"]),
        "fallback_policy": aggregate["fallback_policy"],
        "excluded_holdout_source_rows": preflight[
            "excluded_holdout_source_rows"
        ],
        "baseline_semantics": BASELINE_SEMANTICS,
        "equivalence_verified": True,
        "native_ranked_top1": False,
        "feasibility_scope": FEASIBILITY_SCOPE,
        "closed_loop_safety_claim": False,
        "mini_evidence_scope": "smoke_directional_only_no_performance_or_safety_claim",
        "candidate_generation_executed": False,
        "candidate_tensor_mutation": False,
        "model_or_scale_updates": 0,
        "freeze_root_sha256": args.expected_freeze_root_sha256,
        "candidate_root_sha256": args.expected_candidate_root_sha256,
        "canonical_root_sha256": args.expected_canonical_root_sha256,
        "equivalence_review_root_sha256": (
            args.expected_equivalence_review_root_sha256
        ),
        "controller_pointer": preflight["controller_pointer"],
    }
    _write_json(staging / "summary.json", summary)
    _write_root_manifest(staging)
    os.replace(staging, output)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train/freeze the v18 static 14D CAMP selector or run its frozen "
            "one-shot nuPlan-mini paired evaluation."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("train-calibrate", "paired-eval-preflight", "paired-eval"),
        required=True,
    )
    parser.add_argument("--canonical_root", type=Path, required=True)
    parser.add_argument("--canonical_sha256s", type=Path, required=True)
    parser.add_argument("--expected_canonical_root_sha256", required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_candidate_root_sha256", required=True)
    parser.add_argument("--equivalence_review", type=Path, required=True)
    parser.add_argument(
        "--expected_equivalence_review_root_sha256", required=True
    )
    parser.add_argument("--freeze_root", type=Path)
    parser.add_argument("--expected_freeze_root_sha256")
    parser.add_argument("--freeze_review", type=Path)
    parser.add_argument("--expected_freeze_review_root_sha256")
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_status", type=Path, required=True)
    parser.add_argument("--v18_audit", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.mode != "train-calibrate" and (
        args.freeze_root is None
        or args.expected_freeze_root_sha256 is None
        or args.freeze_review is None
        or args.expected_freeze_review_root_sha256 is None
    ):
        parser.error(
            "paired evaluation modes require frozen selector and independent "
            "freeze-review roots with SHA256 values"
        )
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.mode == "train-calibrate":
        report = run_train_calibrate(args)
    elif args.mode == "paired-eval-preflight":
        report = run_paired_eval_preflight(args)
    else:
        report = run_paired_eval(args)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
