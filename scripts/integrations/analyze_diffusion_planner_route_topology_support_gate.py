#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


SOURCE_DONOR_REJECTED = "source_donor_support_insufficient"
READY_STATUS = "route_topology_candidate_design_ready"
BLOCKED_STATUS = "route_topology_candidate_design_blocked"
SOURCE_CONFLICT_STATUS = "route_topology_candidate_design_source_conflict"


@dataclass(frozen=True)
class RouteTopologyGateConfig:
    min_ready_snapshot_rate: float = 1.0
    max_candidate_lane_p95_m: float = 2.0
    max_red_lane_p95_m: float = 0.25
    min_lane_span_m: float = 80.0
    min_route_lane_span_m: float = 80.0
    min_lane_points: int = 20
    min_red_points: int = 1
    min_candidate_count: int = 2
    min_candidate_horizon: int = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only route/topology support readiness gate after existing "
            "DP candidate-pool donor support was rejected. It inspects fixed "
            "microbenchmark snapshots and does not run DP or generate new "
            "trajectories."
        )
    )
    parser.add_argument("--snapshot_dir", type=Path, required=True)
    parser.add_argument("--source_donor_support_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_ready_snapshot_rate", type=float, default=1.0)
    parser.add_argument("--max_candidate_lane_p95_m", type=float, default=2.0)
    parser.add_argument("--max_red_lane_p95_m", type=float, default=0.25)
    parser.add_argument("--min_lane_span_m", type=float, default=80.0)
    parser.add_argument("--min_route_lane_span_m", type=float, default=80.0)
    parser.add_argument("--min_lane_points", type=int, default=20)
    parser.add_argument("--min_red_points", type=int, default=1)
    parser.add_argument("--min_candidate_count", type=int, default=2)
    parser.add_argument("--min_candidate_horizon", type=int, default=20)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = RouteTopologyGateConfig(
        min_ready_snapshot_rate=args.min_ready_snapshot_rate,
        max_candidate_lane_p95_m=args.max_candidate_lane_p95_m,
        max_red_lane_p95_m=args.max_red_lane_p95_m,
        min_lane_span_m=args.min_lane_span_m,
        min_route_lane_span_m=args.min_route_lane_span_m,
        min_lane_points=args.min_lane_points,
        min_red_points=args.min_red_points,
        min_candidate_count=args.min_candidate_count,
        min_candidate_horizon=args.min_candidate_horizon,
    )
    report = analyze(
        snapshot_dir=args.snapshot_dir,
        source_donor_support_json=args.source_donor_support_json,
        label=args.label,
        config=config,
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
    snapshot_dir: Path,
    source_donor_support_json: Path,
    label: str | None = None,
    config: RouteTopologyGateConfig = RouteTopologyGateConfig(),
) -> dict[str, Any]:
    _validate_config(config)
    source_donor = _load_json(source_donor_support_json)
    rows = [_snapshot_row(path, config) for path in sorted(snapshot_dir.glob("*.npz"))]
    return build_report_from_rows(
        rows,
        source_donor=source_donor,
        label=label,
        config=config,
        paths={
            "snapshot_dir": str(snapshot_dir),
            "source_donor_support_json": str(source_donor_support_json),
        },
    )


