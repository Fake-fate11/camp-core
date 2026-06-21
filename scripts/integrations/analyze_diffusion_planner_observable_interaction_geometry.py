#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)


PAYLOAD_KEY = "observable_state_logging"
SOURCE_STATUS = "observable_interaction_scenario_support_bottleneck_recorded"
SOURCE_NEXT_WORK = "reject_observable_interaction_coverage_or_inspect_map_geometry_before_replay"
READY_STATUS = "observable_interaction_geometry_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = "observable_interaction_geometry_source_not_ready"
NEXT_WORK = "reject_observable_interaction_route_or_predeclare_narrow_support_experiment"
FORMAL_SEEDS = frozenset({11, 12, 13})
BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "offline_separability_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only geometry audit for rejected observable-interaction "
            "coverage. It explains red stopline heading-alignment and NPC "
            "clearance support using existing logs, route pickle metadata, "
            "and map-file presence only; it does not run replay."
        )
    )
    parser.add_argument("--inventory_json", type=Path, required=True)
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--red_distance_budget_m", type=float, default=5.0)
    parser.add_argument("--clearance_budget_m", type=float, default=2.0)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        inventory_report=_read_json(args.inventory_json),
        plan_report=_read_json(args.plan_json),
        root=args.root,
        label=args.label,
        red_distance_budget_m=args.red_distance_budget_m,
        clearance_budget_m=args.clearance_budget_m,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_finite_json(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    *,
    inventory_report: dict[str, Any],
    plan_report: dict[str, Any],
    root: Path,
    label: str | None = None,
    red_distance_budget_m: float = 5.0,
    clearance_budget_m: float = 2.0,
) -> dict[str, Any]:
    source = _source_gate(inventory_report)
    log_paths = iter_selection_log_paths([root])
    if not log_paths:
        raise ValueError(f"No camp_selection_log.json files found under {root}.")

    geometry = _scan_geometry(
        log_paths,
        red_distance_budget_m=red_distance_budget_m,
        clearance_budget_m=clearance_budget_m,
    )
    route_summaries = _route_summaries(plan_report)
    red_bottleneck = _red_bottleneck(geometry["red"])
    clearance_bottleneck = _clearance_bottleneck(geometry["clearance"])
    source_passed = bool(source["passed"])
    passed = source_passed and bool(geometry["counts"]["payload_records"])
    final = {
        "status": READY_STATUS if passed else SOURCE_BLOCKED_STATUS,
        "passed": passed,
        "primary_gap": (
            f"{red_bottleneck},{clearance_bottleneck}"
            if passed
            else "source_inventory_gate_not_ready"
        ),
        "authorized_next_work": (
            NEXT_WORK if passed else "fix_inventory_source_before_geometry_audit"
        ),
        "current_observable_interaction_route_rejected": passed,
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_geometry_audit_v1",
            "label": label,
            "root": str(root),
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "closed_loop_outcome_labels_used": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "formal_seed_policy": "exclude_path_seed_11_12_13",
            "math_boundary": (
                "This audit reads only existing current-tick observable payloads "
                "and route/map metadata. Red and clearance quantities are fixed "
                "finite-candidate diagnostic coefficients, not online selector "
                "thresholds, outcome labels, learned weights, or trajectory-space "
                "convexity claims. If later atomized, they must enter CAMP as "
                "fixed candidate coefficients preserving affine score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 convex master. No DP-side classical "
                "Benders master/subproblem, dual, or cut is constructed."
            ),
        },
        "source_gate": source,
        "budgets": {
            "red_distance_budget_m": float(red_distance_budget_m),
            "clearance_budget_m": float(clearance_budget_m),
        },
        "route_summaries": route_summaries,
        "geometry": geometry,
        "bottlenecks": {
            "red_bottleneck": red_bottleneck,
            "clearance_bottleneck": clearance_bottleneck,
            "next_gate_hint": _next_gate_hint(red_bottleneck, clearance_bottleneck),
        },
        "final_decision": final,
    }


