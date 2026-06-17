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
    _outcome_float,
    _outcome_mask_vs_candidate0,
)
from scripts.integrations.analyze_diffusion_planner_top1_preserving_counterfactual import (  # noqa: E402
    RULES,
    _candidate_label_delta,
    _certificate_mask,
    _proxy_delta,
    _select_candidate,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
)


DEFAULT_RULE = "strict_any_comfort_p005"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute false overrides and hidden outcome opportunities for a "
            "Top-1-preserving counterfactual certificate. This is read-only; "
            "outcomes are posterior labels only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--rule", default=DEFAULT_RULE)
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
        rule_name=args.rule,
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
    rule_name: str = DEFAULT_RULE,
    label: str | None = None,
    max_examples: int = 20,
) -> dict[str, Any]:
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")
    rule = _find_rule(rule_name)
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)

    events: list[dict[str, Any]] = []
    total_records = 0
    fallback_records = 0
    candidate0_feasible_records = 0
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw_record in enumerate(payload):
            total_records += 1
            record = _load_record(raw_record, f"{log_path} record {record_index}")
            if not record["feasible"].any():
                fallback_records += 1
            if not (record["feasible"].any() and bool(record["feasible"][0])):
                continue
            candidate0_feasible_records += 1
            event = _event(
                record,
                rule,
                context=context,
                selection_step=int(raw_record.get("selection_step", record_index)),
                record_index=record_index,
            )
            events.append(event)

    false_events = [event for event in events if event["false_override"]]
    hidden_events = [event for event in events if event["hidden_outcome"]]
    true_events = [event for event in events if event["true_override"]]
    override_events = [event for event in events if event["override"]]
    return {
        "analysis": {
            "name": "dp_camp_top1_preserving_failure_attribution_v1",
            "label": label,
            "role": (
                "read-only attribution of false overrides and hidden "
                "opportunities for a Top-1-preserving finite-candidate rule"
            ),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are posterior labels only",
            "classical_benders_claim": False,
            "rule": {
                key: value
                for key, value in rule.items()
                if key in {"name", "progress_budget_m", "trigger", "description"}
            },
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "math_boundary": (
                "The certificate and blocker attributions use fixed current-tick "
                "finite-candidate diagnostics only. Outcome labels are used to "
                "classify posterior false overrides and hidden opportunities; "
                "they are not online selector inputs and are not Benders cut "
                "sources."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": total_records,
            "fallback": fallback_records,
            "nonfallback": total_records - fallback_records,
            "candidate0_feasible": candidate0_feasible_records,
            "override": len(override_events),
            "true_override": len(true_events),
            "false_override": len(false_events),
            "hidden_outcome": len(hidden_events),
        },
        "false_override": _false_report(false_events, max_examples=max_examples),
        "hidden_outcome": _hidden_report(hidden_events, max_examples=max_examples),
        "true_override": _event_summary(true_events),
        "override": _event_summary(override_events),
        "by_bucket": _bucket_report(events),
    }


def _event(
    record: dict[str, Any],
    rule: dict[str, Any],
    *,
    context: dict[str, Any],
    selection_step: int,
    record_index: int,
) -> dict[str, Any]:
    certificate_mask = _certificate_mask(record, rule)
    selected = _select_candidate(record, certificate_mask)
    outcome_mask = _outcome_mask_vs_candidate0(record, float(rule["progress_budget_m"]))
    override = selected != 0
    selected_matches_outcome = bool(override and outcome_mask[selected])
    false_override = bool(override and not selected_matches_outcome)
    hidden_outcome = bool((not override) and outcome_mask.any())
    best_hidden = (
        _best_outcome_candidate(record, outcome_mask)
        if hidden_outcome
        else None
    )
    return {
        "context": context,
        "selection_step": int(selection_step),
        "record_index": int(record_index),
        "selected": int(selected),
        "override": override,
        "true_override": selected_matches_outcome,
        "false_override": false_override,
        "hidden_outcome": hidden_outcome,
        "certificate_size": int(certificate_mask.sum()),
        "outcome_oracle_size": int(outcome_mask.sum()),
        "selected_candidate": (
            _candidate_payload(record, selected)
            if override
            else _candidate_payload(record, 0)
        ),
        "false_reasons": (
            _outcome_oracle_failure_reasons(
                record,
                selected,
                float(rule["progress_budget_m"]),
            )
            if false_override
            else []
        ),
        "best_hidden_candidate": (
            _candidate_payload(record, best_hidden)
            if best_hidden is not None
            else None
        ),
        "hidden_blockers": (
            _certificate_blockers(
                record,
                best_hidden,
                float(rule["progress_budget_m"]),
            )
            if best_hidden is not None
            else []
        ),
    }


def _candidate_payload(record: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "candidate_index": int(index),
        "candidate_label_delta": _candidate_label_delta(record, index),
        "proxy_delta": _proxy_delta(record, index),
    }


def _outcome_oracle_failure_reasons(
    record: dict[str, Any],
    candidate: int,
    progress_budget_m: float,
) -> list[str]:
    reasons: list[str] = []
    candidate_progress = _outcome_float(record, candidate, "progress_m")
    candidate0_progress = _outcome_float(record, 0, "progress_m")
    if candidate_progress < candidate0_progress - progress_budget_m - TOL:
        reasons.append("outcome_progress_loss_exceeds_budget")
    for field in BOOL_OUTCOMES:
        candidate_value = bool(record["outcomes"][candidate].get(field))
        candidate0_value = bool(record["outcomes"][0].get(field))
        if candidate_value and not candidate0_value:
            reasons.append(f"outcome_{field}_worse")
    jerk = _outcome_float(record, candidate, "mean_jerk_mps3")
    jerk0 = _outcome_float(record, 0, "mean_jerk_mps3")
    lateral = _outcome_float(record, candidate, "mean_lateral_acceleration_mps2")
    lateral0 = _outcome_float(record, 0, "mean_lateral_acceleration_mps2")
    if jerk > jerk0 + TOL:
        reasons.append("outcome_jerk_worse")
    if lateral > lateral0 + TOL:
        reasons.append("outcome_lateral_worse")
    strict = False
    for field in BOOL_OUTCOMES:
        strict |= bool(record["outcomes"][0].get(field)) and not bool(
            record["outcomes"][candidate].get(field)
        )
    strict |= jerk < jerk0 - TOL
    strict |= lateral < lateral0 - TOL
    if not strict:
        reasons.append("no_strict_outcome_safety_or_comfort_gain")
    return reasons or ["unknown_outcome_oracle_failure"]


def _certificate_blockers(
    record: dict[str, Any],
    candidate: int,
    progress_budget_m: float,
) -> list[str]:
    blockers: list[str] = []
    if not bool(record["feasible"][candidate]):
        blockers.append("not_base_feasible")
    if candidate == 0:
        blockers.append("candidate0")
    if (
        record["progress_shortfall"][candidate]
        > record["progress_shortfall"][0] + progress_budget_m + TOL
    ):
        blockers.append("progress_shortfall_exceeds_budget")
    if record["union_red"][candidate] > record["union_red"][0] + TOL:
        blockers.append("union_red_worse")
    if record["red_stopping"][candidate] > record["red_stopping"][0] + TOL:
        blockers.append("red_stopping_worse")
    if record["proxy_jerk"][candidate] > record["proxy_jerk"][0] + TOL:
        blockers.append("proxy_jerk_worse")
    if record["proxy_lateral"][candidate] > record["proxy_lateral"][0] + TOL:
        blockers.append("proxy_lateral_worse")
    any_comfort = (
        record["proxy_jerk"][candidate] < record["proxy_jerk"][0] - TOL
        or record["proxy_lateral"][candidate] < record["proxy_lateral"][0] - TOL
    )
    if not any_comfort:
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
    jerk = np.asarray(
        [
            _outcome_float(record, int(index), "mean_jerk_mps3")
            for index in indices
        ],
        dtype=np.float64,
    )
    lateral = np.asarray(
        [
            _outcome_float(record, int(index), "mean_lateral_acceleration_mps2")
            for index in indices
        ],
        dtype=np.float64,
    )
    order = np.lexsort((indices, lateral, jerk, progress_loss, cost))
    return int(indices[order[0]])


def _false_report(events: list[dict[str, Any]], *, max_examples: int) -> dict[str, Any]:
    return {
        "records": len(events),
        "reason_counts": _counter(
            reason for event in events for reason in event["false_reasons"]
        ),
        "event_summary": _event_summary(events),
        "by_bucket": _bucket_report(events, hidden=False),
        "examples": _examples(events, max_examples=max_examples, sort_key="worst"),
    }


def _hidden_report(events: list[dict[str, Any]], *, max_examples: int) -> dict[str, Any]:
    return {
        "records": len(events),
        "blocker_counts": _counter(
            blocker for event in events for blocker in event["hidden_blockers"]
        ),
        "event_summary": _hidden_candidate_summary(events),
        "by_bucket": _bucket_report(events, hidden=True),
        "examples": _examples(events, max_examples=max_examples, sort_key="best"),
    }


def _event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [event["selected_candidate"] for event in events]
    return _candidate_collection_summary(candidates)


def _hidden_candidate_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        event["best_hidden_candidate"]
        for event in events
        if event["best_hidden_candidate"] is not None
    ]
    return _candidate_collection_summary(candidates)


