#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
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
from scripts.integrations.analyze_diffusion_planner_observable_interaction_scenario_support import (  # noqa: E402
    BOTTLENECK_STATUS as SUPPORT_SOURCE_STATUS,
)


PAYLOAD_KEY = "observable_state_logging"
FORMAL_SEEDS = frozenset({11, 12, 13})
READY_STATUS = "observable_interaction_payload_attribution_diagnosed"
SOURCE_BLOCKED_STATUS = "observable_interaction_payload_attribution_source_not_ready"
SUPPORT_PRESENT_STATUS = "observable_interaction_payload_attribution_support_present"
NEXT_WORK_DIAGNOSE = (
    "diagnose_red_alignment_sign_semantics_and_reject_or_redesign_clearance_context"
)
NEXT_WORK_SOURCE = "fix_scenario_support_and_route_geometry_sources_before_attribution"
NEXT_WORK_SUPPORT = "predeclare_smaller_observable_interaction_inventory_only"
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
            "Read-only payload attribution for missing observable-interaction "
            "support. It splits red-context failure into red-route-point, "
            "distance, and alignment causes, and clearance failure into obstacle "
            "slot, missing-clearance, and far-obstacle causes."
        )
    )
    parser.add_argument("--scenario_support_json", type=Path, required=True)
    parser.add_argument("--route_geometry_json", type=Path, required=True)
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--red_distance_budget_m", type=float, default=5.0)
    parser.add_argument("--clearance_budget_m", type=float, default=2.0)
    parser.add_argument("--max_examples", type=int, default=12)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        scenario_support_report=_read_json(args.scenario_support_json),
        route_geometry_report=_read_json(args.route_geometry_json),
        label=args.label,
        red_distance_budget_m=args.red_distance_budget_m,
        clearance_budget_m=args.clearance_budget_m,
        max_examples=args.max_examples,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    scenario_support_report: dict[str, Any],
    route_geometry_report: dict[str, Any],
    label: str | None = None,
    red_distance_budget_m: float = 5.0,
    clearance_budget_m: float = 2.0,
    max_examples: int = 12,
) -> dict[str, Any]:
    source = _source_gate(scenario_support_report, route_geometry_report)
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No camp_selection_log.json files were found.")

    counts = {
        "input_log_paths": len(log_paths),
        "scanned_logs": 0,
        "excluded_formal_seed_logs": 0,
        "records": 0,
        "candidate_payload_records": 0,
        "baseline_disabled_records": 0,
        "payload_candidates": 0,
        "formal_seed_records": 0,
    }
    red_reasons: Counter[str] = Counter()
    red_record_reasons: Counter[str] = Counter()
    clearance_reasons: Counter[str] = Counter()
    clearance_record_reasons: Counter[str] = Counter()
    red_metrics = {
        "records_with_red_route_points": 0,
        "records_with_red_relation_fields": 0,
        "records_with_red_distance_within_budget": 0,
        "records_with_red_mean_alignment_positive": 0,
        "records_with_red_step_alignment_positive": 0,
        "records_with_red_support": 0,
        "candidate_red_support_count": 0,
        "candidate_red_distance_within_budget_count": 0,
        "candidate_red_mean_alignment_positive_count": 0,
        "candidate_red_step_alignment_positive_count": 0,
        "min_red_distance_m": math.inf,
        "max_red_mean_alignment": -math.inf,
        "max_red_step_alignment": -math.inf,
    }
    clearance_metrics = {
        "records_with_obstacle_slots_positive": 0,
        "records_with_clearance_finite": 0,
        "records_with_clearance_within_budget": 0,
        "candidate_obstacle_slots_positive_count": 0,
        "candidate_clearance_finite_count": 0,
        "candidate_clearance_within_budget_count": 0,
        "min_clearance_m": math.inf,
        "max_obstacle_slot_count": 0,
    }
    red_examples: list[dict[str, Any]] = []
    clearance_examples: list[dict[str, Any]] = []
    log_summaries: list[dict[str, Any]] = []

    for log_path in log_paths:
        path_seeds = sorted(_path_seeds(log_path))
        if any(seed in FORMAL_SEEDS for seed in path_seeds):
            counts["excluded_formal_seed_logs"] += 1
            continue
        counts["scanned_logs"] += 1
        rows = _read_selection_rows(log_path)
        log_summary = {
            "log_path": str(log_path),
            "records": len(rows),
            "candidate_payload_records": 0,
            "baseline_disabled_records": 0,
            "red_candidate_reason_counts": Counter(),
            "clearance_candidate_reason_counts": Counter(),
        }
        for record_index, record in enumerate(rows):
            counts["records"] += 1
            payload = record.get(PAYLOAD_KEY)
            if payload is None:
                counts["baseline_disabled_records"] += 1
                log_summary["baseline_disabled_records"] += 1
                continue
            if not isinstance(payload, dict):
                continue
            counts["candidate_payload_records"] += 1
            log_summary["candidate_payload_records"] += 1
            counts["formal_seed_records"] += int(any(seed in FORMAL_SEEDS for seed in path_seeds))
            contexts = _candidate_contexts(
                payload,
                log_path=log_path,
                record_index=record_index,
                red_distance_budget_m=red_distance_budget_m,
                clearance_budget_m=clearance_budget_m,
            )
            counts["payload_candidates"] += len(contexts)
            record_red_reasons = set()
            record_clearance_reasons = set()
            record_flags = _record_flags(
                contexts,
                payload,
                red_distance_budget_m=red_distance_budget_m,
                clearance_budget_m=clearance_budget_m,
            )
            for key, flag in record_flags["red"].items():
                red_metrics[key] += int(flag)
            for key, flag in record_flags["clearance"].items():
                clearance_metrics[key] += int(flag)
            for item in contexts:
                red_reason = item["red_failure_reason"]
                clearance_reason = item["clearance_failure_reason"]
                red_reasons[red_reason] += 1
                clearance_reasons[clearance_reason] += 1
                log_summary["red_candidate_reason_counts"][red_reason] += 1
                log_summary["clearance_candidate_reason_counts"][clearance_reason] += 1
                record_red_reasons.add(red_reason)
                record_clearance_reasons.add(clearance_reason)
                _update_red_metric_extrema(
                    red_metrics,
                    item,
                    red_distance_budget_m,
                )
                _update_clearance_metric_extrema(
                    clearance_metrics,
                    item,
                    clearance_budget_m,
                )
                if item["red_failure_reason"] != "red_supported":
                    red_examples.append(item)
                if item["clearance_failure_reason"] != "clearance_supported":
                    clearance_examples.append(item)
            for reason in record_red_reasons:
                red_record_reasons[reason] += 1
            for reason in record_clearance_reasons:
                clearance_record_reasons[reason] += 1
        log_summary["red_candidate_reason_counts"] = dict(
            sorted(log_summary["red_candidate_reason_counts"].items())
        )
        log_summary["clearance_candidate_reason_counts"] = dict(
            sorted(log_summary["clearance_candidate_reason_counts"].items())
        )
        log_summaries.append(log_summary)

    red_supported = red_reasons.get("red_supported", 0) > 0
    clearance_supported = clearance_reasons.get("clearance_supported", 0) > 0
    source_ready = bool(source["passed"])
    if not source_ready:
        status = SOURCE_BLOCKED_STATUS
        passed = False
        next_work = NEXT_WORK_SOURCE
    elif red_supported or clearance_supported:
        status = SUPPORT_PRESENT_STATUS
        passed = True
        next_work = NEXT_WORK_SUPPORT
    else:
        status = READY_STATUS
        passed = True
        next_work = NEXT_WORK_DIAGNOSE

    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_payload_attribution_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "closed_loop_outcome_labels_used": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "formal_seed_policy": "exclude_path_seed_11_12_13",
            "math_boundary": (
                "This attribution reads only existing current-tick observable "
                "payloads. It diagnoses why finite-candidate red and clearance "
                "support is absent; it creates no selector, threshold, atom "
                "weight, outcome label, trajectory-space convexity claim, or "
                "Benders cut. Any later atomization must still use fixed "
                "pre-outcome candidate coefficients and preserve affine "
                "score_k(w)=a_k^T w with a convex simplex/CVaR/L2 master."
            ),
        },
        "source_gate": source,
        "budgets": {
            "red_distance_budget_m": float(red_distance_budget_m),
            "clearance_budget_m": float(clearance_budget_m),
        },
        "counts": counts,
        "red_attribution": {
            "candidate_reason_counts": dict(sorted(red_reasons.items())),
            "record_reason_counts": dict(sorted(red_record_reasons.items())),
            "metrics": _finite_json(red_metrics),
            "top_failure_examples": [
                _finite_json(item)
                for item in _rank_red_examples(red_examples)[: max(0, max_examples)]
            ],
        },
        "clearance_attribution": {
            "candidate_reason_counts": dict(sorted(clearance_reasons.items())),
            "record_reason_counts": dict(sorted(clearance_record_reasons.items())),
            "metrics": _finite_json(clearance_metrics),
            "top_failure_examples": [
                _finite_json(item)
                for item in _rank_clearance_examples(clearance_examples)[
                    : max(0, max_examples)
                ]
            ],
        },
        "log_summaries": log_summaries,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": {
            "status": status,
            "passed": passed,
            "primary_gap": _primary_gap(red_reasons, clearance_reasons, source_ready),
            "authorized_next_work": next_work,
            **{key: False for key in BLOCKED_ACTIONS},
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["counts"]
    red = report["red_attribution"]
    clearance = report["clearance_attribution"]
    lines = [
        "# Observable Interaction Payload Attribution",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Counts",
        "",
        f"- scanned logs: `{counts['scanned_logs']}`",
        f"- records: `{counts['records']}`",
        f"- candidate payload records: `{counts['candidate_payload_records']}`",
        f"- payload candidates: `{counts['payload_candidates']}`",
        "",
        "## Red Attribution",
        "",
        _dict_block(red["candidate_reason_counts"]),
        "",
        _dict_block(red["metrics"]),
        "",
        "## Clearance Attribution",
        "",
        _dict_block(clearance["candidate_reason_counts"]),
        "",
        _dict_block(clearance["metrics"]),
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


def _candidate_contexts(
    payload: dict[str, Any],
    *,
    log_path: Path,
    record_index: int,
    red_distance_budget_m: float,
    clearance_budget_m: float,
) -> list[dict[str, Any]]:
    candidate_count = int(payload.get("candidate_count") or 0)
    red_distance = _candidate_matrix_reduction(
        payload.get("candidate_red_stopline_distance_m"),
        candidate_count,
        reduce_matrix="min",
        none_value=None,
    )
    red_mean_alignment = _candidate_matrix_reduction(
        payload.get("candidate_red_heading_alignment"),
        candidate_count,
        reduce_matrix="mean",
        none_value=None,
    )
    red_max_alignment = _candidate_matrix_reduction(
        payload.get("candidate_red_heading_alignment"),
        candidate_count,
        reduce_matrix="max",
        none_value=None,
    )
    clearance = _candidate_scalar_list(
        payload.get("candidate_min_obstacle_clearance_lower_bound_m"),
        candidate_count,
    )
    obstacle_slots = _candidate_scalar_list(
        payload.get("candidate_obstacle_slot_count"),
        candidate_count,
        integer=True,
    )
    red_route_point_count = int(payload.get("red_route_point_count") or 0)
    contexts = []
    for candidate_index in range(candidate_count):
        distance = red_distance[candidate_index]
        mean_alignment = red_mean_alignment[candidate_index]
        max_alignment = red_max_alignment[candidate_index]
        min_clearance = clearance[candidate_index]
        slot_count = obstacle_slots[candidate_index]
        red_risk = (
            max(mean_alignment, 0.0) * max(red_distance_budget_m - distance, 0.0)
            if distance is not None and mean_alignment is not None
            else 0.0
        )
        clearance_deficit = (
            max(clearance_budget_m - min_clearance, 0.0)
            if min_clearance is not None
            else 0.0
        )
        item = {
            "log_path": str(log_path),
            "record_index": record_index,
            "candidate_index": candidate_index,
            "red_route_point_count": red_route_point_count,
            "red_distance_m": distance,
            "red_mean_alignment": mean_alignment,
            "red_max_step_alignment": max_alignment,
            "red_risk": red_risk,
            "clearance_m": min_clearance,
            "obstacle_slot_count": slot_count,
            "clearance_deficit": clearance_deficit,
        }
        item["red_failure_reason"] = _red_failure_reason(
            item,
            red_distance_budget_m=red_distance_budget_m,
        )
        item["clearance_failure_reason"] = _clearance_failure_reason(
            item,
            clearance_budget_m=clearance_budget_m,
        )
        contexts.append(item)
    return contexts


def _red_failure_reason(
    item: dict[str, Any],
    *,
    red_distance_budget_m: float,
) -> str:
    if int(item["red_route_point_count"]) <= 0:
        return "red_route_points_absent"
    if item["red_distance_m"] is None or item["red_mean_alignment"] is None:
        return "red_relation_fields_missing"
    if float(item["red_distance_m"]) > float(red_distance_budget_m):
        return "red_distance_outside_budget"
    if float(item["red_mean_alignment"]) <= 0.0:
        if (
            item["red_max_step_alignment"] is not None
            and float(item["red_max_step_alignment"]) > 0.0
        ):
            return "red_step_positive_but_mean_nonpositive"
        return "red_alignment_nonpositive"
    return "red_supported"


def _clearance_failure_reason(
    item: dict[str, Any],
    *,
    clearance_budget_m: float,
) -> str:
    slot_count = item["obstacle_slot_count"]
    clearance = item["clearance_m"]
    if slot_count is None or int(slot_count) <= 0:
        return "obstacle_slots_absent"
    if clearance is None:
        return "clearance_missing"
    if float(clearance) > float(clearance_budget_m):
        return "obstacles_present_but_far"
    return "clearance_supported"


def _record_flags(
    contexts: list[dict[str, Any]],
    payload: dict[str, Any],
    *,
    red_distance_budget_m: float,
    clearance_budget_m: float,
) -> dict[str, dict[str, bool]]:
    red_route_points = int(payload.get("red_route_point_count") or 0) > 0
    return {
        "red": {
            "records_with_red_route_points": red_route_points,
            "records_with_red_relation_fields": any(
                item["red_distance_m"] is not None
                and item["red_mean_alignment"] is not None
                for item in contexts
            ),
            "records_with_red_distance_within_budget": any(
                item["red_distance_m"] is not None
                and item["red_distance_m"] <= float(red_distance_budget_m)
                for item in contexts
            ),
            "records_with_red_mean_alignment_positive": any(
                item["red_mean_alignment"] is not None
                and item["red_mean_alignment"] > 0.0
                for item in contexts
            ),
            "records_with_red_step_alignment_positive": any(
                item["red_max_step_alignment"] is not None
                and item["red_max_step_alignment"] > 0.0
                for item in contexts
            ),
            "records_with_red_support": any(
                item["red_failure_reason"] == "red_supported" for item in contexts
            ),
        },
        "clearance": {
            "records_with_obstacle_slots_positive": any(
                item["obstacle_slot_count"] is not None
                and int(item["obstacle_slot_count"]) > 0
                for item in contexts
            ),
            "records_with_clearance_finite": any(
                item["clearance_m"] is not None for item in contexts
            ),
            "records_with_clearance_within_budget": any(
                item["clearance_m"] is not None
                and item["clearance_m"] <= float(clearance_budget_m)
                for item in contexts
            ),
        },
    }


def _update_red_metric_extrema(
    metrics: dict[str, Any],
    item: dict[str, Any],
    red_distance_budget_m: float,
) -> None:
    if item["red_distance_m"] is not None:
        metrics["min_red_distance_m"] = min(
            metrics["min_red_distance_m"], float(item["red_distance_m"])
        )
        if float(item["red_distance_m"]) <= float(red_distance_budget_m):
            metrics["candidate_red_distance_within_budget_count"] += 1
    if item["red_mean_alignment"] is not None:
        metrics["max_red_mean_alignment"] = max(
            metrics["max_red_mean_alignment"], float(item["red_mean_alignment"])
        )
        if float(item["red_mean_alignment"]) > 0.0:
            metrics["candidate_red_mean_alignment_positive_count"] += 1
    if item["red_max_step_alignment"] is not None:
        metrics["max_red_step_alignment"] = max(
            metrics["max_red_step_alignment"], float(item["red_max_step_alignment"])
        )
        if float(item["red_max_step_alignment"]) > 0.0:
            metrics["candidate_red_step_alignment_positive_count"] += 1
    if item["red_failure_reason"] == "red_supported":
        metrics["candidate_red_support_count"] += 1


def _update_clearance_metric_extrema(
    metrics: dict[str, Any],
    item: dict[str, Any],
    clearance_budget_m: float,
) -> None:
    if "clearance_m" in item and item["clearance_m"] is not None:
        metrics["min_clearance_m"] = min(
            metrics["min_clearance_m"], float(item["clearance_m"])
        )
        metrics["candidate_clearance_finite_count"] += 1
        if float(item["clearance_m"]) <= float(clearance_budget_m):
            metrics["candidate_clearance_within_budget_count"] += 1
    if item.get("obstacle_slot_count") is not None:
        slot_count = int(item["obstacle_slot_count"])
        metrics["max_obstacle_slot_count"] = max(
            int(metrics["max_obstacle_slot_count"]), slot_count
        )
        if slot_count > 0:
            metrics["candidate_obstacle_slots_positive_count"] += 1


def _candidate_matrix_reduction(
    raw: Any,
    candidate_count: int,
    *,
    reduce_matrix: str,
    none_value: float | None,
) -> list[float | None]:
    if candidate_count <= 0:
        return []
    if raw is None or not isinstance(raw, list):
        return [none_value] * candidate_count
    values: list[float | None] = []
    for candidate_index in range(candidate_count):
        item = raw[candidate_index] if candidate_index < len(raw) else None
        values.append(_candidate_item_value(item, reduce_matrix, none_value))
    return values


def _candidate_scalar_list(
    raw: Any,
    candidate_count: int,
    *,
    integer: bool = False,
) -> list[float | int | None]:
    if candidate_count <= 0:
        return []
    if raw is None or not isinstance(raw, list):
        return [None] * candidate_count
    values: list[float | int | None] = []
    for candidate_index in range(candidate_count):
        item = raw[candidate_index] if candidate_index < len(raw) else None
        value = _as_finite_float(item)
        if value is None:
            values.append(None)
        elif integer:
            values.append(int(value))
        else:
            values.append(value)
    return values


def _candidate_item_value(
    raw: Any,
    reduce_matrix: str,
    none_value: float | None,
) -> float | None:
    if isinstance(raw, list):
        finite = [_as_finite_float(item) for item in raw]
        finite = [item for item in finite if item is not None]
        if not finite:
            return none_value
        if reduce_matrix == "min":
            return min(finite)
        if reduce_matrix == "mean":
            return sum(finite) / len(finite)
        if reduce_matrix == "max":
            return max(finite)
        raise ValueError(f"Unsupported matrix reduction: {reduce_matrix}")
    value = _as_finite_float(raw)
    return none_value if value is None else value


def _source_gate(
    scenario_support_report: dict[str, Any],
    route_geometry_report: dict[str, Any],
) -> dict[str, Any]:
    support_final = (
        scenario_support_report.get("final_decision")
        if isinstance(scenario_support_report, dict)
        else None
    )
    support_final = support_final if isinstance(support_final, dict) else {}
    route_analysis = (
        route_geometry_report.get("analysis")
        if isinstance(route_geometry_report, dict)
        else None
    )
    route_analysis = route_analysis if isinstance(route_analysis, dict) else {}
    routes = route_geometry_report.get("routes", [])
    tl_route_count = 0
    if isinstance(routes, list):
        for route in routes:
            geometry = route.get("geometry") if isinstance(route, dict) else None
            if isinstance(geometry, dict) and int(
                geometry.get("traffic_light_lanelet_count") or 0
            ) > 0:
                tl_route_count += 1
    return {
        "scenario_support_status": support_final.get("status"),
        "scenario_support_passed": support_final.get("passed"),
        "route_geometry_analysis": route_analysis.get("name"),
        "traffic_light_route_count": tl_route_count,
        "passed": (
            support_final.get("status") == SUPPORT_SOURCE_STATUS
            and support_final.get("passed") is False
            and route_analysis.get("name") == "dp_camp_route_scenario_inspection_v1"
            and tl_route_count > 0
        ),
    }


def _primary_gap(
    red_reasons: Counter[str],
    clearance_reasons: Counter[str],
    source_ready: bool,
) -> str:
    if not source_ready:
        return "source_gates_not_ready"
    red_top = _top_non_support_reason(red_reasons, "red_supported")
    clearance_top = _top_non_support_reason(clearance_reasons, "clearance_supported")
    return f"red={red_top};clearance={clearance_top}"


def _top_non_support_reason(counter: Counter[str], support_key: str) -> str:
    for reason, _ in counter.most_common():
        if reason != support_key:
            return reason
    return "support_present"


def _rank_red_examples(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        examples,
        key=lambda item: (
            item["red_distance_m"] is None,
            float("inf") if item["red_distance_m"] is None else item["red_distance_m"],
            -(
                -float("inf")
                if item["red_mean_alignment"] is None
                else item["red_mean_alignment"]
            ),
        ),
    )


def _rank_clearance_examples(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        examples,
        key=lambda item: (
            item["clearance_m"] is None,
            float("inf") if item["clearance_m"] is None else item["clearance_m"],
        ),
    )


def _path_seeds(path: Path) -> set[int]:
    return {int(match) for match in re.findall(r"seed[_-](\d+)", str(path))}


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


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _as_finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _finite_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _finite_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite_json(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
    return value


def _dict_block(payload: dict[str, Any]) -> str:
    return "\n".join(f"- `{key}`: `{_fmt(value)}`" for key, value in payload.items())


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