def build_report_from_rows(
    rows: list[dict[str, Any]],
    *,
    source_donor: dict[str, Any],
    label: str | None = None,
    config: RouteTopologyGateConfig = RouteTopologyGateConfig(),
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_config(config)
    source_summary = _source_donor_summary(source_donor)
    conflicts = _authorization_conflicts(source_donor)
    aggregate = _aggregate_rows(rows, config)
    decision = _decision(
        aggregate=aggregate,
        source_summary=source_summary,
        conflicts=conflicts,
    )
    return {
        "analysis": {
            "name": "dp_camp_route_topology_support_gate_v1",
            "label": label,
            "role": (
                "read-only readiness gate for a route/topology-aware external "
                "candidate augmentation screen after existing DP source donors "
                "were rejected"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "candidate_generation_executed": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This gate only inspects fixed current-tick snapshot tensors. "
                "It does not modify DP, train CAMP, add atoms, run replay, or "
                "construct a DP-side Benders master/subproblem, dual, or cuts. "
                "A later route/topology candidate augmentation, if implemented, "
                "must produce deterministic fixed finite candidates from "
                "current-tick route/map tensors only; CAMP scores remain affine "
                "a_k^T w and the simplex/CVaR/L2 master remains convex for "
                "that fixed finite set."
            ),
            "paths": paths or {},
            "config": asdict(config),
        },
        "source_summaries": {
            "source_donor_support": source_summary,
        },
        "snapshot_aggregate": aggregate,
        "design_contract": _design_contract(),
        "blocked_actions": _blocked_actions(),
        "source_authorization_conflicts": conflicts,
        "final_decision": decision,
    }


def _snapshot_row(path: Path, config: RouteTopologyGateConfig) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as data:
        missing = [
            key
            for key in (
                "candidates",
                "lane_centerline",
                "red_route_points",
                "reward_input__route_lanes",
            )
            if key not in data.files
        ]
        if missing:
            return {
                "snapshot": path.name,
                "ready": False,
                "failure_reasons": [f"missing_{key}" for key in missing],
            }
        candidates = np.asarray(data["candidates"], dtype=float)
        lane = _finite_xy(np.asarray(data["lane_centerline"], dtype=float))
        red = _finite_xy(np.asarray(data["red_route_points"], dtype=float))
        route_lanes = np.asarray(data["reward_input__route_lanes"], dtype=float)
    candidate_xy = _candidate_xy(candidates)
    route_xy = _finite_xy(route_lanes[..., :2].reshape(-1, 2))
    candidate_lane_dist = _nearest_distances(
        _sample_points(candidate_xy.reshape(-1, 2)),
        lane,
    )
    red_lane_dist = _nearest_distances(red, lane)
    lane_span = _polyline_span(lane)
    route_lane_span = _polyline_span(route_xy)
    row = {
        "snapshot": path.name,
        "candidate_count": int(candidate_xy.shape[0]),
        "candidate_horizon": int(candidate_xy.shape[1]),
        "lane_points": int(len(lane)),
        "red_points": int(len(red)),
        "route_lane_points": int(len(route_xy)),
        "lane_span_m": lane_span,
        "route_lane_span_m": route_lane_span,
        "candidate_lane_p50_m": _percentile(candidate_lane_dist, 50.0),
        "candidate_lane_p95_m": _percentile(candidate_lane_dist, 95.0),
        "red_lane_p95_m": _percentile(red_lane_dist, 95.0),
        "finite": bool(
            np.isfinite(candidate_xy).all()
            and np.isfinite(lane).all()
            and np.isfinite(red).all()
            and np.isfinite(route_xy).all()
        ),
    }
    reasons = _row_failure_reasons(row, config)
    row["ready"] = not reasons
    row["failure_reasons"] = reasons
    return row


def _row_failure_reasons(
    row: dict[str, Any],
    config: RouteTopologyGateConfig,
) -> list[str]:
    reasons: list[str] = []
    if not row.get("finite"):
        reasons.append("nonfinite_topology_or_candidate_tensor")
    if row.get("candidate_count", 0) < config.min_candidate_count:
        reasons.append("candidate_count_too_small")
    if row.get("candidate_horizon", 0) < config.min_candidate_horizon:
        reasons.append("candidate_horizon_too_short")
    if row.get("lane_points", 0) < config.min_lane_points:
        reasons.append("lane_centerline_too_sparse")
    if row.get("red_points", 0) < config.min_red_points:
        reasons.append("red_route_points_missing")
    if row.get("lane_span_m", 0.0) < config.min_lane_span_m:
        reasons.append("lane_centerline_span_too_short")
    if row.get("route_lane_span_m", 0.0) < config.min_route_lane_span_m:
        reasons.append("route_lane_span_too_short")
    candidate_lane_p95 = row.get("candidate_lane_p95_m")
    if candidate_lane_p95 is None or candidate_lane_p95 > config.max_candidate_lane_p95_m:
        reasons.append("candidate_lane_coordinate_mismatch")
    red_lane_p95 = row.get("red_lane_p95_m")
    if red_lane_p95 is None or red_lane_p95 > config.max_red_lane_p95_m:
        reasons.append("red_route_lane_coordinate_mismatch")
    return reasons


def _aggregate_rows(
    rows: list[dict[str, Any]],
    config: RouteTopologyGateConfig,
) -> dict[str, Any]:
    ready = [row for row in rows if row.get("ready")]
    failure_counts: dict[str, int] = {}
    for row in rows:
        for reason in row.get("failure_reasons", []):
            failure_counts[reason] = failure_counts.get(reason, 0) + 1
    return {
        "snapshots": len(rows),
        "ready_snapshots": len(ready),
        "ready_snapshot_rate": _rate(len(ready), len(rows)),
        "required_ready_snapshot_rate": config.min_ready_snapshot_rate,
        "candidate_count_min": _min(row.get("candidate_count") for row in rows),
        "candidate_horizon_min": _min(row.get("candidate_horizon") for row in rows),
        "lane_points_min": _min(row.get("lane_points") for row in rows),
        "red_points_min": _min(row.get("red_points") for row in rows),
        "route_lane_points_min": _min(row.get("route_lane_points") for row in rows),
        "lane_span_min_m": _min(row.get("lane_span_m") for row in rows),
        "lane_span_p50_m": _percentile_values(
            (row.get("lane_span_m") for row in rows),
            50.0,
        ),
        "route_lane_span_min_m": _min(row.get("route_lane_span_m") for row in rows),
        "candidate_lane_p95_max_m": _max(
            row.get("candidate_lane_p95_m") for row in rows
        ),
        "candidate_lane_p95_p50_m": _percentile_values(
            (row.get("candidate_lane_p95_m") for row in rows),
            50.0,
        ),
        "red_lane_p95_max_m": _max(row.get("red_lane_p95_m") for row in rows),
        "failure_reason_counts": failure_counts,
        "sample_failures": [
            {
                "snapshot": row.get("snapshot"),
                "failure_reasons": row.get("failure_reasons"),
            }
            for row in rows
            if row.get("failure_reasons")
        ][:10],
    }


def _source_donor_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    support = report.get("support") or {}
    records = report.get("records") or {}
    return {
        "status": decision.get("status"),
        "hard_feasible_snapshot_support_rate": _first_number(
            support.get("hard_feasible_snapshot_support_rate"),
            records.get("hard_feasible_snapshot_support_rate"),
        ),
        "comfort_admissible_snapshot_support_rate": _first_number(
            support.get("comfort_admissible_snapshot_support_rate"),
            records.get("comfort_admissible_snapshot_support_rate"),
        ),
        "required_min_snapshot_support_rate": _first_number(
            support.get("required_min_snapshot_support_rate"),
            records.get("required_min_snapshot_support_rate"),
        ),
    }


def _decision(
    *,
    aggregate: dict[str, Any],
    source_summary: dict[str, Any],
    conflicts: list[str],
) -> dict[str, Any]:
    if conflicts:
        status = SOURCE_CONFLICT_STATUS
        next_step = "Fix or reject conflicting source authorization before new design work."
    elif source_summary["status"] != SOURCE_DONOR_REJECTED:
        status = SOURCE_CONFLICT_STATUS
        next_step = "Run or verify the source-donor support gate before route/topology work."
    elif aggregate["snapshots"] == 0:
        status = BLOCKED_STATUS
        next_step = "Provide fixed non-formal microbenchmark snapshots."
    elif (
        aggregate["ready_snapshot_rate"] is not None
        and aggregate["ready_snapshot_rate"]
        >= aggregate["required_ready_snapshot_rate"]
    ):
        status = READY_STATUS
        next_step = (
            "Implement a separate offline route/topology candidate-augmentation "
            "screen over fixed snapshots. The next screen must materialize "
            "deterministic current-tick candidates and recompute DP hard "
            "feasibility, red/lane costs, progress, comfort, and latency before "
            "any replay or online selector is considered."
        )
    else:
        status = BLOCKED_STATUS
        next_step = (
            "Reject route/topology candidate augmentation until snapshot "
            "coordinate compatibility or topology coverage is fixed."
        )
    return {
        "status": status,
        "offline_candidate_augmentation_screen_authorized": status == READY_STATUS,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "source_authorization_conflicts": conflicts,
        "next_step": next_step,
    }


def _design_contract() -> dict[str, Any]:
    return {
        "materially_new_vs_rejected_routes": [
            "does not choose from the existing DP candidate pool only",
            "does not use lower-red source donors that already fail red/lane hard checks",
            "does not tune bridge length or H-anchor transforms",
            "uses route/lane/red-light topology tensors available at the current tick",
        ],
        "required_next_screen": [
            "default-off offline analyzer only",
            "fixed current-tick deterministic candidate materialization",
            "no closed-loop future outcome labels during candidate construction",
            "DP hard-feasibility and reward recomputation before support claims",
            "progress, comfort, fallback, and latency summaries",
        ],
        "math_boundary": [
            "candidate diagnostics are constants for the current finite candidate set",
            "any later CAMP atom must be finite, nonnegative, and outcome-free",
            "CAMP score remains affine in weights",
            "simplex/CVaR/L2 master remains convex",
            "not classical Benders without a real subproblem, dual, and valid cuts",
        ],
    }


def _blocked_actions() -> list[str]:
    return [
        "online selector promotion",
        "closed-loop replay from this gate alone",
        "Full36",
        "formal seeds 11/12/13",
        "DP source or weight modification",
        "CAMP retraining",
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    aggregate = report["snapshot_aggregate"]
    source = report["source_summaries"]["source_donor_support"]
    lines = [
        "# Route/Topology Candidate-Support Readiness Gate",
        "",
        "This report is read-only. It does not run DP, generate candidates, train CAMP, run replay, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Offline candidate-augmentation screen authorized: `{decision['offline_candidate_augmentation_screen_authorized']}`",
        f"- Closed-loop smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "## Source Donor Gate",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in source.items():
        lines.append(f"| `{key}` | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Snapshot Topology",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key, value in aggregate.items():
        if key in {"failure_reason_counts", "sample_failures"}:
            continue
        lines.append(f"| `{key}` | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Failure Reasons",
            "",
            "```json",
            json.dumps(aggregate["failure_reason_counts"], indent=2, sort_keys=True),
            "```",
            "",
            "## Design Contract",
            "",
        ]
    )
    for key, items in report["design_contract"].items():
        lines.append(f"### {key}")
        lines.append("")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    lines.extend(
        [
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Decision",
            "",
            decision["next_step"],
            "",
        ]
    )
    return "\n".join(lines)


def _authorization_conflicts(report: dict[str, Any]) -> list[str]:
    decision = report.get("final_decision") or {}
    conflicts = []
    for key in (
        "online_selector_authorized",
        "closed_loop_smoke_authorized",
        "full36_authorized",
        "formal_seeds_authorized",
        "camp_retraining_authorized",
        "dp_modification_authorized",
    ):
        if decision.get(key):
            conflicts.append(f"source_donor_support:{key}")
    return conflicts


def _candidate_xy(candidates: np.ndarray) -> np.ndarray:
    if candidates.ndim != 3 or candidates.shape[2] < 2:
        return np.empty((0, 0, 2), dtype=float)
    return np.asarray(candidates[..., :2], dtype=float)


def _finite_xy(points: np.ndarray) -> np.ndarray:
    if points.ndim == 1:
        points = points.reshape(-1, points.shape[0])
    if points.ndim < 2 or points.shape[-1] < 2:
        return np.empty((0, 2), dtype=float)
    xy = np.asarray(points[..., :2], dtype=float).reshape(-1, 2)
    return xy[np.isfinite(xy).all(axis=1)]


def _sample_points(points: np.ndarray, max_points: int = 512) -> np.ndarray:
    if len(points) <= max_points:
        return points
    indexes = np.linspace(0, len(points) - 1, max_points).round().astype(int)
    return points[indexes]


def _nearest_distances(points: np.ndarray, reference: np.ndarray) -> np.ndarray:
    if len(points) == 0 or len(reference) == 0:
        return np.array([], dtype=float)
    chunks = []
    for chunk in np.array_split(points, max(1, len(points) // 256 + 1)):
        distances = np.linalg.norm(chunk[:, None, :] - reference[None, :, :], axis=2)
        chunks.append(distances.min(axis=1))
    return np.concatenate(chunks)


def _polyline_span(points: np.ndarray) -> float:
    if len(points) < 2:
        return 0.0
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def _percentile(values: np.ndarray, percentile: float) -> float | None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return float(np.percentile(finite, percentile))


def _percentile_values(values: Any, percentile: float) -> float | None:
    finite = [float(value) for value in values if value is not None and np.isfinite(value)]
    if not finite:
        return None
    return float(np.percentile(np.asarray(finite), percentile))


def _min(values: Any) -> float | int | None:
    finite = [value for value in values if value is not None and np.isfinite(value)]
    if not finite:
        return None
    result = min(finite)
    return int(result) if float(result).is_integer() else float(result)


def _max(values: Any) -> float | int | None:
    finite = [value for value in values if value is not None and np.isfinite(value)]
    if not finite:
        return None
    result = max(finite)
    return int(result) if float(result).is_integer() else float(result)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator / denominator)


def _first_number(*values: Any) -> float | None:
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number):
            return number
    return None


def _fmt(value: Any) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, float):
        return f"`{value:.6f}`"
    return f"`{value}`"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _validate_config(config: RouteTopologyGateConfig) -> None:
    if not 0.0 <= config.min_ready_snapshot_rate <= 1.0:
        raise ValueError("min_ready_snapshot_rate must be in [0, 1].")
    if config.max_candidate_lane_p95_m < 0.0:
        raise ValueError("max_candidate_lane_p95_m must be nonnegative.")
    if config.max_red_lane_p95_m < 0.0:
        raise ValueError("max_red_lane_p95_m must be nonnegative.")
    if config.min_lane_span_m < 0.0 or config.min_route_lane_span_m < 0.0:
        raise ValueError("minimum span thresholds must be nonnegative.")
    if config.min_lane_points < 0 or config.min_red_points < 0:
        raise ValueError("minimum point thresholds must be nonnegative.")
    if config.min_candidate_count < 1 or config.min_candidate_horizon < 1:
        raise ValueError("candidate thresholds must be positive.")


if __name__ == "__main__":
    main()