def _candidate_collection_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
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
        "bool_worse_counts": {
            field: sum(
                int(candidate["candidate_label_delta"]["bool_delta"][field] > 0)
                for candidate in candidates
            )
            for field in BOOL_OUTCOMES
        },
    }


def _bucket_report(
    events: list[dict[str, Any]],
    *,
    hidden: bool = False,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        buckets = event["context"].get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            if bucket not in SUPPORTED_SCENARIO_BUCKETS:
                raise ValueError(f"Unsupported scenario bucket: {bucket}")
            grouped[str(bucket)].append(event)
    return [
        {
            "bucket": bucket,
            "records": len(grouped[bucket]),
            "summary": (
                _hidden_candidate_summary(grouped[bucket])
                if hidden
                else _event_summary(grouped[bucket])
            ),
        }
        for bucket in _ordered_buckets(grouped)
    ]


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
    sort_key: str,
) -> list[dict[str, Any]]:
    if max_examples <= 0:
        return []
    reverse = sort_key == "worst"
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
    candidate = event.get("selected_candidate") or event.get("best_hidden_candidate")
    if not isinstance(candidate, dict):
        return (0.0, int(event["selection_step"]))
    cost = candidate["candidate_label_delta"]["candidate_label_safety_delta"]
    return (float(cost), int(event["selection_step"]))


