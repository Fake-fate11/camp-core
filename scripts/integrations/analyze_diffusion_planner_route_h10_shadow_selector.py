#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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
from scripts.integrations.analyze_diffusion_planner_hidden_visibility import (  # noqa: E402
    BASE_PROGRESS_DELTA_MAX,
    BASE_PROGRESS_DELTA_MIN,
    OUTCOME_PROGRESS_BUDGET_M,
    _base_mask,
    _candidate_payload,
    _screen_mask,
    _select_candidate,
)
from scripts.integrations.analyze_diffusion_planner_progress_proxy_guard import (  # noqa: E402
    _fmt,
    _load_descriptors,
    _stats,
)
from scripts.integrations.analyze_diffusion_planner_top1_preservation import (  # noqa: E402
    BOOL_OUTCOMES,
    _load_record,
    _log_context,
    _outcome_mask_vs_candidate0,
)
from scripts.integrations.analyze_diffusion_planner_top1_preserving_failure_attribution import (  # noqa: E402
    _outcome_oracle_failure_reasons,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
)


DEFAULT_PROGRESS_DELTA_MIN_M = -2.0
DEFAULT_PROGRESS_DELTA_MAX_M = 0.05
DEFAULT_ROUTE_PROGRESS_LOSS_MAX_M = 0.0
DEFAULT_H10_DISTANCE_LOSS_MIN_M = -0.15
DEFAULT_SCORE_DELTA_MAX = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline route-progress plus H10 lower-bound shadow selector audit. "
            "Selection uses only current-tick finite candidate diagnostics; "
            "candidate outcomes are posterior labels for evaluation only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--max_examples", type=int, default=20)
    parser.add_argument(
        "--progress_delta_min_m",
        type=float,
        default=DEFAULT_PROGRESS_DELTA_MIN_M,
    )
    parser.add_argument(
        "--progress_delta_max_m",
        type=float,
        default=DEFAULT_PROGRESS_DELTA_MAX_M,
    )
    parser.add_argument(
        "--route_progress_loss_max_m",
        type=float,
        default=DEFAULT_ROUTE_PROGRESS_LOSS_MAX_M,
    )
    parser.add_argument(
        "--h10_distance_loss_min_m",
        type=float,
        default=DEFAULT_H10_DISTANCE_LOSS_MIN_M,
    )
    parser.add_argument("--score_delta_max", type=float, default=DEFAULT_SCORE_DELTA_MAX)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        max_examples=args.max_examples,
        progress_delta_min_m=args.progress_delta_min_m,
        progress_delta_max_m=args.progress_delta_max_m,
        route_progress_loss_max_m=args.route_progress_loss_max_m,
        h10_distance_loss_min_m=args.h10_distance_loss_min_m,
        score_delta_max=args.score_delta_max,
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
    progress_delta_min_m: float = DEFAULT_PROGRESS_DELTA_MIN_M,
    progress_delta_max_m: float = DEFAULT_PROGRESS_DELTA_MAX_M,
    route_progress_loss_max_m: float = DEFAULT_ROUTE_PROGRESS_LOSS_MAX_M,
    h10_distance_loss_min_m: float = DEFAULT_H10_DISTANCE_LOSS_MIN_M,
    score_delta_max: float = DEFAULT_SCORE_DELTA_MAX,
) -> dict[str, Any]:
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    rule = _rule_spec(
        progress_delta_min_m=progress_delta_min_m,
        progress_delta_max_m=progress_delta_max_m,
        route_progress_loss_max_m=route_progress_loss_max_m,
        h10_distance_loss_min_m=h10_distance_loss_min_m,
        score_delta_max=score_delta_max,
    )

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

    events = [_event(record, rule) for record in records]
    candidate0_events = [event for event in events if event["candidate0_feasible"]]

    return {
        "analysis": {
            "name": "dp_camp_route_h10_shadow_selector_audit_v1",
            "label": label,
            "role": (
                "default-off offline audit for a finite-candidate CAMP risk "
                "selector proposal"
            ),
            "training": False,
            "online_selector_change": False,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "classical_benders_claim": False,
            "outcome_progress_budget_m": OUTCOME_PROGRESS_BUDGET_M,
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "rule": rule,
            "base_rule": {
                "name": "banded_shortfall_m010_p005",
                "progress_delta_min": BASE_PROGRESS_DELTA_MIN,
                "progress_delta_max": BASE_PROGRESS_DELTA_MAX,
            },
            "math_boundary": (
                "The audited selector operates on a fixed finite candidate set. "
                "Its inputs are current-tick constants already logged with the "
                "candidate set: feasibility, CAMP affine scores, proxy red costs, "
                "proxy comfort costs, candidate_route_progress, and H10 open-loop "
                "distance. Candidate outcomes are posterior labels used only for "
                "offline true/false attribution. If route-progress or H10 guards "
                "are atomized later, use fixed nonnegative hinge transforms; the "
                "CAMP score remains affine in master weights and the simplex/CVaR/"
                "L2 master remains convex. This audit does not claim DP, SG, "
                "postprocess, PerfectTracker, closed-loop futures, SafetyCost, or "
                "trajectory coordinates are Benders subproblems or cut sources."
            ),
        },
        "records": _record_summary(events, len(log_paths)),
        "stage_counts": _counter(event["stage"] for event in events),
        "candidate0_feasible_stage_counts": _counter(
            event["stage"] for event in candidate0_events
        ),
        "shadow_vs_candidate0": _comparison_summary(
            candidate0_events,
            index_key="selected",
            payload_key="selected_candidate",
        ),
        "logged_vs_candidate0": _comparison_summary(
            candidate0_events,
            index_key="logged_selected",
            payload_key="logged_candidate",
        ),
        "shadow_vs_logged": _shadow_vs_logged_summary(candidate0_events),
        "by_stage": _stage_report(candidate0_events),
        "by_bucket": _bucket_report(candidate0_events),
        "examples": _examples(candidate0_events, max_examples=max_examples),
    }


