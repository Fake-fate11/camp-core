from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner import DP_CAMP_ATOM_NAMES_V10
from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (
    _verified_candidate_source,
    read_v18_status_pointer,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v18_training_evaluation import (
    BASELINE_INDEX,
    BASELINE_SEMANTICS,
    _bootstrap_intervals,
    _sha256,
    _verify_artifact_root,
    _verify_sha_list,
    _write_json,
    _write_root_manifest,
    load_materialized_split,
)


DT_S = 0.1
CLEARANCE_CLIP_M = 3.0
MAX_OVERSPEED_MPS = 2.23
MIN_PROGRESS_RATIO = 0.2
RED_COST_TOLERANCE = 1e-12
SCORE_TIE_TOLERANCE = 1e-9
BOOTSTRAP_SEED = 3410
BOOTSTRAP_REPLICATES = 10_000
EXPECTED_HOLDOUT_COUNT = 71
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"

MIN_LONGITUDINAL_ACCELERATION_MPS2 = -4.05
MAX_LONGITUDINAL_ACCELERATION_MPS2 = 2.40
MAX_ABS_LATERAL_ACCELERATION_MPS2 = 4.89
MAX_ABS_YAW_ACCELERATION_RPS2 = 1.93
MAX_ABS_YAW_RATE_RPS = 0.95
MAX_ABS_LONGITUDINAL_JERK_MPS3 = 4.13
MAX_JERK_MAGNITUDE_MPS3 = 8.37


def trajectory_comfort_pass(
    candidates: np.ndarray, dt: float = DT_S
) -> np.ndarray:
    trajectories = np.asarray(candidates, dtype=np.float64)
    if (
        trajectories.ndim != 3
        or trajectories.shape[1:] != (80, 4)
        or not np.isfinite(trajectories).all()
    ):
        raise ValueError("candidates must be finite [K,80,4]")
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive")
    heading_vectors = trajectories[:, :, 2:4]
    norms = np.linalg.norm(heading_vectors, axis=2)
    if np.any(norms < 0.5):
        raise ValueError("candidate headings must be valid")
    heading_vectors = heading_vectors / norms[:, :, None]
    headings = np.unwrap(
        np.arctan2(heading_vectors[:, :, 1], heading_vectors[:, :, 0]), axis=1
    )

    velocity = np.diff(trajectories[:, :, :2], axis=1) / float(dt)
    acceleration = np.diff(velocity, axis=1) / float(dt)
    jerk = np.diff(acceleration, axis=1) / float(dt)
    acceleration_heading = heading_vectors[:, 2:, :]
    lateral_axes = np.stack(
        [-acceleration_heading[:, :, 1], acceleration_heading[:, :, 0]], axis=2
    )
    longitudinal_acceleration = np.sum(
        acceleration * acceleration_heading, axis=2
    )
    lateral_acceleration = np.sum(acceleration * lateral_axes, axis=2)
    yaw_rate = np.diff(headings, axis=1) / float(dt)
    yaw_acceleration = np.diff(yaw_rate, axis=1) / float(dt)
    longitudinal_jerk = np.sum(jerk * heading_vectors[:, 3:, :], axis=2)
    tolerance = 1e-9

    return (
        (np.min(longitudinal_acceleration, axis=1)
         >= MIN_LONGITUDINAL_ACCELERATION_MPS2 - tolerance)
        & (np.max(longitudinal_acceleration, axis=1)
           <= MAX_LONGITUDINAL_ACCELERATION_MPS2 + tolerance)
        & (np.max(np.abs(lateral_acceleration), axis=1)
           <= MAX_ABS_LATERAL_ACCELERATION_MPS2 + tolerance)
        & (np.max(np.abs(yaw_acceleration), axis=1)
           <= MAX_ABS_YAW_ACCELERATION_RPS2 + tolerance)
        & (np.max(np.abs(yaw_rate), axis=1)
           <= MAX_ABS_YAW_RATE_RPS + tolerance)
        & (np.max(np.abs(longitudinal_jerk), axis=1)
           <= MAX_ABS_LONGITUDINAL_JERK_MPS3 + tolerance)
        & (np.max(np.linalg.norm(jerk, axis=2), axis=1)
           <= MAX_JERK_MAGNITUDE_MPS3 + tolerance)
    )


def candidate_safety_components(
    *,
    atom_matrix: np.ndarray,
    candidates: np.ndarray,
    lane_feasible_mask: np.ndarray,
    obb_collision_free_mask: np.ndarray,
    physical_feasible_mask: np.ndarray,
    route_progress: np.ndarray,
    progress_reference: float,
    minimum_obb_clearance: np.ndarray,
    planned_red_light_cost: np.ndarray,
) -> dict[str, np.ndarray]:
    atoms = np.asarray(atom_matrix, dtype=np.float64)
    trajectories = np.asarray(candidates, dtype=np.float64)
    if atoms.ndim != 2 or atoms.shape[1] != len(DP_CAMP_ATOM_NAMES_V10):
        raise ValueError("atom_matrix must have shape [K,14]")
    candidate_count = atoms.shape[0]
    if trajectories.shape != (candidate_count, 80, 4):
        raise ValueError("candidates must have shape [K,80,4]")
    arrays = {
        "atom_matrix": atoms,
        "candidates": trajectories,
        "lane_feasible_mask": np.asarray(lane_feasible_mask).reshape(-1),
        "obb_collision_free_mask": np.asarray(
            obb_collision_free_mask
        ).reshape(-1),
        "physical_feasible_mask": np.asarray(physical_feasible_mask).reshape(-1),
        "route_progress": np.asarray(route_progress, dtype=np.float64).reshape(-1),
        "minimum_obb_clearance": np.asarray(
            minimum_obb_clearance, dtype=np.float64
        ),
        "planned_red_light_cost": np.asarray(
            planned_red_light_cost, dtype=np.float64
        ).reshape(-1),
    }
    if any(
        values.shape != (candidate_count,)
        for name, values in arrays.items()
        if name not in {"atom_matrix", "candidates", "minimum_obb_clearance"}
    ) or arrays["minimum_obb_clearance"].shape != (candidate_count, 80):
        raise ValueError("candidate component shapes must match K")
    if (
        not all(np.isfinite(values).all() for values in arrays.values())
        or not np.isfinite(progress_reference)
    ):
        raise ValueError("candidate safety inputs must be finite")
    if np.any(atoms < 0.0) or np.any(arrays["planned_red_light_cost"] < 0.0):
        raise ValueError("candidate safety costs must be nonnegative")

    lane = arrays["lane_feasible_mask"].astype(bool)
    collision = arrays["obb_collision_free_mask"].astype(bool)
    physical = arrays["physical_feasible_mask"].astype(bool)
    red = arrays["planned_red_light_cost"] <= RED_COST_TOLERANCE
    progress = np.clip(
        np.maximum(arrays["route_progress"], 0.1)
        / max(float(progress_reference), 0.1),
        0.0,
        1.0,
    )
    making_progress = progress >= MIN_PROGRESS_RATIO
    clearance_m = np.min(arrays["minimum_obb_clearance"], axis=1)
    clearance = np.clip(clearance_m / CLEARANCE_CLIP_M, 0.0, 1.0)
    duration_s = (trajectories.shape[1] - 1) * DT_S
    rms_overspeed = np.sqrt(atoms[:, 4] / duration_s)
    speed = np.clip(1.0 - rms_overspeed / MAX_OVERSPEED_MPS, 0.0, 1.0)
    comfort = trajectory_comfort_pass(trajectories).astype(np.float64)
    soft = (5.0 * clearance + 4.0 * speed + 5.0 * progress + 2.0 * comfort) / 16.0
    score = 100.0 * (collision & lane & red & making_progress) * soft

    return {
        "bounded_offline_safety_score": score,
        "collision_free": collision,
        "lane_compliant": lane,
        "red_light_compliant": red,
        "making_progress": making_progress,
        "physical_feasible": physical,
        "clearance_score": clearance,
        "minimum_obb_clearance_m": clearance_m,
        "speed_score": speed,
        "rms_overspeed_mps": rms_overspeed,
        "progress_score": progress,
        "comfort_score": comfort,
        "planned_red_light_cost": arrays["planned_red_light_cost"],
        "red_stopping_margin_cost": atoms[:, 12],
    }


def _verify_sources(args: Any) -> None:
    _verify_sha_list(
        args.canonical_root,
        args.canonical_sha256s,
        args.expected_canonical_root_sha256,
    )
    _verified_candidate_source(
        args.candidate_root, args.expected_candidate_root_sha256
    )


def load_candidate_component_inputs(
    canonical_root: Path, rows: tuple[dict[str, Any], ...]
) -> dict[str, np.ndarray]:
    fields = {
        "lane_feasible_mask",
        "obb_collision_free_mask",
        "physical_feasible_mask",
        "route_progress",
        "progress_reference",
        "minimum_obb_clearance",
        "minimum_obb_clearance_clip_m",
        "planned_red_light_cost",
    }
    loaded: dict[str, list[np.ndarray]] = {field: [] for field in fields}
    for row in rows:
        path = canonical_root / row["canonical_output_npz"]
        if _sha256(path) != row["canonical_output_npz_sha256"]:
            raise ValueError("canonical component NPZ SHA256 mismatch")
        with np.load(path, allow_pickle=False) as archive:
            missing = fields - set(archive.files)
            if missing:
                raise ValueError(f"canonical safety fields missing: {sorted(missing)}")
            for field in fields:
                loaded[field].append(np.array(archive[field]))
    result = {field: np.stack(values) for field, values in loaded.items()}
    clip = np.asarray(result.pop("minimum_obb_clearance_clip_m"), dtype=float)
    if not np.allclose(clip, CLEARANCE_CLIP_M, atol=0.0, rtol=0.0):
        raise ValueError("minimum OBB clearance clip must remain 3.0m")
    return result


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return tuple(
        str(row[key]) for key in ("log_token", "scene_token", "decision_token")
    )


def _protocol() -> dict[str, Any]:
    return {
        "schema_version": "camp_dp_bounded_offline_safety_score_v1",
        "higher_is_better": True,
        "post_hoc_mini_descriptive_only": True,
        "learned_selector_weights_used": False,
        "closed_loop_safety_claim": False,
        "feasibility_scope": "frozen_32_dynamic_plus_5_static_observable_only",
        "hard_multipliers": [
            "obb_collision_free",
            "lane_corridor_compliant",
            "planned_red_light_cost_le_1e-12",
            "progress_ratio_ge_0.2",
        ],
        "soft_weights": {
            "clearance_proxy": 5,
            "rms_speed_compliance": 4,
            "progress_ratio": 5,
            "comfort": 2,
        },
        "clearance_clip_m": CLEARANCE_CLIP_M,
        "maximum_overspeed_mps": MAX_OVERSPEED_MPS,
        "minimum_progress_ratio": MIN_PROGRESS_RATIO,
        "red_cost_tolerance": RED_COST_TOLERANCE,
        "score_tie_tolerance": SCORE_TIE_TOLERANCE,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "ci_level": 0.95,
        "comfort_thresholds": {
            "minimum_longitudinal_acceleration_mps2": (
                MIN_LONGITUDINAL_ACCELERATION_MPS2
            ),
            "maximum_longitudinal_acceleration_mps2": (
                MAX_LONGITUDINAL_ACCELERATION_MPS2
            ),
            "maximum_absolute_lateral_acceleration_mps2": (
                MAX_ABS_LATERAL_ACCELERATION_MPS2
            ),
            "maximum_absolute_yaw_acceleration_rps2": (
                MAX_ABS_YAW_ACCELERATION_RPS2
            ),
            "maximum_absolute_yaw_rate_rps": MAX_ABS_YAW_RATE_RPS,
            "maximum_absolute_longitudinal_jerk_mps3": (
                MAX_ABS_LONGITUDINAL_JERK_MPS3
            ),
            "maximum_jerk_magnitude_mps3": MAX_JERK_MAGNITUDE_MPS3,
        },
        "causal_10k_pass_criteria": {
            "log_cluster_ci95_lower_gt_zero": True,
            "scene_cluster_ci95_lower_gt_zero": True,
            "better_gt_worse": True,
            "no_hard_component_failure_count_regression": True,
        },
    }


def _scalar(value: Any) -> bool | int | float:
    item = np.asarray(value).item()
    if isinstance(item, (bool, np.bool_)):
        return bool(item)
    if isinstance(item, (int, np.integer)):
        return int(item)
    return float(item)


def _method_summary(
    components: Mapping[str, np.ndarray], indices: np.ndarray
) -> dict[str, float]:
    rows = np.arange(indices.size)

    def values(name: str) -> np.ndarray:
        return np.asarray(components[name])[rows, indices]

    return {
        "mean_bounded_offline_safety_score": float(
            np.mean(values("bounded_offline_safety_score"))
        ),
        "collision_free_rate": float(np.mean(values("collision_free"))),
        "lane_compliance_rate": float(np.mean(values("lane_compliant"))),
        "red_light_compliance_rate": float(
            np.mean(values("red_light_compliant"))
        ),
        "making_progress_rate": float(np.mean(values("making_progress"))),
        "physical_feasibility_rate": float(
            np.mean(values("physical_feasible"))
        ),
        "comfort_pass_rate": float(np.mean(values("comfort_score"))),
        "mean_minimum_obb_clearance_m": float(
            np.mean(values("minimum_obb_clearance_m"))
        ),
        "mean_speed_score": float(np.mean(values("speed_score"))),
        "mean_progress_score": float(np.mean(values("progress_score"))),
        "mean_red_stopping_margin_cost": float(
            np.mean(values("red_stopping_margin_cost"))
        ),
    }


def paired_score_cluster_bootstrap(
    deltas: np.ndarray,
    *,
    log_ids: np.ndarray,
    scene_ids: np.ndarray,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict[str, list[float]]]:
    values = np.asarray(deltas, dtype=np.float64).reshape(-1)
    logs = np.asarray(log_ids).reshape(-1)
    scenes = np.asarray(scene_ids).reshape(-1)
    if (
        values.size == 0
        or not np.isfinite(values).all()
        or logs.size != values.size
        or scenes.size != values.size
    ):
        raise ValueError("score deltas and cluster ids must be finite and aligned")
    log_seed, scene_seed = np.random.SeedSequence(seed).spawn(2)
    arrays = {"bounded_offline_safety_score": values}
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


def _compute_evaluation(args: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paired_summary = _verify_artifact_root(
        args.paired_eval_root, args.expected_paired_eval_root_sha256
    )
    if not (
        paired_summary.get("status") == "passed"
        and paired_summary.get("holdout_records") == EXPECTED_HOLDOUT_COUNT
        and paired_summary.get("raw_holdout_labels_persisted") is False
        and paired_summary.get("baseline_semantics") == BASELINE_SEMANTICS
        and paired_summary.get("native_ranked_top1") is False
        and paired_summary.get("closed_loop_safety_claim") is False
    ):
        raise ValueError("paired-evaluation source contract mismatch")
    holdout = load_materialized_split(
        args.canonical_root,
        args.candidate_root,
        "holdout",
        labels_required=False,
    )
    if holdout.labels is not None or len(holdout.rows) != EXPECTED_HOLDOUT_COUNT:
        raise ValueError("holdout must remain label-free with exact record count")
    paired_rows = [
        json.loads(line)
        for line in (args.paired_eval_root / "records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    paired_by_identity = {_identity(row): row for row in paired_rows}
    if len(paired_rows) != EXPECTED_HOLDOUT_COUNT or len(paired_by_identity) != len(
        paired_rows
    ):
        raise ValueError("paired-evaluation identities must be unique and complete")
    expected_identities = {_identity(row) for row in holdout.rows}
    if set(paired_by_identity) != expected_identities:
        raise ValueError("paired-evaluation identities do not match canonical holdout")

    inputs = load_candidate_component_inputs(args.canonical_root, holdout.rows)
    component_rows: list[dict[str, np.ndarray]] = []
    for index in range(EXPECTED_HOLDOUT_COUNT):
        component_rows.append(
            candidate_safety_components(
                atom_matrix=holdout.atoms[index],
                candidates=holdout.candidates[index],
                lane_feasible_mask=inputs["lane_feasible_mask"][index],
                obb_collision_free_mask=inputs["obb_collision_free_mask"][index],
                physical_feasible_mask=inputs["physical_feasible_mask"][index],
                route_progress=inputs["route_progress"][index],
                progress_reference=float(inputs["progress_reference"][index]),
                minimum_obb_clearance=inputs["minimum_obb_clearance"][index],
                planned_red_light_cost=inputs["planned_red_light_cost"][index],
            )
        )
    components = {
        name: np.stack([row[name] for row in component_rows])
        for name in component_rows[0]
    }
    selected = np.asarray(
        [paired_by_identity[_identity(row)]["selected_index"] for row in holdout.rows],
        dtype=np.int64,
    )
    if np.any((selected < 0) | (selected >= holdout.atoms.shape[1])):
        raise ValueError("selected indices are outside fixed K")
    if any(
        int(paired_by_identity[_identity(row)]["baseline_index"]) != BASELINE_INDEX
        for row in holdout.rows
    ):
        raise ValueError("baseline index must remain candidate 0")
    baseline = np.full(EXPECTED_HOLDOUT_COUNT, BASELINE_INDEX, dtype=np.int64)
    row_numbers = np.arange(EXPECTED_HOLDOUT_COUNT)
    camp_scores = components["bounded_offline_safety_score"][row_numbers, selected]
    baseline_scores = components["bounded_offline_safety_score"][
        row_numbers, baseline
    ]
    deltas = camp_scores - baseline_scores
    ci95 = paired_score_cluster_bootstrap(
        deltas,
        log_ids=np.asarray([row["log_token"] for row in holdout.rows]),
        scene_ids=np.asarray([row["scene_token"] for row in holdout.rows]),
        replicates=BOOTSTRAP_REPLICATES,
        seed=BOOTSTRAP_SEED,
    )
    records = []
    for index, row in enumerate(holdout.rows):
        camp_index = int(selected[index])
        record = {
            "record_index": index,
            "split": "holdout",
            "log_token": row["log_token"],
            "scene_token": row["scene_token"],
            "decision_token": row["decision_token"],
            "selected_index": camp_index,
            "baseline_index": BASELINE_INDEX,
            "camp": {
                name: _scalar(values[index, camp_index])
                for name, values in components.items()
            },
            "baseline": {
                name: _scalar(values[index, BASELINE_INDEX])
                for name, values in components.items()
            },
        }
        record["paired_delta_camp_minus_baseline"] = float(deltas[index])
        records.append(record)
    summary = {
        "status": "passed",
        "schema_version": "camp_dp_bounded_offline_safety_score_v1",
        "holdout_records": EXPECTED_HOLDOUT_COUNT,
        "holdout_label_reads": 0,
        "raw_holdout_labels_persisted": False,
        "camp": _method_summary(components, selected),
        "baseline": {
            "semantics": BASELINE_SEMANTICS,
            **_method_summary(components, baseline),
        },
        "paired_delta_camp_minus_baseline": {
            "mean_score": float(np.mean(deltas))
        },
        "better_tie_worse": {
            "better": int(np.sum(deltas > SCORE_TIE_TOLERANCE)),
            "tie": int(np.sum(np.abs(deltas) <= SCORE_TIE_TOLERANCE)),
            "worse": int(np.sum(deltas < -SCORE_TIE_TOLERANCE)),
        },
        "paired_ci95": ci95,
        "fixed_dp_head": FIXED_DP_HEAD,
        "baseline_semantics": BASELINE_SEMANTICS,
        "native_ranked_top1": False,
        "learned_selector_weights_used": False,
        "candidate_generation_executed": False,
        "candidate_tensor_mutation": False,
        "closed_loop_safety_claim": False,
        "mini_evidence_scope": "post_hoc_descriptive_smoke_only_no_claim",
        "candidate_root_sha256": args.expected_candidate_root_sha256,
        "canonical_root_sha256": args.expected_canonical_root_sha256,
        "paired_evaluation_root_sha256": args.expected_paired_eval_root_sha256,
    }
    return summary, records


def run_evaluate(args: Any) -> dict[str, Any]:
    output = Path(args.output_dir)
    staging = output.with_name(output.name + ".tmp")
    if output.exists() or staging.exists():
        raise FileExistsError(output if output.exists() else staging)
    _verify_sources(args)
    pointer = read_v18_status_pointer(args.current_status, args.v18_audit)
    summary, records = _compute_evaluation(args)
    protocol = _protocol()
    staging.mkdir(parents=True)
    _write_json(staging / "protocol.json", protocol)
    summary["protocol_sha256"] = _sha256(staging / "protocol.json")
    summary["controller_pointer"] = pointer
    with (staging / "records.jsonl").open("w", encoding="utf-8") as stream:
        for row in records:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    _write_json(staging / "summary.json", summary)
    _write_root_manifest(staging)
    os.replace(staging, output)
    return summary


def run_review(args: Any) -> dict[str, Any]:
    output = Path(args.output_dir)
    staging = output.with_name(output.name + ".tmp")
    if output.exists() or staging.exists():
        raise FileExistsError(output if output.exists() else staging)
    source_summary = _verify_artifact_root(
        args.safety_root, args.expected_safety_root_sha256
    )
    source_protocol_path = args.safety_root / "protocol.json"
    source_protocol = json.loads(source_protocol_path.read_text(encoding="utf-8"))
    if source_protocol != _protocol():
        raise ValueError("bounded safety protocol does not match frozen constants")
    if source_summary.get("protocol_sha256") != _sha256(source_protocol_path):
        raise ValueError("bounded safety protocol SHA256 mismatch")
    _verify_sources(args)
    recomputed_summary, recomputed_records = _compute_evaluation(args)
    source_core = {
        key: value
        for key, value in source_summary.items()
        if key not in {"controller_pointer", "protocol_sha256"}
    }
    if source_core != recomputed_summary:
        raise ValueError("bounded safety summary recomputation mismatch")
    source_records = [
        json.loads(line)
        for line in (args.safety_root / "records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if source_records != recomputed_records:
        raise ValueError("bounded safety record recomputation mismatch")
    pointer = read_v18_status_pointer(args.current_status, args.v18_audit)
    review = {
        "status": "passed",
        "schema_version": "camp_dp_bounded_offline_safety_score_v1_review",
        "source_safety_root_sha256": args.expected_safety_root_sha256,
        "source_summary_sha256": _sha256(args.safety_root / "summary.json"),
        "source_protocol_sha256": _sha256(source_protocol_path),
        "recomputed_records": len(recomputed_records),
        "holdout_label_reads": 0,
        "learned_selector_weights_used": False,
        "candidate_generation_executed": False,
        "candidate_tensor_mutation": False,
        "fixed_dp_head": FIXED_DP_HEAD,
        "closed_loop_safety_claim": False,
        "mini_evidence_scope": "post_hoc_descriptive_smoke_only_no_claim",
        "controller_pointer": pointer,
    }
    staging.mkdir(parents=True)
    _write_json(staging / "summary.json", review)
    _write_root_manifest(staging)
    os.replace(staging, output)
    return review


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate or review the v18 bounded offline safety score."
    )
    parser.add_argument("--mode", choices=("evaluate", "review"), required=True)
    parser.add_argument("--canonical_root", type=Path, required=True)
    parser.add_argument("--canonical_sha256s", type=Path, required=True)
    parser.add_argument("--expected_canonical_root_sha256", required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_candidate_root_sha256", required=True)
    parser.add_argument("--paired_eval_root", type=Path, required=True)
    parser.add_argument("--expected_paired_eval_root_sha256", required=True)
    parser.add_argument("--safety_root", type=Path)
    parser.add_argument("--expected_safety_root_sha256")
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_status", type=Path, required=True)
    parser.add_argument("--v18_audit", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.mode == "review" and (
        args.safety_root is None or args.expected_safety_root_sha256 is None
    ):
        parser.error("review mode requires safety root and root SHA256")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    report = run_evaluate(args) if args.mode == "evaluate" else run_review(args)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