def _find_rule(name: str) -> dict[str, Any]:
    for rule in RULES:
        if rule["name"] == name:
            return rule
    raise ValueError(f"Unknown rule {name!r}. Available: {[rule['name'] for rule in RULES]}")


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
    false = report["false_override"]
    hidden = report["hidden_outcome"]
    lines = [
        "# DP CAMP Top-1-Preserving Failure Attribution",
        "",
        "This is a read-only offline attribution. Outcome labels classify "
        "posterior false overrides and hidden opportunities only.",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## False Overrides",
        "",
        f"- Records: `{false['records']}`",
        "",
        "| Reason | Records |",
        "| --- | ---: |",
    ]
    for reason, count in false["reason_counts"].items():
        lines.append(f"| `{reason}` | {count} |")
    lines.extend(
        [
            "",
            "### False Override Summary",
            "",
            _summary_table(false["event_summary"]),
            "## Hidden Outcome Opportunities",
            "",
            f"- Records: `{hidden['records']}`",
            "",
            "| Blocker | Records |",
            "| --- | ---: |",
        ]
    )
    for blocker, count in hidden["blocker_counts"].items():
        lines.append(f"| `{blocker}` | {count} |")
    lines.extend(
        [
            "",
            "### Hidden Candidate Summary",
            "",
            _summary_table(hidden["event_summary"]),
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _summary_table(summary: dict[str, Any]) -> str:
    rows = [
        ("candidate_label_safety_delta", summary["candidate_label_safety_delta"]),
        ("outcome_progress_delta_m", summary["outcome_progress_delta_m"]),
        ("outcome_jerk_delta_mps3", summary["outcome_jerk_delta_mps3"]),
        ("outcome_lateral_delta_mps2", summary["outcome_lateral_delta_mps2"]),
    ]
    lines = [
        "| Field | n | mean | p50 | p90 | cvar90 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, stats in rows:
        lines.append(
            f"| `{name}` | {stats['n']} | {_fmt(stats['mean'])} | "
            f"{_fmt(stats['p50'])} | {_fmt(stats['p90'])} | "
            f"{_fmt(stats['cvar90'])} |"
        )
    lines.extend(
        [
            "",
            "| Proxy delta | n | mean | p50 | p90 | cvar90 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, stats in summary["proxy_delta"].items():
        lines.append(
            f"| `{name}` | {stats['n']} | {_fmt(stats['mean'])} | "
            f"{_fmt(stats['p50'])} | {_fmt(stats['p90'])} | "
            f"{_fmt(stats['cvar90'])} |"
        )
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


if __name__ == "__main__":
    main()
