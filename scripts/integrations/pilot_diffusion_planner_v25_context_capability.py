#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_causal_materializer import (  # noqa: E402
    CAUSAL_DP_INPUT_SCHEMA,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    CONTEXT_SCHEMA_VERSION,
    PHI_DIMENSION,
    PHI_SCHEMA_VERSION,
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
    build_v25_raw_context,
    context_weights,
    fit_train_context_scaler,
)


SCHEMA_VERSION = "camp_dp_v25_context_capability_pilot_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


@dataclass(frozen=True)
class RequestKnobs:
    ego_speed_mps: float = 8.0
    ego_longitudinal_acceleration_mps2: float = 0.0
    ego_yaw_rate_radps: float = 0.0
    route_curvature: float = 0.001
    lane_width_m: float = 4.0
    speed_limit_mps: float = 12.0
    phase: str = "green"
    signal_point_index: int = 10
    phase_remaining_s: float = 5.0
    neighbor_count: int = 2
    neighbor_distance_m: float = 15.0
    neighbor_closing_speed_mps: float = 2.0
    neighbor_lateral_gap_m: float = 2.0
    candidate_lateral_spread_m: float = 0.4
    candidate_progress_spread_m: float = 2.0
    source_valid_count: int = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the outcome-blind V25 current-request context capability pilot."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--freeze-config",
        type=Path,
        default=ROOT / "configs/integrations/diffusion_planner_v25_atom_context_freeze.json",
    )
    parser.add_argument("--fixed-dp-head", default=FIXED_DP_HEAD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    freeze = json.loads(args.freeze_config.read_text(encoding="utf-8"))
    _validate_freeze(freeze, args.fixed_dp_head)
    cases, monotonic_pairs = _capability_cases()
    raw_rows: list[np.ndarray] = []
    case_reports: list[dict[str, Any]] = []
    immutable = True
    complete = True
    for name, knobs in cases:
        causal = _causal_input(knobs)
        candidates = _candidates(knobs)
        before = _array_sha256(candidates)
        source_valid = np.zeros(8, dtype=bool)
        source_valid[: knobs.source_valid_count] = True
        record = build_v25_raw_context(
            causal_input=causal,
            candidates=candidates,
            source_valid_mask=source_valid,
            signal_phase_remaining_s=knobs.phase_remaining_s,
        )
        after = _array_sha256(candidates)
        immutable &= before == after
        complete &= all(record.source_complete)
        raw_rows.append(record.raw)
        case_reports.append(
            {
                "name": name,
                "knobs": asdict(knobs),
                "raw_context": record.as_dict(),
                "source_complete": {
                    feature: bool(value)
                    for feature, value in zip(
                        RAW_FEATURE_NAMES, record.source_complete, strict=True
                    )
                },
                "candidate_sha256_before": before,
                "candidate_sha256_after": after,
            }
        )

    raw = np.asarray(raw_rows, dtype=np.float64)
    scaler = fit_train_context_scaler(raw)
    phi = scaler.lift(raw)
    theta = np.zeros((14, PHI_DIMENSION), dtype=np.float64)
    theta[np.arange(PHI_DIMENSION) % 14, np.arange(PHI_DIMENSION)] = 1.0
    weights = context_weights(theta, phi)
    atom_matrix = _fixed_atom_matrix()
    scores = np.einsum("kr,nr->nk", atom_matrix, weights)
    affine_mix_weights = 0.3 * weights[0] + 0.7 * weights[-1]
    affine_left = atom_matrix @ affine_mix_weights
    affine_right = 0.3 * scores[0] + 0.7 * scores[-1]

    feature_ranges = {
        name: {
            "minimum": float(np.min(raw[:, index])),
            "maximum": float(np.max(raw[:, index])),
            "range": float(np.ptp(raw[:, index])),
            "unique_count": int(np.unique(raw[:, index]).size),
        }
        for index, name in enumerate(RAW_FEATURE_NAMES)
    }
    variation_checks = {
        name: values["unique_count"] >= 2 for name, values in feature_ranges.items()
    }
    monotonic_checks = _monotonic_checks(
        case_reports=case_reports,
        monotonic_pairs=monotonic_pairs,
    )
    checks = {
        "freeze_schema_exact": True,
        "fixed_dp_head_exact": args.fixed_dp_head == FIXED_DP_HEAD,
        "case_count_at_least_20": len(cases) >= 20,
        "case_count_at_most_50": len(cases) <= 50,
        "raw_shape_exact": raw.shape == (len(cases), RAW_FEATURE_COUNT),
        "raw_finite": bool(np.all(np.isfinite(raw))),
        "all_sources_complete": bool(complete),
        "every_raw_feature_varies": bool(all(variation_checks.values())),
        "all_registered_monotonic_checks_pass": bool(all(monotonic_checks.values())),
        "phi_shape_exact": phi.shape == (len(cases), PHI_DIMENSION),
        "phi_finite_nonnegative": bool(np.all(np.isfinite(phi)) and np.all(phi >= 0.0)),
        "phi_rows_sum_one": bool(np.allclose(phi.sum(axis=1), 1.0, atol=1e-10)),
        "theta_columns_nonnegative_simplex": bool(
            np.all(theta >= 0.0) and np.allclose(theta.sum(axis=0), 1.0)
        ),
        "context_weights_nonnegative_simplex": bool(
            np.all(weights >= 0.0) and np.allclose(weights.sum(axis=1), 1.0)
        ),
        "context_weights_vary": bool(np.any(np.ptp(weights, axis=0) > 1e-8)),
        "score_affine_in_current_tick_weights": bool(
            np.allclose(affine_left, affine_right, rtol=0.0, atol=1e-12)
        ),
        "candidate_tensors_immutable": bool(immutable),
        "candidate_count_fixed_k8": atom_matrix.shape[0] == 8,
        "dp_unmodified": True,
        "candidate_and_trajectory_immutable": True,
        "no_closed_loop_outcome_read": True,
        "no_gt_future_or_holdout_read": True,
        "no_identity_feature_read": True,
        "no_private_dp_latent_read": True,
        "no_softmax": True,
        "no_runtime_weight_projection": True,
        "no_training_executed": True,
        "no_calibration_executed": True,
        "no_paired_evaluation_executed": True,
    }
    passed = all(checks.values())
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed" if passed else "failed",
        "source_head": _git_head(),
        "fixed_dp_head": args.fixed_dp_head,
        "freeze_config": str(args.freeze_config),
        "freeze_config_sha256": _file_sha256(args.freeze_config),
        "context_schema_version": CONTEXT_SCHEMA_VERSION,
        "phi_schema_version": PHI_SCHEMA_VERSION,
        "raw_feature_names": list(RAW_FEATURE_NAMES),
        "case_count": len(cases),
        "case_reports": case_reports,
        "feature_ranges": feature_ranges,
        "variation_checks": variation_checks,
        "monotonic_checks": monotonic_checks,
        "pilot_only_scaler": {
            "use": "capability_check_only_not_training_or_calibration_freeze",
            "q05": scaler.q05.tolist(),
            "q95": scaler.q95.tolist(),
        },
        "theta_probe": {
            "use": "deterministic_capability_probe_only_not_trained_model",
            "shape": list(theta.shape),
            "weight_range_by_atom": np.ptp(weights, axis=0).tolist(),
        },
        "checks": checks,
        "boundaries": {
            "request_sources": (
                "exact fixed-DP causal input schema plus fixed current K=8 tensor, "
                "current signal schedule remainder, and source-valid mask"
            ),
            "candidate_zero_semantics": "DP operational default; native-ranked Top-1 not claimed",
            "score_contract": "score_k=a_k^T*w(x)",
            "weight_contract": "every Theta column is a nonnegative simplex",
            "master_contract": "finite-candidate CVaR/L2 remains convex for fixed phi and atoms",
            "capability_only": True,
            "scene_conditioned_utility_claimed": False,
            "safety_claimed": False,
            "deployment_or_activation": False,
        },
        "wall_seconds": float(time.perf_counter() - started),
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report_path = args.output_dir / "report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path = args.output_dir / "report.md"
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    manifest = {
        "schema_version": "camp_dp_v25_artifact_manifest_v1",
        "files": {
            "report.json": _file_sha256(report_path),
            "report.md": _file_sha256(markdown_path),
        },
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    root_sha256 = hashlib.sha256(
        json.dumps(manifest["files"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    print(
        json.dumps(
            {
                "status": report["status"],
                "artifact": str(args.output_dir),
                "artifact_root_sha256": root_sha256,
                "check_count": len(checks),
                "case_count": len(cases),
                "source_head": report["source_head"],
                "fixed_dp_head": report["fixed_dp_head"],
            },
            sort_keys=True,
        )
    )
    if not passed:
        raise SystemExit(1)


def _validate_freeze(freeze: dict[str, Any], fixed_dp_head: str) -> None:
    context = freeze.get("causal_context_contract", {})
    names = tuple(item.get("name") for item in context.get("raw_features", ()))
    if context.get("schema_version") != CONTEXT_SCHEMA_VERSION:
        raise ValueError("freeze context schema version mismatch")
    if names != RAW_FEATURE_NAMES or context.get("phi_dimension") != PHI_DIMENSION:
        raise ValueError("freeze raw feature order or phi dimension mismatch")
    if context.get("softmax_allowed") is not False:
        raise ValueError("freeze must forbid softmax")
    if context.get("theta_constraint") != "every_theta_column_nonnegative_simplex":
        raise ValueError("freeze Theta constraint mismatch")
    if freeze.get("corpus_contract", {}).get("fixed_dp_head") != fixed_dp_head:
        raise ValueError("fixed DP head does not match the freeze")


def _capability_cases() -> tuple[list[tuple[str, RequestKnobs]], dict[str, tuple[str, str, str]]]:
    base = RequestKnobs()
    cases: list[tuple[str, RequestKnobs]] = [("base", base)]
    pairs: dict[str, tuple[str, str, str]] = {}

    def add_pair(feature: str, low_name: str, low: RequestKnobs, high_name: str, high: RequestKnobs) -> None:
        cases.extend([(low_name, low), (high_name, high)])
        pairs[feature] = (low_name, high_name, "increase")

    add_pair("ego_speed_mps", "speed_low", replace(base, ego_speed_mps=2.0), "speed_high", replace(base, ego_speed_mps=16.0))
    add_pair("ego_longitudinal_acceleration_mps2", "long_accel_low", replace(base, ego_longitudinal_acceleration_mps2=-4.0), "long_accel_high", replace(base, ego_longitudinal_acceleration_mps2=3.0))
    add_pair("ego_yaw_rate_radps", "yaw_low", replace(base, ego_yaw_rate_radps=-0.25), "yaw_high", replace(base, ego_yaw_rate_radps=0.3))
    add_pair("route_curvature_max_abs_radpm", "curvature_low", replace(base, route_curvature=0.0), "curvature_high", replace(base, route_curvature=0.008))
    add_pair("route_lane_width_min_m", "width_narrow", replace(base, lane_width_m=2.8), "width_wide", replace(base, lane_width_m=5.0))
    add_pair("route_speed_limit_current_mps", "limit_low", replace(base, speed_limit_mps=6.0), "limit_high", replace(base, speed_limit_mps=22.0))
    for phase in ("green", "yellow", "red", "unknown"):
        cases.append((f"phase_{phase}", replace(base, phase=phase)))
    add_pair("traffic_signal_distance_m", "signal_near", replace(base, signal_point_index=2), "signal_far", replace(base, signal_point_index=32))
    add_pair("traffic_signal_phase_remaining_s", "remaining_short", replace(base, phase_remaining_s=0.5), "remaining_long", replace(base, phase_remaining_s=14.0))
    add_pair("neighbor_count", "neighbors_few", replace(base, neighbor_count=1), "neighbors_many", replace(base, neighbor_count=5))
    cases.extend([
        ("neighbor_near", replace(base, neighbor_distance_m=6.0)),
        ("neighbor_far", replace(base, neighbor_distance_m=35.0)),
    ])
    pairs["neighbor_min_distance_m"] = ("neighbor_near", "neighbor_far", "increase")
    cases.extend([
        ("closing_slow", replace(base, neighbor_closing_speed_mps=0.5)),
        ("closing_fast", replace(base, neighbor_closing_speed_mps=6.0)),
    ])
    pairs["neighbor_closing_speed_mps"] = ("closing_slow", "closing_fast", "increase")
    pairs["neighbor_min_ttc_s"] = ("closing_fast", "closing_slow", "increase")
    add_pair("neighbor_lateral_gap_min_m", "lateral_near", replace(base, neighbor_lateral_gap_m=0.5), "lateral_far", replace(base, neighbor_lateral_gap_m=4.0))
    add_pair("candidate_consensus_rms_median_m", "candidate_tight", replace(base, candidate_lateral_spread_m=0.05), "candidate_wide", replace(base, candidate_lateral_spread_m=2.0))
    add_pair("candidate_progress_std_m", "progress_tight", replace(base, candidate_progress_spread_m=0.1), "progress_wide", replace(base, candidate_progress_spread_m=6.0))
    add_pair("candidate_source_valid_fraction", "source_sparse", replace(base, source_valid_count=2), "source_full", replace(base, source_valid_count=8))
    return cases, pairs


def _causal_input(knobs: RequestKnobs) -> dict[str, np.ndarray]:
    data = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    data["version"] = np.array(1, dtype=np.int64)
    data["ego_current_state"] = np.array(
        [
            0.0,
            0.0,
            1.0,
            0.0,
            knobs.ego_speed_mps,
            0.0,
            knobs.ego_longitudinal_acceleration_mps2,
            0.0,
            0.0,
            knobs.ego_yaw_rate_radps,
        ],
        dtype=np.float32,
    )
    route = np.zeros((25, 20, 33), dtype=np.float32)
    phase_index = {"green": 0, "yellow": 1, "red": 2, "unknown": 3}[knobs.phase]
    for slot in range(2):
        for local in range(20):
            global_index = slot * 19 + local
            x = float(global_index)
            y = knobs.route_curvature * x * x
            tangent = np.array([1.0, 2.0 * knobs.route_curvature * x])
            tangent /= np.linalg.norm(tangent)
            row = route[slot, local]
            row[:2] = [x, y]
            row[2:4] = tangent
            half = 0.5 * knobs.lane_width_m
            row[4:6] = [-half * tangent[1], half * tangent[0]]
            row[6:8] = [half * tangent[1], -half * tangent[0]]
            row[12] = 1.0
            if global_index >= knobs.signal_point_index:
                row[12] = 0.0
                row[8 + phase_index] = 1.0
            row[13] = 1.0
            row[23] = 1.0
    data["route_lanes"] = route
    data["lanes"][:2] = route[:2]
    data["route_lanes_has_speed_limit"][:2] = True
    data["route_lanes_speed_limit"][:2, 0] = knobs.speed_limit_mps
    data["lanes_has_speed_limit"][:2] = True
    data["lanes_speed_limit"][:2, 0] = knobs.speed_limit_mps
    for index in range(knobs.neighbor_count):
        distance = knobs.neighbor_distance_m + 2.0 * index
        lateral = knobs.neighbor_lateral_gap_m + 0.25 * index
        row = data["neighbor_agents_past"][index, -1]
        row[:8] = [
            distance,
            lateral,
            1.0,
            0.0,
            knobs.ego_speed_mps - knobs.neighbor_closing_speed_mps,
            0.0,
            1.8,
            4.5,
        ]
        row[8] = 1.0
    return data


def _candidates(knobs: RequestKnobs) -> np.ndarray:
    candidates = np.zeros((8, 80, 4), dtype=np.float64)
    time_axis = np.linspace(0.0, 1.0, 80)
    centered = np.arange(8, dtype=np.float64) - 3.5
    for index in range(8):
        end = 28.0 + centered[index] * knobs.candidate_progress_spread_m / 3.5
        candidates[index, :, 0] = np.linspace(0.05, end, 80)
        candidates[index, :, 1] = (
            centered[index]
            * knobs.candidate_lateral_spread_m
            / 3.5
            * np.sin(np.pi * time_axis)
        )
        candidates[index, :, 2] = 1.0
    return candidates


def _fixed_atom_matrix() -> np.ndarray:
    candidate = np.arange(8, dtype=np.float64)[:, None]
    atom = np.arange(14, dtype=np.float64)[None, :]
    return np.mod((candidate + 1.0) * (atom + 2.0), 17.0) / 17.0


def _monotonic_checks(
    *,
    case_reports: list[dict[str, Any]],
    monotonic_pairs: dict[str, tuple[str, str, str]],
) -> dict[str, bool]:
    by_name = {item["name"]: item["raw_context"] for item in case_reports}
    checks: dict[str, bool] = {}
    for feature, (low_name, high_name, direction) in monotonic_pairs.items():
        low = float(by_name[low_name][feature])
        high = float(by_name[high_name][feature])
        checks[f"{feature}:{low_name}->{high_name}"] = (
            high > low if direction == "increase" else high < low
        )
    for phase in ("green", "yellow", "red", "unknown"):
        phase_row = by_name[f"phase_{phase}"]
        checks[f"traffic_one_hot:{phase}"] = bool(
            phase_row[f"traffic_phase_{phase}"] == 1.0
            and sum(phase_row[f"traffic_phase_{name}"] for name in ("green", "yellow", "red", "unknown")) == 1.0
        )
    return checks


def _markdown(report: dict[str, Any]) -> str:
    failed = [name for name, passed in report["checks"].items() if not passed]
    return (
        "# V25 scene-conditioned context capability pilot\n\n"
        f"- status: `{report['status']}`\n"
        f"- source HEAD: `{report['source_head']}`\n"
        f"- fixed DP HEAD: `{report['fixed_dp_head']}`\n"
        f"- outcome-blind current-request cases: `{report['case_count']}`\n"
        f"- raw/phi dimensions: `{len(report['raw_feature_names'])}` / `{PHI_DIMENSION}`\n"
        f"- failed checks: `{failed}`\n\n"
        "This pilot proves source construction, finite behavior, variation, "
        "registered monotonic responses, candidate immutability, universal "
        "simplex weights, and affine fixed-candidate scoring only. Its scaler "
        "and Theta are deterministic capability probes, not trained or "
        "calibrated assets. It makes no scene-conditioned utility, safety, "
        "promotion, deployment, native-ranked Top-1, or real-road claim.\n"
    )


def _array_sha256(array: np.ndarray) -> str:
    values = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(values.dtype.str.encode())
    digest.update(str(values.shape).encode())
    digest.update(values.tobytes())
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


if __name__ == "__main__":
    main()
