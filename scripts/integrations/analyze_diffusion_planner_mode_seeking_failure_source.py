#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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
    parse_selection_log_metadata,
)


FORMAL_SEEDS = {11, 12, 13}


@dataclass(frozen=True)
class FailureSourceThresholds:
    candidate0_preservation_max_abs_xy_m: float = 1e-6
    min_endpoint_pairwise_mean_m: float = 0.50
    min_endpoint_pairwise_gain_vs_baseline_m: float = 0.25
    min_mode_count_mean: float = 2.0
    progress_loss_budget_m: float = 0.10
    target_speed_loss_budget_mps: float = 0.20
    jerk_worse_budget_mps3: float = 0.05
    lateral_worse_budget_mps2: float = 0.05
    absolute_lateral_limit_mps2: float = 2.0
    latency_p95_limit_ms: float = 100.0
    lateral_mode_threshold_m: float = 0.25
    longitudinal_mode_threshold_m: float = 0.25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only failure-source diagnostic for a mode-seeking DP "
            "candidate-generation smoke. It separates reward feasibility "
            "blocking from current-tick geometry/PerfectTracker support and "
            "does not generate new DP candidates."
        )
    )
    parser.add_argument("--baseline_selection_log", type=Path, required=True)
    parser.add_argument("--candidate_selection_log", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--candidate0_preservation_max_abs_xy_m", type=float, default=1e-6)
    parser.add_argument("--min_endpoint_pairwise_mean_m", type=float, default=0.50)
    parser.add_argument("--min_endpoint_pairwise_gain_vs_baseline_m", type=float, default=0.25)
    parser.add_argument("--min_mode_count_mean", type=float, default=2.0)
    parser.add_argument("--progress_loss_budget_m", type=float, default=0.10)
    parser.add_argument("--target_speed_loss_budget_mps", type=float, default=0.20)
    parser.add_argument("--jerk_worse_budget_mps3", type=float, default=0.05)
    parser.add_argument("--lateral_worse_budget_mps2", type=float, default=0.05)
    parser.add_argument("--absolute_lateral_limit_mps2", type=float, default=2.0)
    parser.add_argument("--latency_p95_limit_ms", type=float, default=100.0)
    parser.add_argument("--lateral_mode_threshold_m", type=float, default=0.25)
    parser.add_argument("--longitudinal_mode_threshold_m", type=float, default=0.25)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = FailureSourceThresholds(
        candidate0_preservation_max_abs_xy_m=args.candidate0_preservation_max_abs_xy_m,
        min_endpoint_pairwise_mean_m=args.min_endpoint_pairwise_mean_m,
        min_endpoint_pairwise_gain_vs_baseline_m=(
            args.min_endpoint_pairwise_gain_vs_baseline_m
        ),
        min_mode_count_mean=args.min_mode_count_mean,
        progress_loss_budget_m=args.progress_loss_budget_m,
        target_speed_loss_budget_mps=args.target_speed_loss_budget_mps,
        jerk_worse_budget_mps3=args.jerk_worse_budget_mps3,
        lateral_worse_budget_mps2=args.lateral_worse_budget_mps2,
        absolute_lateral_limit_mps2=args.absolute_lateral_limit_mps2,
        latency_p95_limit_ms=args.latency_p95_limit_ms,
        lateral_mode_threshold_m=args.lateral_mode_threshold_m,
        longitudinal_mode_threshold_m=args.longitudinal_mode_threshold_m,
    )
    report = analyze(
        baseline_selection_log=args.baseline_selection_log,
        candidate_selection_log=args.candidate_selection_log,
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
    baseline_selection_log: Path,
    candidate_selection_log: Path,
    thresholds: FailureSourceThresholds = FailureSourceThresholds(),
    label: str | None = None,
) -> dict[str, Any]:
    baseline_context = _log_context(baseline_selection_log)
    candidate_context = _log_context(candidate_selection_log)
    baseline_records = _read_records(baseline_selection_log)
    candidate_records = _read_records(candidate_selection_log)
    return analyze_record_pairs(
        baseline_records,
        candidate_records,
        baseline_context=baseline_context,
        candidate_context=candidate_context,
        thresholds=thresholds,
        label=label,
        paths={
            "baseline_selection_log": str(baseline_selection_log),
            "candidate_selection_log": str(candidate_selection_log),
        },
    )


def analyze_record_pairs(
    baseline_records: list[dict[str, Any]],
    candidate_records: list[dict[str, Any]],
    *,
    baseline_context: dict[str, Any] | None = None,
    candidate_context: dict[str, Any] | None = None,
    thresholds: FailureSourceThresholds = FailureSourceThresholds(),
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    _validate_thresholds(thresholds)
    if not baseline_records or not candidate_records:
        raise ValueError("Both baseline and candidate records must be nonempty.")
    if len(baseline_records) != len(candidate_records):
        raise ValueError("Baseline and candidate records must have equal length.")
    baseline_context = baseline_context or {}
    candidate_context = candidate_context or {}

    rows = [
        _pair_row(
            baseline,
            candidate,
            record_index=index,
            thresholds=thresholds,
        )
        for index, (baseline, candidate) in enumerate(
            zip(baseline_records, candidate_records)
        )
    ]
    aggregate = _aggregate(rows, thresholds)
    formal = _formal_seed_report(baseline_context, candidate_context, len(rows))
    contract = _contract_report(candidate_records)
    decision = _decision(
        aggregate=aggregate,
        formal=formal,
        contract=contract,
    )
    return {
        "analysis": {
            "name": "dp_camp_mode_seeking_failure_source_v1",
            "label": label,
            "role": (
                "read-only diagnostic separating DP reward feasibility failure "
                "from current-tick geometry and PerfectTracker proxy support"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "All quantities are fixed current-tick finite-candidate log "
                "fields. Outcome labels are not used. CAMP scoring remains "
                "affine a_k^T w for any fixed candidate set and the "
                "simplex/CVaR/L2 master remains convex. This diagnostic is not "
                "classical Benders decomposition."
            ),
            "paths": paths or {},
        },
        "thresholds": thresholds.__dict__,
        "contexts": {
            "baseline": baseline_context,
            "candidate": candidate_context,
        },
        "records": {
            "paired_records": len(rows),
        },
        "contract": contract,
        "aggregate": aggregate,
        "formal_seed_policy": formal,
        "final_decision": decision,
        "sample_rows": rows[:5],
    }


def _pair_row(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    record_index: int,
    thresholds: FailureSourceThresholds,
) -> dict[str, Any]:
    base = _loaded_record(baseline, f"baseline record {record_index}")
    guided = _loaded_record(candidate, f"candidate record {record_index}")
    if base["candidate_count"] != guided["candidate_count"]:
        raise ValueError(f"record {record_index} candidate count mismatch.")
    candidate0_delta = _candidate0_delta(base["prefix"], guided["prefix"])
    baseline_spatial = _spatial_metrics(base["prefix"], thresholds)
    guided_spatial = _spatial_metrics(guided["prefix"], thresholds)
    support = _tracker_support(guided, thresholds)
    return {
        "record_index": record_index,
        "selected_index": guided["selected_index"],
        "candidate0_max_abs_xy_m": candidate0_delta,
        "candidate0_preserved": (
            candidate0_delta <= thresholds.candidate0_preservation_max_abs_xy_m
        ),
        "baseline_reward_feasible_count": int(base["feasible"].sum()),
        "candidate_reward_feasible_count": int(guided["feasible"].sum()),
        "candidate_reward_infeasibility_reasons": dict(
            Counter(
                reason
                for reasons in guided["infeasibility_reasons"]
                for reason in reasons
            )
        ),
        "baseline_spatial": baseline_spatial,
        "candidate_spatial": guided_spatial,
        "endpoint_pairwise_mean_gain_m": (
            guided_spatial["endpoint_pairwise_mean_m"]
            - baseline_spatial["endpoint_pairwise_mean_m"]
        ),
        "tracker_support": support,
        "latency_ms": guided["latency_ms"],
    }


def _loaded_record(raw: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index", 0))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    return {
        "candidate_count": candidate_count,
        "selected_index": selected,
        "feasible": _bool_vector(raw.get("feasible_mask"), candidate_count, f"{label} feasible_mask"),
        "infeasibility_reasons": _reasons(raw.get("infeasibility_reasons"), candidate_count),
        "prefix": _prefix(raw, candidate_count, label),
        "progress": _vector(
            raw.get("candidate_route_progress", raw.get("candidate_step_reach")),
            candidate_count,
            f"{label} candidate progress",
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
        "latency_ms": _latency_ms(raw),
    }


def _tracker_support(
    record: dict[str, Any],
    thresholds: FailureSourceThresholds,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    progress = record["progress"]
    speed = record["target_speed"]
    jerk = record["jerk"]
    lateral = record["lateral"]
    non_top1 = []
    relative_budget = []
    absolute_lateral = []
    combined = []
    for index in range(record["candidate_count"]):
        if index == 0 or index == selected:
            continue
        non_top1.append(index)
        relative_ok = (
            progress[index] >= progress[selected] - thresholds.progress_loss_budget_m
            and speed[index] >= speed[selected] - thresholds.target_speed_loss_budget_mps
            and jerk[index] <= jerk[selected] + thresholds.jerk_worse_budget_mps3
            and lateral[index] <= lateral[selected] + thresholds.lateral_worse_budget_mps2
        )
        lateral_ok = lateral[index] <= thresholds.absolute_lateral_limit_mps2
        if relative_ok:
            relative_budget.append(index)
        if lateral_ok:
            absolute_lateral.append(index)
        if relative_ok and lateral_ok:
            combined.append(index)
    return {
        "non_top1_candidate_count": len(non_top1),
        "relative_budget_support_count": len(relative_budget),
        "absolute_lateral_support_count": len(absolute_lateral),
        "combined_tracker_support_count": len(combined),
        "relative_budget_indices": relative_budget,
        "absolute_lateral_indices": absolute_lateral,
        "combined_tracker_indices": combined,
    }


def _aggregate(
    rows: list[dict[str, Any]],
    thresholds: FailureSourceThresholds,
) -> dict[str, Any]:
    latencies = [row["latency_ms"] for row in rows if row["latency_ms"] is not None]
    baseline_endpoint = _mean(
        [row["baseline_spatial"]["endpoint_pairwise_mean_m"] for row in rows]
    )
    candidate_endpoint = _mean(
        [row["candidate_spatial"]["endpoint_pairwise_mean_m"] for row in rows]
    )
    endpoint_gain = candidate_endpoint - baseline_endpoint
    candidate_mode = _mean([row["candidate_spatial"]["mode_count"] for row in rows])
    reward_feasible = sum(row["candidate_reward_feasible_count"] for row in rows)
    relative_support_records = sum(
        int(row["tracker_support"]["relative_budget_support_count"] > 0)
        for row in rows
    )
    combined_support_records = sum(
        int(row["tracker_support"]["combined_tracker_support_count"] > 0)
        for row in rows
    )
    reason_counts: Counter[str] = Counter()
    for row in rows:
        reason_counts.update(row["candidate_reward_infeasibility_reasons"])
    p95_latency = None if not latencies else float(np.percentile(latencies, 95))
    gates = {
        "candidate0_preserved": all(row["candidate0_preserved"] for row in rows),
        "reward_feasible_exists": reward_feasible > 0,
        "relative_tracker_support_exists": relative_support_records > 0,
        "combined_tracker_support_exists": combined_support_records > 0,
        "endpoint_pairwise_mean_pass": (
            candidate_endpoint >= thresholds.min_endpoint_pairwise_mean_m
        ),
        "endpoint_gain_pass": (
            endpoint_gain >= thresholds.min_endpoint_pairwise_gain_vs_baseline_m
        ),
        "mode_count_pass": candidate_mode >= thresholds.min_mode_count_mean,
        "latency_p95_pass": (
            p95_latency is not None and p95_latency < thresholds.latency_p95_limit_ms
        ),
    }
    return {
        "candidate0_preservation_max_abs_xy_m": max(
            row["candidate0_max_abs_xy_m"] for row in rows
        ),
        "candidate_reward_feasible_total": reward_feasible,
        "candidate_reward_infeasibility_reason_counts": dict(reason_counts),
        "relative_tracker_support_records": relative_support_records,
        "combined_tracker_support_records": combined_support_records,
        "baseline_endpoint_pairwise_mean_m": baseline_endpoint,
        "candidate_endpoint_pairwise_mean_m": candidate_endpoint,
        "endpoint_pairwise_mean_gain_m": endpoint_gain,
        "candidate_mode_count_mean": candidate_mode,
        "latency_p95_ms": p95_latency,
        "gates": gates,
    }


def _decision(
    *,
    aggregate: dict[str, Any],
    formal: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    gates = aggregate["gates"]
    formal_ok = not formal["formal_seeds_present"]
    contract_ok = (
        contract["guidance_enabled_values"] == [True]
        and contract["candidate0_preservation_structural_values"] == [True]
        and contract["changes_diffusion_planner_weights_values"] == [False]
        and contract["changes_camp_score_values"] == [False]
    )
    reward_gate_suspect = (
        formal_ok
        and contract_ok
        and gates["candidate0_preserved"]
        and not gates["reward_feasible_exists"]
        and gates["combined_tracker_support_exists"]
        and gates["endpoint_pairwise_mean_pass"]
        and gates["endpoint_gain_pass"]
    )
    geometry_or_tracker_insufficient = not (
        gates["combined_tracker_support_exists"]
        and gates["endpoint_pairwise_mean_pass"]
        and gates["endpoint_gain_pass"]
    )
    latency_blocked = not gates["latency_p95_pass"]
    if reward_gate_suspect:
        status = "mode_seeking_failure_source_reward_gate_suspect"
        next_step = (
            "Design a separate feasibility-gate audit before changing any "
            "selector or running closed-loop replay."
        )
    else:
        status = "mode_seeking_failure_source_candidate_support_insufficient"
        next_step = (
            "Reject this guidance candidate-generation branch unless a "
            "materially different generator can improve geometry/tracker "
            "support and latency."
        )
    return {
        "status": status,
        "reward_gate_suspect": reward_gate_suspect,
        "geometry_or_tracker_support_insufficient": geometry_or_tracker_insufficient,
        "latency_blocked": latency_blocked,
        "formal_seeds_absent": formal_ok,
        "contract_ok": contract_ok,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    aggregate = report["aggregate"]
    lines = [
        "# DP CAMP Mode-Seeking Failure-Source Diagnostic",
        "",
        "This is a read-only diagnostic over existing selection logs. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Reward gate suspect: `{decision['reward_gate_suspect']}`",
        f"- Geometry/tracker support insufficient: `{decision['geometry_or_tracker_support_insufficient']}`",
        f"- Latency blocked: `{decision['latency_blocked']}`",
        f"- Closed-loop smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        "",
        "## Metrics",
        "",
        f"- Candidate0 max abs xy: `{aggregate['candidate0_preservation_max_abs_xy_m']}`",
        f"- Reward-feasible candidates: `{aggregate['candidate_reward_feasible_total']}`",
        f"- Relative tracker-support records: `{aggregate['relative_tracker_support_records']}`",
        f"- Combined tracker-support records: `{aggregate['combined_tracker_support_records']}`",
        f"- Candidate endpoint pairwise mean: `{aggregate['candidate_endpoint_pairwise_mean_m']}`",
        f"- Endpoint pairwise mean gain: `{aggregate['endpoint_pairwise_mean_gain_m']}`",
        f"- Candidate mode-count mean: `{aggregate['candidate_mode_count_mean']}`",
        f"- Latency p95 ms: `{aggregate['latency_p95_ms']}`",
        "",
        "Gates:",
    ]
    for key, value in aggregate["gates"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "Reward infeasibility reasons:",
        ]
    )
    for key, value in aggregate["candidate_reward_infeasibility_reason_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
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


def _read_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a nonempty JSON list.")
    return payload


def _log_context(path: Path) -> dict[str, Any]:
    metadata = parse_selection_log_metadata(path)
    summary_path = path.with_name("camp_validation_summary.json")
    summary = {}
    if summary_path.is_file():
        payload = json.loads(summary_path.read_text(encoding="utf-8-sig"))
        summary = payload if isinstance(payload, dict) else {}
    benchmark = summary.get("benchmark") if isinstance(summary.get("benchmark"), dict) else {}
    seed = benchmark.get("seed", metadata.seed)
    return {
        "log_path": str(path),
        "route_name": Path(str(benchmark.get("route", metadata.route))).stem,
        "seed": seed,
        "max_npcs": benchmark.get("max_npcs", metadata.npc_count),
        "formal_seed": seed in FORMAL_SEEDS if seed is not None else False,
    }


def _formal_seed_report(
    baseline_context: dict[str, Any],
    candidate_context: dict[str, Any],
    record_count: int,
) -> dict[str, Any]:
    present = bool(
        baseline_context.get("formal_seed") or candidate_context.get("formal_seed")
    )
    return {
        "formal_seed_records": record_count if present else 0,
        "formal_seeds_present": present,
    }


def _contract_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    contracts = [_contract(record) for record in records]
    return {
        "guidance_enabled_values": sorted(
            {bool(contract.get("guidance_enabled")) for contract in contracts}
        ),
        "candidate0_guidance_policies": sorted(
            {str(contract.get("candidate0_guidance_policy")) for contract in contracts}
        ),
        "candidate0_preservation_structural_values": sorted(
            {bool(contract.get("candidate0_preservation_structural")) for contract in contracts}
        ),
        "changes_diffusion_planner_weights_values": sorted(
            {bool(contract.get("changes_diffusion_planner_weights")) for contract in contracts}
        ),
        "changes_camp_score_values": sorted(
            {bool(contract.get("changes_camp_score")) for contract in contracts}
        ),
    }


def _contract(record: dict[str, Any]) -> dict[str, Any]:
    contract = record.get("candidate_generation_contract")
    if not isinstance(contract, dict):
        raise ValueError("record is missing candidate_generation_contract.")
    return contract


def _prefix(raw: dict[str, Any], candidate_count: int, label: str) -> np.ndarray:
    value = raw.get("candidate_perfect_tracker_postprocessed_reference_prefix")
    if value is None:
        value = raw.get("candidate_trajectories")
    prefix = np.asarray(value, dtype=np.float64)
    if prefix.ndim != 3 or prefix.shape[0] != candidate_count or prefix.shape[1] < 2:
        raise ValueError(f"{label} candidate prefix must have shape [K,T>=2,D].")
    if prefix.shape[2] < 2 or not np.all(np.isfinite(prefix[:, :, :2])):
        raise ValueError(f"{label} candidate prefix xy values must be finite.")
    return prefix


def _candidate0_delta(baseline_prefix: np.ndarray, candidate_prefix: np.ndarray) -> float:
    baseline = baseline_prefix[0, :, :2]
    candidate = candidate_prefix[0, :, :2]
    if baseline.shape != candidate.shape:
        raise ValueError("candidate0 prefix shape mismatch.")
    return float(np.max(np.abs(candidate - baseline)))


def _spatial_metrics(prefix: np.ndarray, thresholds: FailureSourceThresholds) -> dict[str, float]:
    endpoints = prefix[:, -1, :2]
    pairwise = _pairwise_distances(endpoints)
    axis = _selected_axis(prefix, 0)
    lateral_axis = np.asarray([-axis[1], axis[0]], dtype=np.float64)
    deltas = endpoints - endpoints[0]
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


def _reasons(value: Any, expected: int) -> list[list[str]]:
    if value is None:
        return [[] for _ in range(expected)]
    if not isinstance(value, list) or len(value) != expected:
        raise ValueError(f"infeasibility_reasons must have length {expected}.")
    return [[str(reason) for reason in reasons] for reasons in value]


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


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _validate_thresholds(thresholds: FailureSourceThresholds) -> None:
    for name, value in thresholds.__dict__.items():
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and nonnegative.")


if __name__ == "__main__":
    main()
