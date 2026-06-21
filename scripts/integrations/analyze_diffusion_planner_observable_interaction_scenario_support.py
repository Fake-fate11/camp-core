#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
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
from scripts.integrations.analyze_diffusion_planner_observable_interaction_coverage_smoke import (  # noqa: E402
    NEXT_WORK_REJECT as SOURCE_NEXT_WORK,
    REJECT_STATUS as SOURCE_REJECT_STATUS,
)


PAYLOAD_KEY = "observable_state_logging"
FORMAL_SEEDS = frozenset({11, 12, 13})
FOUND_STATUS = "observable_interaction_scenario_support_found"
BOTTLENECK_STATUS = "observable_interaction_scenario_support_bottleneck_recorded"
SOURCE_BLOCKED_STATUS = "observable_interaction_scenario_support_source_not_rejected"
NEXT_WORK_PLAN = "predeclare_smaller_observable_interaction_coverage_inventory_only"
NEXT_WORK_BOTTLENECK = (
    "reject_observable_interaction_coverage_or_inspect_map_geometry_before_replay"
)
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
            "Read-only scenario-support audit for rejected observable-interaction "
            "coverage. It scans existing current-tick observable payloads for "
            "red-aligned stopline and near-obstacle clearance support, without "
            "running Diffusion Planner or using closed-loop outcome labels."
        )
    )
    parser.add_argument("--source_smoke_json", type=Path, required=True)
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--red_distance_budget_m", type=float, default=5.0)
    parser.add_argument("--clearance_budget_m", type=float, default=2.0)
    parser.add_argument("--max_examples", type=int, default=10)
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
        source_smoke_report=_read_json(args.source_smoke_json),
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
    source_smoke_report: dict[str, Any],
    label: str | None = None,
    red_distance_budget_m: float = 5.0,
    clearance_budget_m: float = 2.0,
    max_examples: int = 10,
) -> dict[str, Any]:
    source = _source_gate(source_smoke_report)
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No camp_selection_log.json files were found.")

    scanned_logs = 0
    excluded_formal_logs = 0
    total_records = 0
    candidate_payload_records = 0
    baseline_disabled_records = 0
    payload_candidates = 0
    formal_seed_records = 0
    log_reports: list[dict[str, Any]] = []
    red_examples: list[dict[str, Any]] = []
    clearance_examples: list[dict[str, Any]] = []

    for log_path in log_paths:
        path_seeds = sorted(_path_seeds(log_path))
        if any(seed in FORMAL_SEEDS for seed in path_seeds):
            excluded_formal_logs += 1
            continue
        scanned_logs += 1
        rows = _read_selection_rows(log_path)
        log_report = {
            "log_path": str(log_path),
            "records": len(rows),
            "candidate_payload_records": 0,
            "baseline_disabled_records": 0,
            "red_context_records": 0,
            "clearance_context_records": 0,
            "min_red_distance_m": math.inf,
            "max_red_alignment": -math.inf,
            "min_clearance_m": math.inf,
        }
        for record_index, record in enumerate(rows):
            total_records += 1
            payload = record.get(PAYLOAD_KEY) if isinstance(record, dict) else None
            if payload is None:
                baseline_disabled_records += 1
                log_report["baseline_disabled_records"] += 1
                continue
            if not isinstance(payload, dict):
                continue
            candidate_payload_records += 1
            log_report["candidate_payload_records"] += 1
            formal_seed_records += int(any(seed in FORMAL_SEEDS for seed in path_seeds))
            contexts = _candidate_contexts(
                payload,
                log_path=log_path,
                record_index=record_index,
                red_distance_budget_m=red_distance_budget_m,
                clearance_budget_m=clearance_budget_m,
            )
            payload_candidates += len(contexts)
            if any(item["red_risk"] > 0.0 for item in contexts):
                log_report["red_context_records"] += 1
            if any(item["clearance_deficit"] > 0.0 for item in contexts):
                log_report["clearance_context_records"] += 1
            for item in contexts:
                log_report["min_red_distance_m"] = min(
                    log_report["min_red_distance_m"], item["red_distance_m"]
                )
                log_report["max_red_alignment"] = max(
                    log_report["max_red_alignment"], item["red_alignment"]
                )
                log_report["min_clearance_m"] = min(
                    log_report["min_clearance_m"], item["clearance_m"]
                )
                if item["red_risk"] > 0.0:
                    red_examples.append(item)
                if item["clearance_deficit"] > 0.0:
                    clearance_examples.append(item)
        log_reports.append(_finite_json(log_report))

    red_examples = sorted(red_examples, key=lambda item: item["red_risk"], reverse=True)
    clearance_examples = sorted(
        clearance_examples, key=lambda item: item["clearance_deficit"], reverse=True
    )
    support = {
        "red_context_supported": bool(red_examples),
        "clearance_context_supported": bool(clearance_examples),
        "red_context_candidate_count": len(red_examples),
        "clearance_context_candidate_count": len(clearance_examples),
        "red_context_record_count": _distinct_record_count(red_examples),
        "clearance_context_record_count": _distinct_record_count(clearance_examples),
        "min_red_distance_m": _finite_min(log_reports, "min_red_distance_m"),
        "max_red_alignment": _finite_max(log_reports, "max_red_alignment"),
        "min_clearance_m": _finite_min(log_reports, "min_clearance_m"),
    }
    source_passed = bool(source["passed"])
    found = (
        source_passed
        and support["red_context_supported"]
        and support["clearance_context_supported"]
    )
    status = (
        FOUND_STATUS
        if found
        else BOTTLENECK_STATUS
        if source_passed
        else SOURCE_BLOCKED_STATUS
    )
    final = {
        "status": status,
        "passed": found,
        "primary_gap": _primary_gap(source_passed, support),
        "authorized_next_work": (
            NEXT_WORK_PLAN
            if found
            else NEXT_WORK_BOTTLENECK
            if source_passed
            else "fix_or_run_rejected_coverage_smoke_before_support_audit"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_scenario_support_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "closed_loop_outcome_labels_used": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "formal_seed_policy": "exclude_path_seed_11_12_13",
            "math_boundary": (
                "This audit scans existing current-tick finite-candidate "
                "observable payloads only. Red and clearance support are "
                "diagnostic state coefficients, not selector thresholds, "
                "outcome labels, atom weights, or trajectory-space convexity "
                "claims. If later atomized, they must enter CAMP as fixed "
                "candidate coefficients preserving affine score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 convex master. No DP-side classical "
                "Benders master/subproblem, dual, or cut is constructed."
            ),
        },
        "source_gate": source,
        "budgets": {
            "red_distance_budget_m": float(red_distance_budget_m),
            "clearance_budget_m": float(clearance_budget_m),
        },
        "counts": {
            "input_log_paths": len(log_paths),
            "scanned_logs": scanned_logs,
            "excluded_formal_seed_logs": excluded_formal_logs,
            "records": total_records,
            "candidate_payload_records": candidate_payload_records,
            "baseline_disabled_records": baseline_disabled_records,
            "payload_candidates": payload_candidates,
            "formal_seed_records": formal_seed_records,
        },
        "support": _finite_json(support),
        "top_red_context_examples": [
            _finite_json(item) for item in red_examples[:max(0, max_examples)]
        ],
        "top_clearance_context_examples": [
            _finite_json(item) for item in clearance_examples[:max(0, max_examples)]
        ],
        "log_summaries": log_reports,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["counts"]
    support = report["support"]
    lines = [
        "# Observable Interaction Scenario Support Audit",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Counts",
        "",
        f"- scanned logs: `{counts['scanned_logs']}`",
        f"- excluded formal-seed logs: `{counts['excluded_formal_seed_logs']}`",
        f"- records: `{counts['records']}`",
        f"- candidate payload records: `{counts['candidate_payload_records']}`",
        f"- payload candidates: `{counts['payload_candidates']}`",
        "",
        "## Support",
        "",
        f"- red context supported: `{support['red_context_supported']}`",
        f"- clearance context supported: `{support['clearance_context_supported']}`",
        f"- red context candidates: `{support['red_context_candidate_count']}`",
        f"- clearance context candidates: `{support['clearance_context_candidate_count']}`",
        f"- min red distance m: `{_fmt(support['min_red_distance_m'])}`",
        f"- max red alignment: `{_fmt(support['max_red_alignment'])}`",
        f"- min clearance m: `{_fmt(support['min_clearance_m'])}`",
        "",
        "## Top Red Examples",
        "",
        *_example_table(report["top_red_context_examples"], "red_risk"),
        "",
        "## Top Clearance Examples",
        "",
        *_example_table(report["top_clearance_context_examples"], "clearance_deficit"),
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
    red_distance = _candidate_vector(
        payload.get("candidate_red_stopline_distance_m"),
        candidate_count,
        reduce_matrix="min",
        none_value=math.inf,
    )
    red_alignment = _candidate_vector(
        payload.get("candidate_red_heading_alignment"),
        candidate_count,
        reduce_matrix="mean",
        none_value=0.0,
    )
    clearance = _candidate_vector(
        payload.get("candidate_min_obstacle_clearance_lower_bound_m"),
        candidate_count,
        reduce_matrix="min",
        none_value=math.inf,
    )
    contexts = []
    for candidate_index in range(candidate_count):
        distance = red_distance[candidate_index]
        alignment = red_alignment[candidate_index]
        min_clearance = clearance[candidate_index]
        red_risk = max(alignment, 0.0) * max(red_distance_budget_m - distance, 0.0)
        clearance_deficit = max(clearance_budget_m - min_clearance, 0.0)
        contexts.append(
            {
                "log_path": str(log_path),
                "record_index": record_index,
                "candidate_index": candidate_index,
                "red_distance_m": distance,
                "red_alignment": alignment,
                "red_risk": red_risk,
                "clearance_m": min_clearance,
                "clearance_deficit": clearance_deficit,
            }
        )
    return contexts


def _candidate_vector(
    raw: Any,
    candidate_count: int,
    *,
    reduce_matrix: str,
    none_value: float,
) -> list[float]:
    if candidate_count <= 0:
        return []
    if raw is None:
        return [none_value] * candidate_count
    if not isinstance(raw, list):
        return [none_value] * candidate_count
    values: list[float] = []
    for candidate_index in range(candidate_count):
        item = raw[candidate_index] if candidate_index < len(raw) else None
        values.append(_candidate_item_value(item, reduce_matrix, none_value))
    return values


def _candidate_item_value(raw: Any, reduce_matrix: str, none_value: float) -> float:
    if isinstance(raw, list):
        finite = [_as_finite_float(item) for item in raw]
        finite = [item for item in finite if item is not None]
        if not finite:
            return none_value
        if reduce_matrix == "min":
            return min(finite)
        if reduce_matrix == "mean":
            return sum(finite) / len(finite)
        raise ValueError(f"Unsupported matrix reduction: {reduce_matrix}")
    value = _as_finite_float(raw)
    return none_value if value is None else value


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") if isinstance(report, dict) else None
    final = final if isinstance(final, dict) else {}
    return {
        "expected_status": SOURCE_REJECT_STATUS,
        "actual_status": final.get("status"),
        "expected_authorized_next_work": SOURCE_NEXT_WORK,
        "actual_authorized_next_work": final.get("authorized_next_work"),
        "passed": (
            final.get("status") == SOURCE_REJECT_STATUS
            and final.get("passed") is False
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and final.get("offline_separability_authorized") is False
            and final.get("CAMP_retraining_authorized") is False
            and final.get("Full36_authorized") is False
        ),
    }


def _primary_gap(source_passed: bool, support: dict[str, Any]) -> str | None:
    if not source_passed:
        return "source_smoke_gate_not_rejected_as_expected"
    missing = []
    if not support["red_context_supported"]:
        missing.append("red_context_support_absent")
    if not support["clearance_context_supported"]:
        missing.append("clearance_context_support_absent")
    return ",".join(missing) if missing else None


def _distinct_record_count(examples: list[dict[str, Any]]) -> int:
    return len({(item["log_path"], item["record_index"]) for item in examples})


def _finite_min(items: list[dict[str, Any]], key: str) -> float | None:
    values = [item.get(key) for item in items]
    finite = [float(value) for value in values if _is_finite_number(value)]
    return min(finite) if finite else None


def _finite_max(items: list[dict[str, Any]], key: str) -> float | None:
    values = [item.get(key) for item in items]
    finite = [float(value) for value in values if _is_finite_number(value)]
    return max(finite) if finite else None


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


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _finite_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _finite_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite_json(item) for item in value]
    if isinstance(value, float):
        if math.isinf(value):
            return None
        if math.isnan(value):
            return None
    return value


def _example_table(examples: list[dict[str, Any]], score_key: str) -> list[str]:
    if not examples:
        return ["No examples found."]
    lines = [
        "| score | log | record | candidate | red distance | red alignment | clearance |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in examples:
        lines.append(
            "| "
            f"{_fmt(item[score_key])} | "
            f"`{item['log_path']}` | "
            f"{item['record_index']} | "
            f"{item['candidate_index']} | "
            f"{_fmt(item['red_distance_m'])} | "
            f"{_fmt(item['red_alignment'])} | "
            f"{_fmt(item['clearance_m'])} |"
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