def _rule_spec(
    *,
    progress_delta_min_m: float,
    progress_delta_max_m: float,
    route_progress_loss_max_m: float,
    h10_distance_loss_min_m: float,
    score_delta_max: float,
) -> dict[str, Any]:
    return {
        "name": "base_then_route_nonworse_h10_lower_m015_score0",
        "description": (
            "Apply the existing protected base band first. If it is empty, allow "
            "a lower-band escape only when route progress is nonworse than "
            "candidate0, H10 distance is not more than 0.15 m ahead of "
            "candidate0 by default, and the original CAMP affine score is "
            "nonworse. Empty masks retain candidate0."
        ),
        "progress_delta_min": float(progress_delta_min_m),
        "progress_delta_max": float(progress_delta_max_m),
        "filters": (
            {"field": "route_progress_loss", "max": float(route_progress_loss_max_m)},
            {"field": "h10_distance_loss", "min": float(h10_distance_loss_min_m)},
            {"field": "score_delta", "max": float(score_delta_max)},
        ),
        "fail_closed": (
            "all-infeasible and candidate0-infeasible records retain the logged "
            "selector result; candidate0-feasible records retain candidate0 when "
            "base and route-H10 masks are empty or required descriptors are missing"
        ),
    }


def _event(record: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    logged_selected = int(record["selected_index"])
    feasible = record["feasible"]
    selected = logged_selected
    stage = "all_infeasible_retain_logged"
    mask = np.zeros(int(record["candidate_count"]), dtype=bool)
    descriptor_missing = False

    if feasible.any() and bool(feasible[0]):
        base_mask = _base_mask(record)
        if base_mask.any():
            selected = _select_candidate(record, base_mask)
            stage = "base"
            mask = base_mask
        else:
            route_mask, descriptor_missing = _screen_mask(record, rule)
            if route_mask.any():
                selected = _select_candidate(record, route_mask)
                stage = "route_h10_escape"
                mask = route_mask
            else:
                selected = 0
                stage = (
                    "candidate0_retain_descriptor_missing"
                    if descriptor_missing
                    else "candidate0_retain_empty_mask"
                )
                mask = route_mask
    elif feasible.any():
        stage = "candidate0_infeasible_retain_logged"

    candidate0_feasible = bool(feasible.any() and bool(feasible[0]))
    outcome_mask = (
        _outcome_mask_vs_candidate0(record, OUTCOME_PROGRESS_BUDGET_M)
        if candidate0_feasible
        else np.zeros(int(record["candidate_count"]), dtype=bool)
    )
    false_override = bool(candidate0_feasible and selected != 0 and not outcome_mask[selected])
    logged_false_override = bool(
        candidate0_feasible
        and logged_selected != 0
        and not outcome_mask[logged_selected]
    )
    return {
        "context": record["context"],
        "selection_step": int(record["selection_step"]),
        "record_index": int(record["record_index"]),
        "candidate0_feasible": candidate0_feasible,
        "stage": stage,
        "selected": int(selected),
        "logged_selected": logged_selected,
        "changed_from_candidate0": bool(candidate0_feasible and selected != 0),
        "changed_from_logged": bool(selected != logged_selected),
        "descriptor_missing": bool(descriptor_missing),
        "certificate_size": int(mask.sum()),
        "outcome_oracle_size": int(outcome_mask.sum()),
        "selected_candidate": (
            _candidate_payload(record, int(selected)) if candidate0_feasible else None
        ),
        "logged_candidate": (
            _candidate_payload(record, logged_selected) if candidate0_feasible else None
        ),
        "true_override": bool(candidate0_feasible and selected != 0 and outcome_mask[selected]),
        "false_override": false_override,
        "false_reasons": (
            _outcome_oracle_failure_reasons(
                record,
                int(selected),
                OUTCOME_PROGRESS_BUDGET_M,
            )
            if false_override
            else []
        ),
        "logged_true_override": bool(
            candidate0_feasible and logged_selected != 0 and outcome_mask[logged_selected]
        ),
        "logged_false_override": logged_false_override,
        "logged_false_reasons": (
            _outcome_oracle_failure_reasons(
                record,
                logged_selected,
                OUTCOME_PROGRESS_BUDGET_M,
            )
            if logged_false_override
            else []
        ),
    }


def _record_summary(events: list[dict[str, Any]], logs: int) -> dict[str, Any]:
    return {
        "logs": logs,
        "total": len(events),
        "nonfallback": sum(
            int(event["stage"] != "all_infeasible_retain_logged") for event in events
        ),
        "fallback": sum(
            int(event["stage"] == "all_infeasible_retain_logged") for event in events
        ),
        "candidate0_feasible": sum(int(event["candidate0_feasible"]) for event in events),
        "candidate0_infeasible": sum(
            int(event["stage"] == "candidate0_infeasible_retain_logged")
            for event in events
        ),
        "descriptor_missing_when_escape_needed": sum(
            int(event["descriptor_missing"]) for event in events
        ),
    }


def _comparison_summary(
    events: list[dict[str, Any]],
    *,
    index_key: str,
    payload_key: str,
) -> dict[str, Any]:
    overrides = [event for event in events if int(event[index_key]) != 0]
    true_overrides = [
        event for event in overrides if bool(event[f"{_prefix(index_key)}true_override"])
    ]
    false_overrides = [
        event for event in overrides if bool(event[f"{_prefix(index_key)}false_override"])
    ]
    deltas = [event[payload_key]["candidate_label_delta"] for event in overrides]
    return {
        "candidate0_feasible_records": len(events),
        "override_records": len(overrides),
        "true_override_records": len(true_overrides),
        "false_override_records": len(false_overrides),
        "true_override_rate_among_overrides": len(true_overrides) / max(len(overrides), 1),
        "false_override_rate_among_overrides": len(false_overrides) / max(len(overrides), 1),
        "candidate_label_safety_delta": _stats(
            [delta["candidate_label_safety_delta"] for delta in deltas]
        ),
        "progress_delta_m": _stats([delta["progress_m"] for delta in deltas]),
        "jerk_delta_mps3": _stats([delta["mean_jerk_mps3"] for delta in deltas]),
        "lateral_delta_mps2": _stats(
            [delta["mean_lateral_acceleration_mps2"] for delta in deltas]
        ),
        "hard_gate_bool_worse_records": _bool_worse_summary(deltas),
        "false_reason_counts": _counter(
            reason
            for event in false_overrides
            for reason in event[f"{_prefix(index_key)}false_reasons"]
        ),
    }


def _prefix(index_key: str) -> str:
    return "logged_" if index_key == "logged_selected" else ""


def _shadow_vs_logged_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    changed = [event for event in events if event["changed_from_logged"]]
    return {
        "candidate0_feasible_records": len(events),
        "different_records": len(changed),
        "same_records": len(events) - len(changed),
        "different_by_shadow_stage": _counter(event["stage"] for event in changed),
        "shadow_removes_logged_override_records": sum(
            int(event["logged_selected"] != 0 and event["selected"] == 0)
            for event in changed
        ),
        "shadow_adds_override_records": sum(
            int(event["logged_selected"] == 0 and event["selected"] != 0)
            for event in changed
        ),
    }


def _stage_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    stages = sorted({str(event["stage"]) for event in events})
    return {
        stage: _stage_summary(
            [event for event in events if event["stage"] == stage]
        )
        for stage in stages
    }


def _stage_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    overrides = [event for event in events if event["selected"] != 0]
    true_overrides = [event for event in overrides if event["true_override"]]
    false_overrides = [event for event in overrides if event["false_override"]]
    deltas = [
        event["selected_candidate"]["candidate_label_delta"]
        for event in overrides
    ]
    return {
        "records": len(events),
        "override_records": len(overrides),
        "true_override_records": len(true_overrides),
        "false_override_records": len(false_overrides),
        "candidate_label_safety_delta": _stats(
            [delta["candidate_label_safety_delta"] for delta in deltas]
        ),
        "hard_gate_bool_worse_records": _bool_worse_summary(deltas),
        "false_reason_counts": _counter(
            reason for event in false_overrides for reason in event["false_reasons"]
        ),
    }


def _bucket_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {"overall": _bucket_summary(events)}
    for bucket in SUPPORTED_SCENARIO_BUCKETS:
        bucket_events = [
            event
            for event in events
            if bucket in event["context"].get("scenario_buckets", ())
        ]
        report[str(bucket)] = _bucket_summary(bucket_events)
    return report


def _bucket_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    overrides = [event for event in events if event["selected"] != 0]
    false_overrides = [event for event in overrides if event["false_override"]]
    return {
        "records": len(events),
        "shadow_override_records": len(overrides),
        "route_h10_escape_records": sum(
            int(event["stage"] == "route_h10_escape") for event in events
        ),
        "false_override_records": len(false_overrides),
        "hard_gate_bool_worse_records": _bool_worse_summary(
            [event["selected_candidate"]["candidate_label_delta"] for event in overrides]
        ),
    }


def _examples(events: list[dict[str, Any]], *, max_examples: int) -> dict[str, Any]:
    return {
        "route_h10_escape": _event_examples(
            [event for event in events if event["stage"] == "route_h10_escape"],
            max_examples=max_examples,
        ),
        "false_override": _event_examples(
            [event for event in events if event["false_override"]],
            max_examples=max_examples,
        ),
        "changed_from_logged": _event_examples(
            [event for event in events if event["changed_from_logged"]],
            max_examples=max_examples,
        ),
    }


def _event_examples(events: list[dict[str, Any]], *, max_examples: int) -> list[dict[str, Any]]:
    rows = []
    for event in events[:max_examples]:
        rows.append(
            {
                "run_key": event["context"].get("run_key"),
                "route_name": event["context"].get("route_name"),
                "seed": event["context"].get("seed"),
                "max_npcs": event["context"].get("max_npcs"),
                "traffic_lights": event["context"].get("traffic_lights"),
                "scenario_buckets": event["context"].get("scenario_buckets", []),
                "selection_step": event["selection_step"],
                "record_index": event["record_index"],
                "stage": event["stage"],
                "selected": event["selected"],
                "logged_selected": event["logged_selected"],
                "certificate_size": event["certificate_size"],
                "selected_candidate": event["selected_candidate"],
                "logged_candidate": event["logged_candidate"],
                "false_reasons": event["false_reasons"],
                "logged_false_reasons": event["logged_false_reasons"],
            }
        )
    return rows


def _bool_worse_summary(deltas: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for delta in deltas:
        bool_delta = delta.get("bool_delta", {})
        for field in BOOL_OUTCOMES:
            counts[field] += int(int(bool_delta.get(field, 0)) > 0)
    return dict(sorted(counts.items()))


def _counter(values) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def render_markdown(report: dict[str, Any]) -> str:
    shadow = report["shadow_vs_candidate0"]
    logged = report["logged_vs_candidate0"]
    lines = [
        "# DP CAMP Route-H10 Shadow Selector Audit",
        "",
        "This is a default-off offline audit. The shadow selector uses only "
        "current-tick finite candidate diagnostics; candidate outcomes are "
        "posterior labels for evaluation only.",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Rule",
        "",
        "```json",
        json.dumps(report["analysis"]["rule"], indent=2, sort_keys=True),
        "```",
        "",
        "## Stage Counts",
        "",
        "| Stage | Records |",
        "| --- | ---: |",
    ]
    for stage, count in report["stage_counts"].items():
        lines.append(f"| `{stage}` | {count} |")
    lines.extend(
        [
            "",
            "## Candidate0 Comparison",
            "",
            "| Selector | Overrides | True | False | Mean safety delta | CVaR90 safety delta | Hard bool worse |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
            _comparison_row("shadow", shadow),
            _comparison_row("logged", logged),
            "",
            "## Shadow Vs Logged",
            "",
            "```json",
            json.dumps(report["shadow_vs_logged"], indent=2, sort_keys=True),
            "```",
            "",
            "## Bucket Summary",
            "",
            "| Bucket | Records | Shadow overrides | Route-H10 escapes | False overrides | Hard bool worse |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for bucket, row in report["by_bucket"].items():
        lines.append(
            f"| `{bucket}` | {row['records']} | {row['shadow_override_records']} | "
            f"{row['route_h10_escape_records']} | {row['false_override_records']} | "
            f"{_nonzero_counts(row['hard_gate_bool_worse_records'])} |"
        )
    lines.extend(
        [
            "",
            "## Stage Outcome Summary",
            "",
            "| Stage | Records | Overrides | True | False | Mean safety delta | CVaR90 safety delta | Hard bool worse |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for stage, row in report["by_stage"].items():
        safety = row["candidate_label_safety_delta"]
        lines.append(
            f"| `{stage}` | {row['records']} | {row['override_records']} | "
            f"{row['true_override_records']} | {row['false_override_records']} | "
            f"{_fmt(safety['mean'])} | {_fmt(safety['cvar90'])} | "
            f"{_nonzero_counts(row['hard_gate_bool_worse_records'])} |"
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


def _comparison_row(name: str, row: dict[str, Any]) -> str:
    safety = row["candidate_label_safety_delta"]
    return (
        f"| `{name}` | {row['override_records']} | "
        f"{row['true_override_records']} | {row['false_override_records']} | "
        f"{_fmt(safety['mean'])} | {_fmt(safety['cvar90'])} | "
        f"{_nonzero_counts(row['hard_gate_bool_worse_records'])} |"
    )


def _nonzero_counts(counts: dict[str, int]) -> str:
    nonzero = [f"{key}:{value}" for key, value in sorted(counts.items()) if value]
    return ", ".join(nonzero) if nonzero else "none"


if __name__ == "__main__":
    main()
