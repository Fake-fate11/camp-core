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
    parse_selection_log_metadata,
)
from scripts.integrations.analyze_diffusion_planner_candidate_availability import (  # noqa: E402
    PROGRESS_BUDGETS_M,
    _best_outcome_candidate,
    _load_record,
    _outcome_float,
    _outcome_joint_comfort_mask,
    _outcome_pareto_mask,
    _proxy_joint_comfort_mask,
    _proxy_pareto_mask,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
    _run_key,
    _scenario_buckets,
)


TOL = 1e-12
DEFAULT_TICK_BIN_SIZE = 50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute hidden outcome-labeled candidate opportunities by route, "
            "scenario bucket, run context, and tick bin. This is read-only and "
            "does not change CAMP selection."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument(
        "--progress_budget_m",
        type=float,
        action="append",
        default=[],
        help="Repeat to override default budgets 0, 0.05, 0.10, 0.25.",
    )
    parser.add_argument("--tick_bin_size", type=int, default=DEFAULT_TICK_BIN_SIZE)
    parser.add_argument("--max_examples", type=int, default=20)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def analyze(
    paths: list[Path],
    *,
    scenario_bucket_manifest: Path | None = None,
    progress_budgets_m: tuple[float, ...] = PROGRESS_BUDGETS_M,
    tick_bin_size: int = DEFAULT_TICK_BIN_SIZE,
    max_examples: int = 20,
) -> dict[str, Any]:
    if tick_bin_size <= 0:
        raise ValueError("tick_bin_size must be positive.")
    budgets = tuple(_canonical_budget(value) for value in progress_budgets_m)
    if len(set(budgets)) != len(budgets):
        raise ValueError("Progress budgets must be unique.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)

    events: dict[float, list[dict[str, Any]]] = {budget: [] for budget in budgets}
    fallback_records = 0
    total_records = 0
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(payload):
            total_records += 1
            loaded = _load_record(record, f"{log_path} record {record_index}")
            if not loaded["feasible"].any():
                fallback_records += 1
                continue
            step = int(record.get("selection_step", record_index))
            for budget in budgets:
                events[budget].append(
                    _record_event(
                        loaded,
                        context=context,
                        selection_step=step,
                        tick_bin_size=tick_bin_size,
                        budget=budget,
                    )
                )

    budget_reports = [
        _budget_report(
            budget,
            events[budget],
            max_examples=max_examples,
        )
        for budget in budgets
    ]
    return {
        "analysis": {
            "name": "dp_camp_hidden_outcome_gap_v1",
            "role": "offline hidden outcome-labeled opportunity attribution",
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are offline labels only",
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "progress_budgets_m": list(budgets),
            "tick_bin_size": int(tick_bin_size),
            "outcome_joint_definition": (
                "candidate passes the existing outcome Pareto mask and is "
                "strictly better than selected on both outcome jerk and outcome "
                "lateral acceleration"
            ),
            "proxy_joint_definition": (
                "candidate passes the existing current-tick proxy Pareto mask "
                "and is strictly better than selected on both proxy jerk and "
                "proxy lateral acceleration"
            ),
            "math_boundary": (
                "All proxy quantities are fixed current-tick finite-candidate "
                "constants. Closed-loop candidate outcomes are labels for this "
                "offline attribution only and are not online atoms or a Benders "
                "subproblem."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": total_records,
            "nonfallback": total_records - fallback_records,
            "fallback": fallback_records,
        },
        "budgets": budget_reports,
    }


def _log_context(log_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = parse_selection_log_metadata(log_path)
    validation_summary = _read_json_if_exists(
        log_path.with_name("camp_validation_summary.json")
    )
    benchmark = validation_summary.get("benchmark", {})
    if not isinstance(benchmark, dict):
        benchmark = {}
    route = benchmark.get("route")
    route_name = Path(str(route)).stem if route is not None else metadata.route
    traffic_lights = benchmark.get("traffic_lights")
    if traffic_lights is None:
        traffic_lights = metadata.traffic_light == "on"
    max_npcs = benchmark.get("max_npcs")
    if max_npcs is None:
        max_npcs = metadata.npc_count
    seed = benchmark.get("seed")
    if seed is None:
        seed = metadata.seed
    row = {
        "run_key": _run_key(validation_summary, log_path.parent),
        "route": route,
        "route_name": route_name,
        "seed": seed,
        "max_npcs": max_npcs,
        "traffic_lights": bool(traffic_lights),
        "advance_mode": benchmark.get(
            "advance_mode",
            validation_summary.get("advance_mode"),
        ),
    }
    return {
        **row,
        "log_path": str(log_path),
        "scenario_buckets": _scenario_buckets(row, manifest),
    }


def _record_event(
    record: dict[str, Any],
    *,
    context: dict[str, Any],
    selection_step: int,
    tick_bin_size: int,
    budget: float,
) -> dict[str, Any]:
    outcome_joint_mask = (
        _outcome_pareto_mask(record, budget) & _outcome_joint_comfort_mask(record)
    )
    proxy_joint_mask = (
        _proxy_pareto_mask(record, budget) & _proxy_joint_comfort_mask(record)
    )
    outcome_joint = bool(outcome_joint_mask.any())
    proxy_joint = bool(proxy_joint_mask.any())
    event = {
        "context": context,
        "selection_step": int(selection_step),
        "tick_bin": _tick_bin(selection_step, tick_bin_size),
        "outcome_joint": outcome_joint,
        "proxy_joint": proxy_joint,
        "hidden_joint": outcome_joint and not proxy_joint,
        "selected_index": int(record["selected_index"]),
    }
    if event["hidden_joint"]:
        best = _best_outcome_candidate(record, outcome_joint_mask)
        event["best_hidden_candidate"] = _hidden_candidate_metrics(
            record,
            best,
            budget=budget,
        )
    return event


def _hidden_candidate_metrics(
    record: dict[str, Any],
    candidate_index: int,
    *,
    budget: float,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    proxy = {
        "progress_shortfall": _delta(record["progress_shortfall"], candidate_index, selected),
        "proxy_jerk": _delta(record["proxy_jerk"], candidate_index, selected),
        "proxy_lateral": _delta(record["proxy_lateral"], candidate_index, selected),
        "union_red": _delta(record["union_red"], candidate_index, selected),
        "red_stopping": _delta(record["red_stopping"], candidate_index, selected),
    }
    outcome = {
        "progress_m": (
            _outcome_float(record, candidate_index, "progress_m")
            - _outcome_float(record, selected, "progress_m")
        ),
        "mean_jerk_mps3": (
            _outcome_float(record, candidate_index, "mean_jerk_mps3")
            - _outcome_float(record, selected, "mean_jerk_mps3")
        ),
        "mean_lateral_acceleration_mps2": (
            _outcome_float(record, candidate_index, "mean_lateral_acceleration_mps2")
            - _outcome_float(record, selected, "mean_lateral_acceleration_mps2")
        ),
    }
    return {
        "candidate_index": int(candidate_index),
        "outcome_delta": outcome,
        "proxy_delta": proxy,
        "proxy_blockers": _proxy_blockers(proxy, budget),
    }


def _proxy_blockers(proxy_delta: dict[str, float], budget: float) -> list[str]:
    blockers = []
    if proxy_delta["progress_shortfall"] > budget + TOL:
        blockers.append("proxy_progress_shortfall_blocked")
    if proxy_delta["union_red"] > TOL or proxy_delta["red_stopping"] > TOL:
        blockers.append("proxy_safety_proxy_blocked")
    if proxy_delta["proxy_jerk"] > TOL or proxy_delta["proxy_lateral"] > TOL:
        blockers.append("proxy_comfort_nonworse_blocked")
    if not (
        proxy_delta["proxy_jerk"] < -TOL and proxy_delta["proxy_lateral"] < -TOL
    ):
        blockers.append("proxy_joint_comfort_not_strict")
    return blockers or ["other_proxy_joint_not_available"]


def _budget_report(
    budget: float,
    events: list[dict[str, Any]],
    *,
    max_examples: int,
) -> dict[str, Any]:
    overall = _summarize_events(events)
    return {
        "progress_budget_m": float(budget),
        "overall": overall,
        "by_route": _group_report(events, lambda event: event["context"]["route_name"]),
        "by_bucket": _group_report(
            events,
            lambda event: event["context"]["scenario_buckets"],
            multi=True,
        ),
        "by_run_context": _group_report(events, _run_context_key),
        "by_tick_bin": _group_report(events, lambda event: event["tick_bin"]),
        "hidden_proxy_blockers": _counter_dict(
            blocker
            for event in events
            if event["hidden_joint"]
            for blocker in event["best_hidden_candidate"]["proxy_blockers"]
        ),
        "hidden_delta_summary": _hidden_delta_summary(events),
        "top_hidden_examples": _top_hidden_examples(events, max_examples),
    }


def _summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)
    outcome = sum(int(event["outcome_joint"]) for event in events)
    proxy = sum(int(event["proxy_joint"]) for event in events)
    hidden = sum(int(event["hidden_joint"]) for event in events)
    return {
        "nonfallback_records": total,
        "outcome_joint_records": outcome,
        "outcome_joint_rate": outcome / max(total, 1),
        "proxy_joint_records": proxy,
        "proxy_joint_rate": proxy / max(total, 1),
        "hidden_joint_records": hidden,
        "hidden_joint_rate": hidden / max(total, 1),
        "hidden_given_outcome_joint_rate": hidden / max(outcome, 1),
    }


def _group_report(
    events: list[dict[str, Any]],
    key_fn,
    *,
    multi: bool = False,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        keys = key_fn(event)
        if not multi:
            keys = [keys]
        for key in keys:
            groups[str(key)].append(event)
    rows = [
        {"group": key, **_summarize_events(group)}
        for key, group in sorted(groups.items())
    ]
    rows.sort(
        key=lambda row: (
            -int(row["hidden_joint_records"]),
            -float(row["hidden_joint_rate"]),
            row["group"],
        )
    )
    return rows


def _hidden_delta_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    fields = {
        "outcome_delta.progress_m": [],
        "outcome_delta.mean_jerk_mps3": [],
        "outcome_delta.mean_lateral_acceleration_mps2": [],
        "proxy_delta.progress_shortfall": [],
        "proxy_delta.proxy_jerk": [],
        "proxy_delta.proxy_lateral": [],
        "proxy_delta.union_red": [],
        "proxy_delta.red_stopping": [],
    }
    for event in events:
        if not event["hidden_joint"]:
            continue
        candidate = event["best_hidden_candidate"]
        for key, value in candidate["outcome_delta"].items():
            fields[f"outcome_delta.{key}"].append(float(value))
        for key, value in candidate["proxy_delta"].items():
            fields[f"proxy_delta.{key}"].append(float(value))
    return {key: _stats(values) for key, values in fields.items()}


def _top_hidden_examples(
    events: list[dict[str, Any]],
    max_examples: int,
) -> list[dict[str, Any]]:
    hidden = [event for event in events if event["hidden_joint"]]
    hidden.sort(key=_hidden_example_sort_key)
    examples = []
    for event in hidden[: max(0, max_examples)]:
        candidate = event["best_hidden_candidate"]
        context = event["context"]
        examples.append(
            {
                "route_name": context["route_name"],
                "scenario_buckets": context["scenario_buckets"],
                "seed": context["seed"],
                "max_npcs": context["max_npcs"],
                "traffic_lights": context["traffic_lights"],
                "selection_step": event["selection_step"],
                "tick_bin": event["tick_bin"],
                "selected_index": event["selected_index"],
                "candidate_index": candidate["candidate_index"],
                "outcome_delta": candidate["outcome_delta"],
                "proxy_delta": candidate["proxy_delta"],
                "proxy_blockers": candidate["proxy_blockers"],
                "run_key": context["run_key"],
                "log_path": context["log_path"],
            }
        )
    return examples


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Hidden Outcome Gap Attribution",
        "",
        "Candidate outcomes are offline labels only. This report does not change "
        "the online selector, CAMP weights, atom schema, DP sampler, or DP code.",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
    ]
    for budget in report["budgets"]:
        overall = budget["overall"]
        lines.extend(
            [
                f"## Progress Budget {budget['progress_budget_m']:.2f} m",
                "",
                "| Scope | Nonfallback | Outcome joint | Proxy joint | Hidden joint | "
                "Hidden / outcome |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
                _summary_row("overall", overall),
                "",
                "### By Route",
                "",
                _table_for_groups(budget["by_route"]),
                "### By Scenario Bucket",
                "",
                _table_for_groups(budget["by_bucket"]),
                "### By Tick Bin",
                "",
                _table_for_groups(budget["by_tick_bin"]),
                "### Hidden Proxy Blockers",
                "",
                _counter_table(budget["hidden_proxy_blockers"]),
                "",
            ]
        )
    lines.extend(
        [
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _summary_row(label: str, row: dict[str, Any]) -> str:
    return (
        f"| {label} | {row['nonfallback_records']} | "
        f"{row['outcome_joint_records']} ({row['outcome_joint_rate']:.6f}) | "
        f"{row['proxy_joint_records']} ({row['proxy_joint_rate']:.6f}) | "
        f"{row['hidden_joint_records']} ({row['hidden_joint_rate']:.6f}) | "
        f"{row['hidden_given_outcome_joint_rate']:.6f} |"
    )


def _table_for_groups(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No records._\n"
    lines = [
        "| Group | Nonfallback | Outcome joint | Proxy joint | Hidden joint | "
        "Hidden / outcome |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(_summary_row(str(row["group"]), row))
    return "\n".join(lines) + "\n"


def _counter_table(counter: dict[str, int]) -> str:
    if not counter:
        return "_No hidden records._"
    lines = ["| Blocker | Records |", "| --- | ---: |"]
    for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def _run_context_key(event: dict[str, Any]) -> str:
    context = event["context"]
    return (
        f"route={context['route_name']}|seed={context['seed']}|"
        f"npc={context['max_npcs']}|tl={context['traffic_lights']}"
    )


def _tick_bin(step: int, tick_bin_size: int) -> str:
    start = (int(step) // tick_bin_size) * tick_bin_size
    end = start + tick_bin_size - 1
    return f"{start:04d}-{end:04d}"


def _hidden_example_sort_key(event: dict[str, Any]) -> tuple[float, int]:
    candidate = event["best_hidden_candidate"]
    outcome = candidate["outcome_delta"]
    comfort_gain = (
        float(outcome["mean_jerk_mps3"])
        + float(outcome["mean_lateral_acceleration_mps2"])
    )
    return (comfort_gain, int(event["selection_step"]))


def _delta(values: np.ndarray, candidate: int, selected: int) -> float:
    return float(values[candidate] - values[selected])


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "p50": None, "p90": None}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
    }


def _counter_dict(values) -> dict[str, int]:
    return {key: int(value) for key, value in Counter(values).items()}


def _canonical_budget(value: float) -> float:
    budget = round(float(value), 8)
    if budget < -TOL:
        raise ValueError("Progress budgets must be nonnegative.")
    return budget


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def main() -> None:
    args = parse_args()
    paths = list(args.root) + list(args.selection_log)
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    budgets = (
        tuple(args.progress_budget_m)
        if args.progress_budget_m
        else PROGRESS_BUDGETS_M
    )
    report = analyze(
        paths,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        progress_budgets_m=budgets,
        tick_bin_size=args.tick_bin_size,
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


if __name__ == "__main__":
    main()
