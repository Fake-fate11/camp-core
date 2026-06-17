#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
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
)
from scripts.integrations.analyze_diffusion_planner_top1_preservation import (  # noqa: E402
    BOOL_OUTCOMES,
    TOL,
    _load_record,
    _log_context,
    _outcome_mask_vs_candidate0,
)
from scripts.integrations.analyze_diffusion_planner_top1_preserving_counterfactual import (  # noqa: E402
    _candidate_label_delta,
    _proxy_delta,
)
from scripts.integrations.analyze_diffusion_planner_top1_preserving_failure_attribution import (  # noqa: E402
    _outcome_oracle_failure_reasons,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
)


OUTCOME_PROGRESS_BUDGET_M = 0.05
DESCRIPTOR_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "progress_shortfall_p005",
        "field": "progress_shortfall",
        "direction": "lower",
        "budget": 0.05,
    },
    {
        "name": "route_progress_loss005",
        "field": "candidate_route_progress",
        "direction": "higher",
        "budget": 0.05,
    },
    {
        "name": "route_progress_loss010",
        "field": "candidate_route_progress",
        "direction": "higher",
        "budget": 0.10,
    },
    {
        "name": "step_reach_loss005",
        "field": "candidate_step_reach",
        "direction": "higher",
        "budget": 0.05,
    },
    {
        "name": "tracker_first_step_reach_loss005",
        "field": "candidate_perfect_tracker_first_step_reach_m",
        "direction": "higher",
        "budget": 0.05,
    },
    {
        "name": "target_speed_loss005",
        "field": "candidate_perfect_tracker_target_speed_mps",
        "direction": "higher",
        "budget": 0.05,
    },
    {
        "name": "h3_rollout_distance_loss005",
        "field": "rollout_h3_distance_m",
        "direction": "higher",
        "budget": 0.05,
    },
    {
        "name": "h5_rollout_distance_loss005",
        "field": "rollout_h5_distance_m",
        "direction": "higher",
        "budget": 0.05,
    },
    {
        "name": "h10_rollout_distance_loss005",
        "field": "rollout_h10_distance_m",
        "direction": "higher",
        "budget": 0.05,
    },
    {
        "name": "h10_rollout_distance_loss010",
        "field": "rollout_h10_distance_m",
        "direction": "higher",
        "budget": 0.10,
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline audit of current-tick progress proxy guards for a "
            "Top-1-preserving any-comfort certificate. Outcome labels are "
            "posterior evaluation only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--max_examples", type=int, default=20)
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
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        max_examples=args.max_examples,
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
    paths: list[Path],
    *,
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
    max_examples: int = 20,
) -> dict[str, Any]:
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)

    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw_record in enumerate(payload):
            record = _load_record(raw_record, f"{log_path} record {record_index}")
            record["descriptors"] = _load_descriptors(
                raw_record,
                int(record["candidate_count"]),
                f"{log_path} record {record_index}",
            )
            record["context"] = context
            record["selection_step"] = int(raw_record.get("selection_step", record_index))
            record["record_index"] = int(record_index)
            records.append(record)

    reports = [_descriptor_report(records, spec, max_examples=max_examples) for spec in DESCRIPTOR_SPECS]
    return {
        "analysis": {
            "name": "dp_camp_progress_proxy_guard_audit_v1",
            "label": label,
            "role": (
                "offline current-tick progress proxy guard audit before any "
                "Top-1-preserving online selector"
            ),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are posterior labels only",
            "classical_benders_claim": False,
            "outcome_progress_budget_m": OUTCOME_PROGRESS_BUDGET_M,
            "common_certificate": (
                "candidate0 feasible; nonzero base-feasible candidate; union-red, "
                "red-stopping, proxy jerk, and proxy lateral nonworse than "
                "candidate0; either proxy jerk or proxy lateral strictly improves; "
                "one progress descriptor loss is inside its declared budget"
            ),
            "descriptor_specs": list(DESCRIPTOR_SPECS),
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "math_boundary": (
                "Every descriptor is a fixed current-tick finite-candidate "
                "constant already logged in the artifact. Outcome labels evaluate "
                "posterior true/false/hidden status only and are not online "
                "selector inputs or Benders cut sources. If any descriptor is "
                "later atomized with fixed nonnegative scaling, CAMP scores can "
                "remain affine in the master variable."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": sum(int(record["feasible"].any()) for record in records),
            "fallback": sum(int(not record["feasible"].any()) for record in records),
            "candidate0_feasible": sum(
                int(record["feasible"].any() and bool(record["feasible"][0]))
                for record in records
            ),
        },
        "descriptors": reports,
    }


def _load_descriptors(
    raw_record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, np.ndarray | None]:
    descriptors: dict[str, np.ndarray | None] = {
        "progress_shortfall": None,
        "candidate_route_progress": _optional_vector(
            raw_record.get("candidate_route_progress"),
            candidate_count,
            f"{label} candidate_route_progress",
        ),
        "candidate_step_reach": _optional_vector(
            raw_record.get("candidate_step_reach"),
            candidate_count,
            f"{label} candidate_step_reach",
        ),
        "candidate_perfect_tracker_first_step_reach_m": _optional_vector(
            raw_record.get("candidate_perfect_tracker_first_step_reach_m"),
            candidate_count,
            f"{label} candidate_perfect_tracker_first_step_reach_m",
        ),
        "candidate_perfect_tracker_target_speed_mps": _optional_vector(
            raw_record.get("candidate_perfect_tracker_target_speed_mps"),
            candidate_count,
            f"{label} candidate_perfect_tracker_target_speed_mps",
        ),
    }
    rollout = raw_record.get("candidate_perfect_tracker_open_loop_rollout")
    for horizon in ("3", "5", "10"):
        field = f"rollout_h{horizon}_distance_m"
        descriptors[field] = None
        if not isinstance(rollout, dict):
            continue
        payload = rollout.get(horizon)
        if not isinstance(payload, dict):
            continue
        descriptors[field] = _optional_vector(
            payload.get("distance_m"),
            candidate_count,
            f"{label} rollout H{horizon} distance_m",
        )
    return descriptors


def _descriptor_report(
    records: list[dict[str, Any]],
    spec: dict[str, Any],
    *,
    max_examples: int,
) -> dict[str, Any]:
    events = [
        _event(record, spec)
        for record in records
        if record["feasible"].any() and bool(record["feasible"][0])
    ]
    available = [event for event in events if event["descriptor_available"]]
    overrides = [event for event in available if event["override"]]
    true_overrides = [event for event in overrides if event["true_override"]]
    false_overrides = [event for event in overrides if event["false_override"]]
    hidden = [event for event in available if event["hidden_outcome"]]
    return {
        "name": str(spec["name"]),
        "field": str(spec["field"]),
        "direction": str(spec["direction"]),
        "budget": float(spec["budget"]),
        "overall": _summary(events, available, overrides, true_overrides, false_overrides, hidden),
        "by_bucket": _bucket_report(available),
        "false_reason_counts": _counter(
            reason for event in false_overrides for reason in event["false_reasons"]
        ),
        "hidden_blocker_counts": _counter(
            blocker for event in hidden for blocker in event["hidden_blockers"]
        ),
        "examples": {
            "false_override": _examples(false_overrides, max_examples=max_examples, reverse=True),
            "hidden_outcome": _examples(hidden, max_examples=max_examples, reverse=False),
        },
    }


def _event(record: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    descriptor = _descriptor_values(record, spec)
    descriptor_available = descriptor is not None
    if descriptor is None:
        mask = np.zeros(int(record["candidate_count"]), dtype=bool)
        selected = 0
        descriptor_delta = np.zeros(int(record["candidate_count"]), dtype=np.float64)
    else:
        descriptor_delta = _descriptor_delta(descriptor, str(spec["direction"]))
        mask = _certificate_mask(record, descriptor_delta, float(spec["budget"]))
        selected = _select_candidate(record, mask, descriptor_delta)
    outcome_mask = _outcome_mask_vs_candidate0(record, OUTCOME_PROGRESS_BUDGET_M)
    override = selected != 0
    true_override = bool(override and outcome_mask[selected])
    false_override = bool(override and not true_override)
    hidden_outcome = bool((not override) and outcome_mask.any())
    best_hidden = _best_outcome_candidate(record, outcome_mask) if hidden_outcome else None
    return {
        "context": record["context"],
        "selection_step": int(record["selection_step"]),
        "record_index": int(record["record_index"]),
        "descriptor_available": descriptor_available,
        "descriptor_delta_selected": float(descriptor_delta[selected]) if descriptor_available else None,
        "selected": int(selected),
        "override": override,
        "true_override": true_override,
        "false_override": false_override,
        "hidden_outcome": hidden_outcome,
        "certificate_size": int(mask.sum()),
        "outcome_oracle_size": int(outcome_mask.sum()),
        "selected_candidate": _candidate_payload(record, selected),
        "false_reasons": (
            _outcome_oracle_failure_reasons(
                record,
                selected,
                OUTCOME_PROGRESS_BUDGET_M,
            )
            if false_override
            else []
        ),
        "best_hidden_candidate": (
            _candidate_payload(record, best_hidden) if best_hidden is not None else None
        ),
        "hidden_blockers": (
            _descriptor_blockers(record, best_hidden, descriptor_delta, spec)
            if best_hidden is not None and descriptor_available
            else []
        ),
    }


def _descriptor_values(record: dict[str, Any], spec: dict[str, Any]) -> np.ndarray | None:
    field = str(spec["field"])
    if field == "progress_shortfall":
        return np.asarray(record["progress_shortfall"], dtype=np.float64)
    value = record["descriptors"].get(field)
    if value is None:
        return None
    return np.asarray(value, dtype=np.float64)


def _descriptor_delta(values: np.ndarray, direction: str) -> np.ndarray:
    if direction == "lower":
        return values - values[0]
    if direction == "higher":
        return values[0] - values
    raise ValueError(f"Unsupported descriptor direction: {direction}")


def _certificate_mask(
    record: dict[str, Any],
    descriptor_delta: np.ndarray,
    budget: float,
) -> np.ndarray:
    mask = record["feasible"].copy()
    mask[0] = False
    mask &= descriptor_delta <= budget + TOL
    mask &= record["union_red"] <= record["union_red"][0] + TOL
    mask &= record["red_stopping"] <= record["red_stopping"][0] + TOL
    mask &= record["proxy_jerk"] <= record["proxy_jerk"][0] + TOL
    mask &= record["proxy_lateral"] <= record["proxy_lateral"][0] + TOL
    mask &= (
        (record["proxy_jerk"] < record["proxy_jerk"][0] - TOL)
        | (record["proxy_lateral"] < record["proxy_lateral"][0] - TOL)
    )
    return mask


def _select_candidate(
    record: dict[str, Any],
    mask: np.ndarray,
    descriptor_delta: np.ndarray,
) -> int:
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return 0
    order = np.lexsort(
        (
            indices,
            record["scores"][indices],
            descriptor_delta[indices],
            record["proxy_jerk"][indices],
            record["proxy_lateral"][indices],
            record["red_stopping"][indices],
            record["union_red"][indices],
        )
    )
    return int(indices[order[0]])


def _descriptor_blockers(
    record: dict[str, Any],
    candidate: int,
    descriptor_delta: np.ndarray,
    spec: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not bool(record["feasible"][candidate]):
        blockers.append("not_base_feasible")
    if descriptor_delta[candidate] > float(spec["budget"]) + TOL:
        blockers.append(f"{spec['name']}_exceeds_budget")
    if record["union_red"][candidate] > record["union_red"][0] + TOL:
        blockers.append("union_red_worse")
    if record["red_stopping"][candidate] > record["red_stopping"][0] + TOL:
        blockers.append("red_stopping_worse")
    if record["proxy_jerk"][candidate] > record["proxy_jerk"][0] + TOL:
        blockers.append("proxy_jerk_worse")
    if record["proxy_lateral"][candidate] > record["proxy_lateral"][0] + TOL:
        blockers.append("proxy_lateral_worse")
    if not (
        record["proxy_jerk"][candidate] < record["proxy_jerk"][0] - TOL
        or record["proxy_lateral"][candidate] < record["proxy_lateral"][0] - TOL
    ):
        blockers.append("no_strict_proxy_comfort_gain")
    return blockers or ["passes_certificate_but_not_selected"]


def _best_outcome_candidate(record: dict[str, Any], outcome_mask: np.ndarray) -> int:
    indices = np.flatnonzero(outcome_mask)
    if indices.size == 0:
        raise ValueError("best outcome candidate requested for empty mask.")
    cost = np.asarray(
        [
            _candidate_label_delta(record, int(index))["candidate_label_safety_delta"]
            for index in indices
        ],
        dtype=np.float64,
    )
    progress_loss = np.asarray(
        [
            _candidate_label_delta(record, int(index))["progress_loss_m"]
            for index in indices
        ],
        dtype=np.float64,
    )
    indices_arr = np.asarray(indices, dtype=np.int64)
    order = np.lexsort((indices_arr, progress_loss, cost))
    return int(indices[order[0]])


def _candidate_payload(record: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "candidate_index": int(index),
        "candidate_label_delta": _candidate_label_delta(record, index),
        "proxy_delta": _proxy_delta(record, index),
    }


def _summary(
    events: list[dict[str, Any]],
    available: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    true_overrides: list[dict[str, Any]],
    false_overrides: list[dict[str, Any]],
    hidden: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "candidate0_feasible_records": len(events),
        "descriptor_available_records": len(available),
        "override_records": len(overrides),
        "override_rate": len(overrides) / max(len(available), 1),
        "true_override_records": len(true_overrides),
        "true_override_rate_among_overrides": len(true_overrides) / max(len(overrides), 1),
        "false_override_records": len(false_overrides),
        "false_override_rate_among_overrides": len(false_overrides) / max(len(overrides), 1),
        "hidden_outcome_records": len(hidden),
        "hidden_outcome_rate": len(hidden) / max(len(available), 1),
        "override_summary": _candidate_collection_summary(overrides, selected=True),
        "false_summary": _candidate_collection_summary(false_overrides, selected=True),
        "hidden_summary": _candidate_collection_summary(hidden, selected=False),
        "hard_gate_bool_worse_records": {
            field: sum(
                int(
                    event["selected_candidate"]["candidate_label_delta"]["bool_delta"][field]
                    > 0
                )
                for event in overrides
            )
            for field in BOOL_OUTCOMES
        },
    }


def _candidate_collection_summary(
    events: list[dict[str, Any]],
    *,
    selected: bool,
) -> dict[str, Any]:
    key = "selected_candidate" if selected else "best_hidden_candidate"
    candidates = [event[key] for event in events if event.get(key) is not None]
    return {
        "candidate_label_safety_delta": _stats(
            [
                candidate["candidate_label_delta"]["candidate_label_safety_delta"]
                for candidate in candidates
            ]
        ),
        "outcome_progress_delta_m": _stats(
            [candidate["candidate_label_delta"]["progress_m"] for candidate in candidates]
        ),
        "outcome_jerk_delta_mps3": _stats(
            [
                candidate["candidate_label_delta"]["mean_jerk_mps3"]
                for candidate in candidates
            ]
        ),
        "outcome_lateral_delta_mps2": _stats(
            [
                candidate["candidate_label_delta"]["mean_lateral_acceleration_mps2"]
                for candidate in candidates
            ]
        ),
        "proxy_delta": {
            field: _stats([candidate["proxy_delta"][field] for candidate in candidates])
            for field in (
                "progress_shortfall",
                "proxy_jerk",
                "proxy_lateral",
                "union_red",
                "red_stopping",
                "selection_score",
            )
        },
    }


def _bucket_report(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        buckets = event["context"].get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            if bucket not in SUPPORTED_SCENARIO_BUCKETS:
                raise ValueError(f"Unsupported scenario bucket: {bucket}")
            grouped[str(bucket)].append(event)
    rows = []
    for bucket in _ordered_buckets(grouped):
        group = grouped[bucket]
        overrides = [event for event in group if event["override"]]
        false = [event for event in group if event["false_override"]]
        hidden = [event for event in group if event["hidden_outcome"]]
        rows.append(
            {
                "bucket": bucket,
                "records": len(group),
                "override_records": len(overrides),
                "false_override_records": len(false),
                "hidden_outcome_records": len(hidden),
                "override_safety_mean": _stats(
                    [
                        event["selected_candidate"]["candidate_label_delta"][
                            "candidate_label_safety_delta"
                        ]
                        for event in overrides
                    ]
                )["mean"],
                "hidden_safety_mean": _stats(
                    [
                        event["best_hidden_candidate"]["candidate_label_delta"][
                            "candidate_label_safety_delta"
                        ]
                        for event in hidden
                        if event["best_hidden_candidate"] is not None
                    ]
                )["mean"],
            }
        )
    return rows


def _ordered_buckets(grouped: dict[str, list[dict[str, Any]]]) -> list[str]:
    order = [
        "overall",
        "normal",
        "traffic_light",
        "red_light_turn",
        "sharp_turn",
        "npc_interaction",
        "dense_scene",
        "lane_change_or_merge",
    ]
    return [bucket for bucket in order if bucket in grouped] + sorted(
        bucket for bucket in grouped if bucket not in order
    )


def _examples(
    events: list[dict[str, Any]],
    *,
    max_examples: int,
    reverse: bool,
) -> list[dict[str, Any]]:
    if max_examples <= 0:
        return []
    events = sorted(events, key=_event_cost_sort_key, reverse=reverse)
    examples = []
    for event in events[:max_examples]:
        context = event["context"]
        examples.append(
            {
                "route_name": context["route_name"],
                "scenario_buckets": context["scenario_buckets"],
                "seed": context["seed"],
                "max_npcs": context["max_npcs"],
                "traffic_lights": context["traffic_lights"],
                "selection_step": event["selection_step"],
                "selected": event["selected"],
                "certificate_size": event["certificate_size"],
                "outcome_oracle_size": event["outcome_oracle_size"],
                "descriptor_delta_selected": event["descriptor_delta_selected"],
                "selected_candidate": event["selected_candidate"],
                "false_reasons": event["false_reasons"],
                "best_hidden_candidate": event["best_hidden_candidate"],
                "hidden_blockers": event["hidden_blockers"],
                "run_key": context["run_key"],
                "log_path": context["log_path"],
            }
        )
    return examples


def _event_cost_sort_key(event: dict[str, Any]) -> tuple[float, int]:
    candidate = event["selected_candidate"]
    cost = candidate["candidate_label_delta"]["candidate_label_safety_delta"]
    return (float(cost), int(event["selection_step"]))


def _optional_vector(values: Any, size: int, label: str) -> np.ndarray | None:
    if values is None:
        return None
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}].")
    if not np.all(np.isfinite(vector)):
        raise ValueError(f"{label} must be finite.")
    return vector


def _counter(values) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "p50": None, "p90": None, "cvar90": None}
    arr = np.asarray(values, dtype=np.float64)
    threshold = float(np.percentile(arr, 90.0))
    tail = arr[arr >= threshold]
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": threshold,
        "cvar90": float(np.mean(tail)) if tail.size else threshold,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Progress Proxy Guard Audit",
        "",
        "This is an offline audit. It swaps only the current-tick progress guard "
        "inside the rejected any-comfort certificate.",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Descriptor Results",
        "",
        "| Descriptor | Available | Override | True | False | Hidden | "
        "Mean override safety | CVaR90 override safety |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["descriptors"]:
        overall = row["overall"]
        safety = overall["override_summary"]["candidate_label_safety_delta"]
        lines.append(
            f"| `{row['name']}` | "
            f"{overall['descriptor_available_records']} | "
            f"{overall['override_records']} | "
            f"{overall['true_override_records']} | "
            f"{overall['false_override_records']} | "
            f"{overall['hidden_outcome_records']} | "
            f"{_fmt(safety['mean'])} | {_fmt(safety['cvar90'])} |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


if __name__ == "__main__":
    main()