def render_markdown(report: dict[str, Any]) -> str:
    final = report["final_decision"]
    counts = report["geometry"]["counts"]
    red = report["geometry"]["red"]
    clearance = report["geometry"]["clearance"]
    bottlenecks = report["bottlenecks"]
    lines = [
        "# Observable Interaction Geometry Audit",
        "",
        f"- status: `{final['status']}`",
        f"- passed: `{final['passed']}`",
        f"- primary gap: `{final['primary_gap']}`",
        f"- authorized next work: `{final['authorized_next_work']}`",
        "",
        "## Counts",
        "",
        f"- scanned logs: `{counts['scanned_logs']}`",
        f"- excluded formal-seed logs: `{counts['excluded_formal_seed_logs']}`",
        f"- records: `{counts['records']}`",
        f"- payload records: `{counts['payload_records']}`",
        f"- payload candidates: `{counts['payload_candidates']}`",
        "",
        "## Red Geometry",
        "",
        f"- payload records: `{red['payload_records']}`",
        f"- reduced near-budget candidates: `{red['reduced_near_budget_candidates']}`",
        (
            "- reduced positive-alignment candidates: "
            f"`{red['reduced_positive_alignment_candidates']}`"
        ),
        (
            "- reduced near-and-positive candidates: "
            f"`{red['reduced_near_and_positive_candidates']}`"
        ),
        f"- raw positive-alignment samples: `{red['raw_positive_alignment_samples']}`",
        f"- raw near-and-positive samples: `{red['raw_near_and_positive_samples']}`",
        f"- min red distance m: `{_fmt(red['min_red_distance_m'])}`",
        f"- max reduced red alignment: `{_fmt(red['max_reduced_alignment'])}`",
        f"- max raw red alignment: `{_fmt(red['max_raw_alignment'])}`",
        f"- red bottleneck: `{bottlenecks['red_bottleneck']}`",
        "",
        "## Clearance Geometry",
        "",
        f"- finite clearance candidates: `{clearance['finite_clearance_candidates']}`",
        f"- positive obstacle-slot candidates: `{clearance['positive_obstacle_slot_candidates']}`",
        f"- clearance inside-budget candidates: `{clearance['inside_budget_candidates']}`",
        f"- min clearance m: `{_fmt(clearance['min_clearance_m'])}`",
        f"- clearance bottleneck: `{bottlenecks['clearance_bottleneck']}`",
        "",
        "## Routes",
        "",
        *_route_table(report["route_summaries"]),
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") if isinstance(report, dict) else None
    final = final if isinstance(final, dict) else {}
    return {
        "expected_status": SOURCE_STATUS,
        "actual_status": final.get("status"),
        "expected_authorized_next_work": SOURCE_NEXT_WORK,
        "actual_authorized_next_work": final.get("authorized_next_work"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and final.get("passed") is False
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and final.get("new_replay_authorized") is False
            and final.get("offline_separability_authorized") is False
            and final.get("camp_retraining_authorized") is False
        ),
    }


def _scan_geometry(
    log_paths: list[Path],
    *,
    red_distance_budget_m: float,
    clearance_budget_m: float,
) -> dict[str, Any]:
    counts = {
        "input_log_paths": len(log_paths),
        "scanned_logs": 0,
        "excluded_formal_seed_logs": 0,
        "records": 0,
        "payload_records": 0,
        "baseline_disabled_records": 0,
        "payload_candidates": 0,
        "formal_seed_records": 0,
    }
    red = _empty_red_metrics()
    clearance = _empty_clearance_metrics()
    log_summaries: list[dict[str, Any]] = []
    for log_path in log_paths:
        if any(seed in FORMAL_SEEDS for seed in _path_seeds(log_path)):
            counts["excluded_formal_seed_logs"] += 1
            continue
        counts["scanned_logs"] += 1
        rows = _read_selection_rows(log_path)
        summary = {
            "log_path": str(log_path),
            "records": len(rows),
            "payload_records": 0,
            "baseline_disabled_records": 0,
            "min_red_distance_m": math.inf,
            "max_reduced_alignment": -math.inf,
            "max_raw_alignment": -math.inf,
            "min_clearance_m": math.inf,
        }
        for row in rows:
            counts["records"] += 1
            payload = row.get(PAYLOAD_KEY) if isinstance(row, dict) else None
            if payload is None:
                counts["baseline_disabled_records"] += 1
                summary["baseline_disabled_records"] += 1
                continue
            if not isinstance(payload, dict):
                continue
            counts["payload_records"] += 1
            summary["payload_records"] += 1
            candidate_count = int(payload.get("candidate_count") or 0)
            counts["payload_candidates"] += candidate_count
            _accumulate_red(
                red,
                summary,
                payload,
                candidate_count=candidate_count,
                red_distance_budget_m=red_distance_budget_m,
            )
            _accumulate_clearance(
                clearance,
                summary,
                payload,
                candidate_count=candidate_count,
                clearance_budget_m=clearance_budget_m,
            )
        log_summaries.append(_finite_json(summary))
    return {
        "counts": counts,
        "red": _finalize_red(red),
        "clearance": _finalize_clearance(clearance),
        "log_summaries": log_summaries,
    }


def _empty_red_metrics() -> dict[str, Any]:
    return {
        "payload_records": 0,
        "reduced_candidate_count": 0,
        "reduced_near_budget_candidates": 0,
        "reduced_positive_alignment_candidates": 0,
        "reduced_near_and_positive_candidates": 0,
        "raw_sample_count": 0,
        "raw_near_budget_samples": 0,
        "raw_positive_alignment_samples": 0,
        "raw_near_and_positive_samples": 0,
        "min_red_distance_m": math.inf,
        "max_reduced_alignment": -math.inf,
        "max_raw_alignment": -math.inf,
    }


def _empty_clearance_metrics() -> dict[str, Any]:
    return {
        "payload_records": 0,
        "candidate_count": 0,
        "finite_clearance_candidates": 0,
        "positive_obstacle_slot_candidates": 0,
        "inside_budget_candidates": 0,
        "min_clearance_m": math.inf,
    }


def _accumulate_red(
    red: dict[str, Any],
    summary: dict[str, Any],
    payload: dict[str, Any],
    *,
    candidate_count: int,
    red_distance_budget_m: float,
) -> None:
    distances = _candidate_matrix(payload.get("candidate_red_stopline_distance_m"), candidate_count)
    alignments = _candidate_matrix(payload.get("candidate_red_heading_alignment"), candidate_count)
    if not distances or not alignments:
        return
    red["payload_records"] += 1
    for distance_row, alignment_row in zip(distances, alignments):
        finite_distances = [value for value in distance_row if math.isfinite(value)]
        finite_alignments = [value for value in alignment_row if math.isfinite(value)]
        if not finite_distances or not finite_alignments:
            continue
        min_distance = min(finite_distances)
        mean_alignment = sum(finite_alignments) / len(finite_alignments)
        red["reduced_candidate_count"] += 1
        red["min_red_distance_m"] = min(red["min_red_distance_m"], min_distance)
        red["max_reduced_alignment"] = max(red["max_reduced_alignment"], mean_alignment)
        summary["min_red_distance_m"] = min(summary["min_red_distance_m"], min_distance)
        summary["max_reduced_alignment"] = max(
            summary["max_reduced_alignment"], mean_alignment
        )
        near = min_distance < red_distance_budget_m
        positive = mean_alignment > 0.0
        red["reduced_near_budget_candidates"] += int(near)
        red["reduced_positive_alignment_candidates"] += int(positive)
        red["reduced_near_and_positive_candidates"] += int(near and positive)
        for distance, alignment in zip(distance_row, alignment_row):
            if not math.isfinite(distance) or not math.isfinite(alignment):
                continue
            red["raw_sample_count"] += 1
            red["min_red_distance_m"] = min(red["min_red_distance_m"], distance)
            red["max_raw_alignment"] = max(red["max_raw_alignment"], alignment)
            summary["min_red_distance_m"] = min(summary["min_red_distance_m"], distance)
            summary["max_raw_alignment"] = max(summary["max_raw_alignment"], alignment)
            raw_near = distance < red_distance_budget_m
            raw_positive = alignment > 0.0
            red["raw_near_budget_samples"] += int(raw_near)
            red["raw_positive_alignment_samples"] += int(raw_positive)
            red["raw_near_and_positive_samples"] += int(raw_near and raw_positive)


def _accumulate_clearance(
    clearance: dict[str, Any],
    summary: dict[str, Any],
    payload: dict[str, Any],
    *,
    candidate_count: int,
    clearance_budget_m: float,
) -> None:
    values = _candidate_vector(
        payload.get("candidate_min_obstacle_clearance_lower_bound_m"),
        candidate_count,
        none_value=math.inf,
    )
    slots = _candidate_vector(
        payload.get("candidate_obstacle_slot_count"),
        candidate_count,
        none_value=0.0,
    )
    if not values and not slots:
        return
    clearance["payload_records"] += 1
    for value, slot_count in zip(values, slots):
        clearance["candidate_count"] += 1
        slot_positive = math.isfinite(slot_count) and slot_count > 0.0
        clearance["positive_obstacle_slot_candidates"] += int(slot_positive)
        if not math.isfinite(value):
            continue
        clearance["finite_clearance_candidates"] += 1
        clearance["min_clearance_m"] = min(clearance["min_clearance_m"], value)
        summary["min_clearance_m"] = min(summary["min_clearance_m"], value)
        clearance["inside_budget_candidates"] += int(value < clearance_budget_m)


def _finalize_red(red: dict[str, Any]) -> dict[str, Any]:
    return _finite_json(red)


def _finalize_clearance(clearance: dict[str, Any]) -> dict[str, Any]:
    return _finite_json(clearance)


def _candidate_matrix(raw: Any, candidate_count: int) -> list[list[float]]:
    if raw is None or candidate_count <= 0 or not isinstance(raw, list):
        return []
    rows: list[list[float]] = []
    for index in range(candidate_count):
        item = raw[index] if index < len(raw) else None
        if isinstance(item, list):
            rows.append([_to_float(value) for value in item])
        else:
            rows.append([_to_float(item)])
    return rows


def _candidate_vector(raw: Any, candidate_count: int, *, none_value: float) -> list[float]:
    if candidate_count <= 0:
        return []
    if raw is None or not isinstance(raw, list):
        return [none_value] * candidate_count
    values = []
    for index in range(candidate_count):
        item = raw[index] if index < len(raw) else None
        if isinstance(item, list):
            finite = [_to_float(value) for value in item]
            finite = [value for value in finite if math.isfinite(value)]
            values.append(min(finite) if finite else none_value)
        else:
            value = _to_float(item)
            values.append(value if math.isfinite(value) else none_value)
    return values


def _route_summaries(plan_report: dict[str, Any]) -> list[dict[str, Any]]:
    spec = plan_report.get("plan_spec") if isinstance(plan_report, dict) else None
    runs = spec.get("runs") if isinstance(spec, dict) else None
    if not isinstance(runs, list):
        return []
    by_route: dict[str, dict[str, Any]] = {}
    for run in runs:
        if not isinstance(run, dict):
            continue
        route_path = str(run.get("route") or "")
        if not route_path:
            continue
        entry = by_route.setdefault(route_path, {"route_path": route_path, "run_ids": []})
        entry["run_ids"].append(str(run.get("run_id") or ""))
    summaries = []
    for route_path, base in sorted(by_route.items()):
        summary = {**base, **_load_route_summary(Path(route_path))}
        summaries.append(_finite_json(summary))
    return summaries


def _load_route_summary(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {"route_exists": path.exists()}
    if not path.exists():
        return summary
    try:
        with path.open("rb") as handle:
            route = pickle.load(handle)
    except Exception as exc:  # pragma: no cover - exercised on corrupted assets
        summary["route_load_error"] = f"{type(exc).__name__}: {exc}"
        return summary
    map_path = Path(str(getattr(route, "map_path", ""))) if getattr(route, "map_path", None) else None
    lanelet_ids = [int(item) for item in getattr(route, "route_lanelet_ids", [])]
    start_pose = _pose_list(getattr(route, "start_pose", None))
    goal_pose = _pose_list(getattr(route, "goal_pose", None))
    summary.update(
        {
            "map_path": str(map_path) if map_path else None,
            "map_exists": bool(map_path and map_path.exists()),
            "start_lanelet_id": _optional_int(getattr(route, "start_lanelet_id", None)),
            "goal_lanelet_id": _optional_int(getattr(route, "goal_lanelet_id", None)),
            "route_lanelet_count": len(lanelet_ids),
            "route_lanelet_ids_head": lanelet_ids[:8],
            "start_pose": start_pose,
            "goal_pose": goal_pose,
            "start_to_goal_distance_m": _pose_distance(start_pose, goal_pose),
            "start_to_goal_heading_rad": _pose_heading(start_pose, goal_pose),
            "route_start_heading_rad": start_pose[2] if len(start_pose) >= 3 else None,
            "route_goal_heading_rad": goal_pose[2] if len(goal_pose) >= 3 else None,
        }
    )
    if map_path and map_path.exists() and lanelet_ids:
        summary["map_route_relation_hits"] = _count_map_relation_hits(map_path, lanelet_ids)
    return summary


def _count_map_relation_hits(map_path: Path, lanelet_ids: list[int]) -> int:
    targets = {str(item) for item in lanelet_ids}
    hits = 0
    try:
        for _, elem in ET.iterparse(map_path, events=("end",)):
            if elem.tag == "relation" and elem.attrib.get("id") in targets:
                hits += 1
            elem.clear()
    except ET.ParseError:
        return 0
    return hits


def _red_bottleneck(red: dict[str, Any]) -> str:
    if red["reduced_near_and_positive_candidates"] > 0:
        return "red_context_supported"
    if red["payload_records"] <= 0:
        return "red_payload_absent"
    if red["reduced_near_budget_candidates"] <= 0:
        return "red_stopline_never_inside_budget"
    if red["reduced_positive_alignment_candidates"] <= 0:
        return "reduced_red_alignment_nonpositive"
    return "reduced_near_stopline_and_positive_alignment_do_not_overlap"


def _clearance_bottleneck(clearance: dict[str, Any]) -> str:
    if clearance["inside_budget_candidates"] > 0:
        return "clearance_context_supported"
    if clearance["finite_clearance_candidates"] <= 0:
        return "clearance_payload_absent"
    if clearance["positive_obstacle_slot_candidates"] <= 0:
        return "no_positive_obstacle_slots"
    return "clearance_budget_never_active"


def _next_gate_hint(red_bottleneck: str, clearance_bottleneck: str) -> str:
    if red_bottleneck == "reduced_red_alignment_nonpositive":
        return "inspect_or_redefine_red_alignment_direction_before_support_experiment"
    if clearance_bottleneck == "clearance_budget_never_active":
        return "inspect_npc_spawn_distance_or_predeclare_near_clearance_support_plan"
    return "reject_observable_interaction_route_or_predeclare_smaller_support_inventory"


def _read_selection_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list.")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"{path} record {index} must be an object.")
        rows.append(row)
    return rows


def _path_seeds(path: Path) -> set[int]:
    import re

    return {int(match) for match in re.findall(r"seed[_-](\d+)", str(path))}


def _pose_list(value: Any) -> list[float]:
    if value is None:
        return []
    try:
        return [float(item) for item in value]
    except TypeError:
        return []


def _pose_distance(start: list[float], goal: list[float]) -> float | None:
    if len(start) < 2 or len(goal) < 2:
        return None
    return math.hypot(goal[0] - start[0], goal[1] - start[1])


def _pose_heading(start: list[float], goal: list[float]) -> float | None:
    if len(start) < 2 or len(goal) < 2:
        return None
    return math.atan2(goal[1] - start[1], goal[0] - start[0])


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _finite_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _finite_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite_json(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _route_table(routes: list[dict[str, Any]]) -> list[str]:
    if not routes:
        return ["No routes found in the plan artifact."]
    lines = [
        "| Route | Runs | Lanelets | Map exists | Map lanelet hits | Start | Goal |",
        "| --- | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for route in routes:
        lines.append(
            "| "
            f"`{route.get('route_path')}` | "
            f"{len(route.get('run_ids') or [])} | "
            f"{route.get('route_lanelet_count', 'n/a')} | "
            f"`{route.get('map_exists')}` | "
            f"{route.get('map_route_relation_hits', 'n/a')} | "
            f"`{route.get('start_lanelet_id')}` | "
            f"`{route.get('goal_lanelet_id')}` |"
        )
    return lines


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            return "n/a"
        return f"{float(value):.6g}"
    return str(value)


if __name__ == "__main__":
    main()
