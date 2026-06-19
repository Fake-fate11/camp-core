#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
    parse_selection_log_metadata,
)


FORMAL_SEEDS = {11, 12, 13}


@dataclass(frozen=True)
class GateThresholds:
    candidate0_preservation_max_abs_xy_m: float = 1e-6
    min_endpoint_pairwise_mean_m: float = 0.50
    min_endpoint_pairwise_gain_vs_baseline_m: float = 0.25
    min_mode_count_mean: float = 2.0
    non_top1_dense_lane_change_support_rate_min: float = 0.25
    progress_loss_budget_m: float = 0.10
    target_speed_loss_budget_mps: float = 0.20
    jerk_worse_budget_mps3: float = 0.05
    lateral_worse_budget_mps2: float = 0.05
    latency_p95_limit_ms: float = 100.0
    lateral_mode_threshold_m: float = 0.25
    longitudinal_mode_threshold_m: float = 0.25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare unguided and default-off mode-seeking DP candidate logs "
            "for candidate0 preservation, endpoint/mode diversity, non-Top1 "
            "dense lane-change support, and latency. This is a diagnostic only."
        )
    )
    parser.add_argument("--baseline_root", type=Path, action="append", default=[])
    parser.add_argument("--baseline_selection_log", type=Path, action="append", default=[])
    parser.add_argument("--candidate_root", type=Path, action="append", default=[])
    parser.add_argument("--candidate_selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--candidate0_preservation_max_abs_xy_m", type=float, default=1e-6)
    parser.add_argument("--min_endpoint_pairwise_mean_m", type=float, default=0.50)
    parser.add_argument("--min_endpoint_pairwise_gain_vs_baseline_m", type=float, default=0.25)
    parser.add_argument("--min_mode_count_mean", type=float, default=2.0)
    parser.add_argument("--non_top1_dense_lane_change_support_rate_min", type=float, default=0.25)
    parser.add_argument("--progress_loss_budget_m", type=float, default=0.10)
    parser.add_argument("--target_speed_loss_budget_mps", type=float, default=0.20)
    parser.add_argument("--jerk_worse_budget_mps3", type=float, default=0.05)
    parser.add_argument("--lateral_worse_budget_mps2", type=float, default=0.05)
    parser.add_argument("--latency_p95_limit_ms", type=float, default=100.0)
    parser.add_argument("--lateral_mode_threshold_m", type=float, default=0.25)
    parser.add_argument("--longitudinal_mode_threshold_m", type=float, default=0.25)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = GateThresholds(
        candidate0_preservation_max_abs_xy_m=args.candidate0_preservation_max_abs_xy_m,
        min_endpoint_pairwise_mean_m=args.min_endpoint_pairwise_mean_m,
        min_endpoint_pairwise_gain_vs_baseline_m=(
            args.min_endpoint_pairwise_gain_vs_baseline_m
        ),
        min_mode_count_mean=args.min_mode_count_mean,
        non_top1_dense_lane_change_support_rate_min=(
            args.non_top1_dense_lane_change_support_rate_min
        ),
        progress_loss_budget_m=args.progress_loss_budget_m,
        target_speed_loss_budget_mps=args.target_speed_loss_budget_mps,
        jerk_worse_budget_mps3=args.jerk_worse_budget_mps3,
        lateral_worse_budget_mps2=args.lateral_worse_budget_mps2,
        latency_p95_limit_ms=args.latency_p95_limit_ms,
        lateral_mode_threshold_m=args.lateral_mode_threshold_m,
        longitudinal_mode_threshold_m=args.longitudinal_mode_threshold_m,
    )
    report = analyze(
        baseline_paths=[*args.baseline_root, *args.baseline_selection_log],
        candidate_paths=[*args.candidate_root, *args.candidate_selection_log],
        thresholds=thresholds,
        label=args.label,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(
    *,
    baseline_paths: list[Path],
    candidate_paths: list[Path],
    thresholds: GateThresholds = GateThresholds(),
    label: str | None = None,
) -> dict[str, Any]:
    _validate_thresholds(thresholds)
    baseline_logs = iter_selection_log_paths(baseline_paths)
    candidate_logs = iter_selection_log_paths(candidate_paths)
    if not baseline_logs:
        raise ValueError("No baseline selection logs were found.")
    if not candidate_logs:
        raise ValueError("No candidate selection logs were found.")

    baseline_records = _load_records(baseline_logs, expected_guidance_enabled=False)
    candidate_records = _load_records(candidate_logs, expected_guidance_enabled=True)
    paired = _paired_records(baseline_records, candidate_records)
    if not paired:
        raise ValueError("No paired baseline/candidate records were found.")

    preservation = [_candidate0_preservation(row) for row in paired]
    baseline_spatial = [_spatial_metrics(row["baseline"]["prefix"], thresholds) for row in paired]
    candidate_spatial = [_spatial_metrics(row["candidate"]["prefix"], thresholds) for row in paired]
    support = _support_report(candidate_records, thresholds)
    latency = _latency_report(candidate_records, thresholds)
    formal = _formal_seed_report([*baseline_records, *candidate_records])
    contract = {
        "baseline": _contract_summary(baseline_records),
        "candidate": _contract_summary(candidate_records),
    }
    decision = _decision(
        preservation=preservation,
        baseline_spatial=baseline_spatial,
        candidate_spatial=candidate_spatial,
        support=support,
        latency=latency,
        formal=formal,
        contract=contract,
        thresholds=thresholds,
    )

    return {
        "analysis": {
            "name": "dp_camp_mode_seeking_candidate_availability_v1",
            "label": label,
            "role": (
                "outcome-free comparison of unguided and default-off "
                "mode-seeking candidate logs before any closed-loop replay"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "Candidate generation changes only the current-tick finite "
                "candidate set under fixed DP weights. CAMP runtime atoms "
                "remain current-tick finite-candidate quantities, scores remain "
                "affine a_k^T w, and the simplex/CVaR/L2 robust master remains "
                "convex. This diagnostic is not classical Benders decomposition."
            ),
        },
        "thresholds": thresholds.__dict__,
        "records": {
            "baseline_logs": len(baseline_logs),
            "candidate_logs": len(candidate_logs),
            "paired_records": len(paired),
            "candidate_records": len(candidate_records),
            "candidate_nonfallback_records": sum(
                int(record["feasible"].any()) for record in candidate_records
            ),
        },
        "guidance_contract": {
            "baseline": contract["baseline"],
            "candidate": contract["candidate"],
        },
        "candidate0_preservation": _summary(
            [row["max_abs_xy_m"] for row in preservation]
        ),
        "spatial_diversity": {
            "baseline": _spatial_summary(baseline_spatial),
            "candidate": _spatial_summary(candidate_spatial),
            "gain": _spatial_gain_summary(baseline_spatial, candidate_spatial),
        },
        "dense_lane_change_support": support,
        "latency": latency,
        "formal_seed_policy": formal,
        "final_decision": decision,
    }


def _load_records(
    log_paths: list[Path],
    *,
    expected_guidance_enabled: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for log_path in log_paths:
        metadata = parse_selection_log_metadata(log_path)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        summary = _read_json(log_path.with_name("camp_validation_summary.json"))
        for record_index, raw in enumerate(payload):
            row = _load_record(raw, f"{log_path} record {record_index}")
            row["log_path"] = str(log_path)
            row["record_index"] = int(record_index)
            row["pair_key"] = _pair_key(metadata, summary, record_index)
            row["route_name"] = _route_name(metadata, summary)
            row["seed"] = _seed(metadata, summary)
            row["max_npcs"] = _max_npcs(metadata, summary)
            row["latency_ms"] = _latency_ms(raw)
            if row["contract"]["guidance_enabled"] != expected_guidance_enabled:
                expected = str(expected_guidance_enabled)
                actual = str(row["contract"]["guidance_enabled"])
                raise ValueError(
                    f"{log_path} record {record_index} guidance_enabled={actual}; "
                    f"expected {expected}."
                )
            rows.append(row)
    return rows


def _load_record(raw: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index", 0))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    prefix = _prefix(raw, candidate_count, label)
    contract = _candidate_generation_contract(raw, label)
    return {
        "candidate_count": candidate_count,
        "selected_index": selected,
        "feasible": _bool_vector(raw.get("feasible_mask"), candidate_count, f"{label} feasible_mask"),
        "prefix": prefix,
        "progress": _vector(
            raw.get("candidate_route_progress", raw.get("candidate_step_reach")),
            candidate_count,
            f"{label} candidate_route_progress",
            default=0.0,
        ),
        "target_speed": _vector(
            raw.get("candidate_perfect_tracker_target_speed_mps"),
            candidate_count,
            f"{label} candidate_perfect_tracker_target_speed_mps",
            default=0.0,
        ),
        "jerk": _vector(
            raw.get("candidate_perfect_tracker_jerk_magnitude_mps3"),
            candidate_count,
            f"{label} candidate_perfect_tracker_jerk_magnitude_mps3",
            default=0.0,
        ),
        "lateral": _vector(
            raw.get("candidate_perfect_tracker_lateral_acceleration_magnitude_mps2"),
            candidate_count,
            f"{label} candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
            default=0.0,
        ),
        "contract": contract,
    }


def _candidate_generation_contract(raw: dict[str, Any], label: str) -> dict[str, Any]:
    contract = raw.get("candidate_generation_contract")
    if contract is None:
        metadata_json = raw.get("metadata_json")
        if metadata_json is not None:
            metadata = json.loads(str(metadata_json))
            contract = metadata.get("candidate_generation_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{label} is missing candidate_generation_contract.")
    return {
        "guidance_enabled": bool(contract.get("guidance_enabled")),
        "guidance_policy": str(contract.get("guidance_policy")),
        "changes_diffusion_planner_weights": bool(
            contract.get("changes_diffusion_planner_weights")
        ),
        "changes_camp_score": bool(contract.get("changes_camp_score")),
        "num_candidates": int(contract.get("num_candidates", 0)),
        "noise_strategy": contract.get("noise_strategy"),
        "candidate0_guidance_policy": contract.get("candidate0_guidance_policy"),
        "candidate0_preservation_structural": bool(
            contract.get("candidate0_preservation_structural")
        ),
        "guidance": contract.get("guidance") or {},
    }


def _paired_records(
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_by_key = {row["pair_key"]: row for row in baseline}
    candidate_by_key = {row["pair_key"]: row for row in candidate}
    return [
        {
            "key": key,
            "baseline": baseline_by_key[key],
            "candidate": candidate_by_key[key],
        }
        for key in sorted(set(baseline_by_key) & set(candidate_by_key))
    ]


def _candidate0_preservation(row: dict[str, Any]) -> dict[str, float]:
    baseline = row["baseline"]["prefix"][0, :, :2]
    candidate = row["candidate"]["prefix"][0, :, :2]
    if baseline.shape != candidate.shape:
        raise ValueError(f"{row['key']} candidate0 prefix shape mismatch.")
    return {"max_abs_xy_m": float(np.max(np.abs(candidate - baseline)))}


def _spatial_metrics(prefix: np.ndarray, thresholds: GateThresholds) -> dict[str, float]:
    endpoints = prefix[:, -1, :2]
    selected = 0
    pairwise = _pairwise_distances(endpoints)
    axis = _selected_axis(prefix, selected)
    lateral_axis = np.asarray([-axis[1], axis[0]], dtype=np.float64)
    deltas = endpoints - endpoints[selected]
    longitudinal = deltas @ axis
    lateral = deltas @ lateral_axis
    modes = {
        (
            _mode_bin(float(lateral[index]), thresholds.lateral_mode_threshold_m),
            _mode_bin(
                float(longitudinal[index]),
                thresholds.longitudinal_mode_threshold_m,
            ),
        )
        for index in range(prefix.shape[0])
    }
    return {
        "endpoint_pairwise_mean_m": float(np.mean(pairwise)) if pairwise.size else 0.0,
        "endpoint_pairwise_max_m": float(np.max(pairwise)) if pairwise.size else 0.0,
        "mode_count": float(len(modes)),
    }


def _support_report(
    records: list[dict[str, Any]],
    thresholds: GateThresholds,
) -> dict[str, Any]:
    targets = [
        record
        for record in records
        if _is_dense_lane_change(record)
        and record["feasible"].any()
        and int(record["selected_index"]) != 0
    ]
    supported = [record for record in targets if _has_non_top1_support(record, thresholds)]
    rate = len(supported) / len(targets) if targets else 0.0
    return {
        "target_records": len(targets),
        "supported_records": len(supported),
        "support_rate": rate,
        "passes_threshold": (
            bool(targets)
            and rate >= thresholds.non_top1_dense_lane_change_support_rate_min
        ),
    }


def _has_non_top1_support(record: dict[str, Any], thresholds: GateThresholds) -> bool:
    selected = int(record["selected_index"])
    feasible = record["feasible"]
    for index in range(record["candidate_count"]):
        if index == 0 or index == selected or not bool(feasible[index]):
            continue
        if float(record["progress"][index]) < float(record["progress"][selected]) - thresholds.progress_loss_budget_m:
            continue
        if float(record["target_speed"][index]) < float(record["target_speed"][selected]) - thresholds.target_speed_loss_budget_mps:
            continue
        if float(record["jerk"][index]) > float(record["jerk"][selected]) + thresholds.jerk_worse_budget_mps3:
            continue
        if float(record["lateral"][index]) > float(record["lateral"][selected]) + thresholds.lateral_worse_budget_mps2:
            continue
        return True
    return False


def _latency_report(records: list[dict[str, Any]], thresholds: GateThresholds) -> dict[str, Any]:
    values = [record["latency_ms"] for record in records if record["latency_ms"] is not None]
    if not values:
        return {
            "records": 0,
            "p95_ms": None,
            "passes_p95_limit": False,
            "reason": "latency_missing",
        }
    p95 = float(np.percentile(np.asarray(values, dtype=np.float64), 95))
    return {
        "records": len(values),
        "p95_ms": p95,
        "passes_p95_limit": p95 < thresholds.latency_p95_limit_ms,
        "reason": "ok",
    }


def _formal_seed_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    formal = [
        record
        for record in records
        if record["seed"] is not None and int(record["seed"]) in FORMAL_SEEDS
    ]
    return {
        "formal_seed_records": len(formal),
        "formal_seeds_present": bool(formal),
    }


def _decision(
    *,
    preservation: list[dict[str, float]],
    baseline_spatial: list[dict[str, float]],
    candidate_spatial: list[dict[str, float]],
    support: dict[str, Any],
    latency: dict[str, Any],
    formal: dict[str, Any],
    contract: dict[str, dict[str, Any]],
    thresholds: GateThresholds,
) -> dict[str, Any]:
    max_candidate0 = max(row["max_abs_xy_m"] for row in preservation)
    baseline_endpoint = _mean_metric(baseline_spatial, "endpoint_pairwise_mean_m")
    candidate_endpoint = _mean_metric(candidate_spatial, "endpoint_pairwise_mean_m")
    endpoint_gain = candidate_endpoint - baseline_endpoint
    candidate_mode = _mean_metric(candidate_spatial, "mode_count")
    gates = {
        "candidate0_preserved": (
            max_candidate0 <= thresholds.candidate0_preservation_max_abs_xy_m
        ),
        "endpoint_pairwise_mean_pass": (
            candidate_endpoint >= thresholds.min_endpoint_pairwise_mean_m
        ),
        "endpoint_gain_pass": (
            endpoint_gain >= thresholds.min_endpoint_pairwise_gain_vs_baseline_m
        ),
        "mode_count_pass": candidate_mode >= thresholds.min_mode_count_mean,
        "non_top1_dense_lane_change_support_pass": bool(support["passes_threshold"]),
        "latency_p95_pass": bool(latency["passes_p95_limit"]),
        "formal_seeds_absent": not bool(formal["formal_seeds_present"]),
        "fixed_dp_weights": contract["candidate"][
            "changes_diffusion_planner_weights_values"
        ]
        == [False],
        "camp_score_unchanged": contract["candidate"][
            "changes_camp_score_values"
        ]
        == [False],
        "candidate0_structural_preservation_contract": contract["candidate"][
            "candidate0_preservation_structural_values"
        ]
        == [True],
    }
    passed = all(gates.values())
    return {
        "status": (
            "mode_seeking_candidate_availability_passed"
            if passed
            else "mode_seeking_candidate_availability_rejected"
        ),
        "gates": gates,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": (
            "run_outcome_labeled_offline_screen_before_any_closed_loop_smoke"
            if passed
            else "reject_or_redesign_mode_seeking_candidate_generation"
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Mode-Seeking Candidate Availability Diagnostic",
        "",
        "This is an outcome-free diagnostic over existing selection logs. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Closed-loop smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "Gates:",
    ]
    for key, value in decision["gates"].items():
        lines.append(f"- `{key}`: `{value}`")
    spatial = report["spatial_diversity"]
    support = report["dense_lane_change_support"]
    latency = report["latency"]
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            f"- Candidate0 max abs xy: `{report['candidate0_preservation']['max']}`",
            f"- Baseline endpoint pairwise mean: `{spatial['baseline']['endpoint_pairwise_mean_m']['mean']}`",
            f"- Candidate endpoint pairwise mean: `{spatial['candidate']['endpoint_pairwise_mean_m']['mean']}`",
            f"- Endpoint pairwise mean gain: `{spatial['gain']['endpoint_pairwise_mean_m']}`",
            f"- Candidate mode-count mean: `{spatial['candidate']['mode_count']['mean']}`",
            f"- Dense lane-change support rate: `{support['support_rate']}`",
            f"- Candidate latency p95 ms: `{latency['p95_ms']}`",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            f"Next step: {decision['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _route_name(metadata: Any, summary: dict[str, Any]) -> str:
    benchmark = summary.get("benchmark") if isinstance(summary.get("benchmark"), dict) else {}
    route = benchmark.get("route")
    if route is not None:
        return Path(str(route)).stem
    return str(metadata.route)


def _seed(metadata: Any, summary: dict[str, Any]) -> int | None:
    benchmark = summary.get("benchmark") if isinstance(summary.get("benchmark"), dict) else {}
    seed = benchmark.get("seed", metadata.seed)
    return None if seed is None else int(seed)


def _max_npcs(metadata: Any, summary: dict[str, Any]) -> int | None:
    benchmark = summary.get("benchmark") if isinstance(summary.get("benchmark"), dict) else {}
    value = benchmark.get("max_npcs", metadata.npc_count)
    return None if value is None else int(value)


def _pair_key(metadata: Any, summary: dict[str, Any], record_index: int) -> str:
    return "|".join(
        [
            _route_name(metadata, summary),
            str(_seed(metadata, summary)),
            str(_max_npcs(metadata, summary)),
            str(record_index),
        ]
    )


def _is_dense_lane_change(record: dict[str, Any]) -> bool:
    route = str(record["route_name"]).lower()
    return "lane_change" in route and (record["max_npcs"] or 0) >= 8


def _latency_ms(raw: dict[str, Any]) -> float | None:
    for key in (
        "latency_ms_including_candidate_generation",
        "selection_latency_ms",
        "latency_ms",
    ):
        value = raw.get(key)
        if value is None:
            continue
        value = float(value)
        if np.isfinite(value):
            return value
    return None


def _prefix(raw: dict[str, Any], candidate_count: int, label: str) -> np.ndarray:
    value = raw.get("candidate_perfect_tracker_postprocessed_reference_prefix")
    if value is None:
        value = raw.get("candidate_trajectories")
    prefix = np.asarray(value, dtype=np.float64)
    if prefix.ndim != 3 or prefix.shape[0] != candidate_count or prefix.shape[1] < 2:
        raise ValueError(
            f"{label} candidate prefix must have shape [K,T>=2,D]."
        )
    if prefix.shape[2] < 2 or not np.all(np.isfinite(prefix[:, :, :2])):
        raise ValueError(f"{label} candidate prefix xy values must be finite.")
    return prefix


def _vector(
    value: Any,
    expected: int,
    label: str,
    *,
    default: float | None = None,
) -> np.ndarray:
    if value is None and default is not None:
        return np.full(expected, float(default), dtype=np.float64)
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (expected,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must have shape [{expected}] with finite values.")
    return array


def _bool_vector(value: Any, expected: int, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=bool)
    if array.shape != (expected,):
        raise ValueError(f"{label} must have shape [{expected}].")
    return array


def _pairwise_distances(points: np.ndarray) -> np.ndarray:
    values = []
    for i in range(points.shape[0]):
        for j in range(i + 1, points.shape[0]):
            values.append(float(np.linalg.norm(points[i] - points[j])))
    return np.asarray(values, dtype=np.float64)


def _selected_axis(prefix: np.ndarray, selected: int) -> np.ndarray:
    delta = prefix[selected, -1, :2] - prefix[selected, 0, :2]
    norm = float(np.linalg.norm(delta))
    if norm <= 1e-9:
        return np.asarray([1.0, 0.0], dtype=np.float64)
    return delta / norm


def _mode_bin(value: float, threshold: float) -> str:
    if value > threshold:
        return "positive"
    if value < -threshold:
        return "negative"
    return "near"


def _validate_thresholds(thresholds: GateThresholds) -> None:
    for name, value in thresholds.__dict__.items():
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and nonnegative.")


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "max": None, "min": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "mean": float(np.mean(array)),
        "max": float(np.max(array)),
        "min": float(np.min(array)),
    }


def _spatial_summary(rows: list[dict[str, float]]) -> dict[str, dict[str, float | int | None]]:
    return {
        "endpoint_pairwise_mean_m": _summary(
            [row["endpoint_pairwise_mean_m"] for row in rows]
        ),
        "endpoint_pairwise_max_m": _summary(
            [row["endpoint_pairwise_max_m"] for row in rows]
        ),
        "mode_count": _summary([row["mode_count"] for row in rows]),
    }


def _spatial_gain_summary(
    baseline: list[dict[str, float]],
    candidate: list[dict[str, float]],
) -> dict[str, float]:
    return {
        "endpoint_pairwise_mean_m": _mean_metric(
            candidate, "endpoint_pairwise_mean_m"
        )
        - _mean_metric(baseline, "endpoint_pairwise_mean_m"),
        "mode_count": _mean_metric(candidate, "mode_count")
        - _mean_metric(baseline, "mode_count"),
    }


def _mean_metric(rows: list[dict[str, float]], key: str) -> float:
    if not rows:
        return 0.0
    return float(np.mean([row[key] for row in rows]))


def _contract_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "guidance_enabled_values": sorted(
            {bool(record["contract"]["guidance_enabled"]) for record in records}
        ),
        "guidance_policies": sorted(
            {str(record["contract"]["guidance_policy"]) for record in records}
        ),
        "changes_diffusion_planner_weights_values": sorted(
            {
                bool(record["contract"]["changes_diffusion_planner_weights"])
                for record in records
            }
        ),
        "changes_camp_score_values": sorted(
            {bool(record["contract"]["changes_camp_score"]) for record in records}
        ),
        "candidate0_guidance_policies": sorted(
            {str(record["contract"]["candidate0_guidance_policy"]) for record in records}
        ),
        "candidate0_preservation_structural_values": sorted(
            {
                bool(record["contract"]["candidate0_preservation_structural"])
                for record in records
            }
        ),
    }


if __name__ == "__main__":
    main()
