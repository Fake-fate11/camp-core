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
    _canonical_budget,
    _load_record,
    _log_context,
    _outcome_float,
    _outcome_mask_vs_candidate0,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
)


RULES: tuple[dict[str, Any], ...] = (
    {
        "name": "top1_only",
        "progress_budget_m": 0.05,
        "trigger": "none",
        "description": "candidate0 whenever candidate0 is feasible; otherwise retain baseline",
    },
    {
        "name": "strict_joint_comfort_p005",
        "progress_budget_m": 0.05,
        "trigger": "joint_comfort",
        "description": (
            "override only if current-tick proxy jerk and proxy lateral are both "
            "strictly lower than candidate0, red proxies are nonworse, and "
            "progress_shortfall is within 0.05 m of candidate0"
        ),
    },
    {
        "name": "strict_joint_comfort_p010",
        "progress_budget_m": 0.10,
        "trigger": "joint_comfort",
        "description": (
            "same as strict_joint_comfort_p005 with a 0.10 m progress budget"
        ),
    },
    {
        "name": "strict_red_or_joint_comfort_p005",
        "progress_budget_m": 0.05,
        "trigger": "red_or_joint_comfort",
        "description": (
            "override only if red proxy strictly improves or both proxy comfort "
            "terms strictly improve, while all red/comfort proxies are nonworse "
            "and progress_shortfall is within 0.05 m of candidate0"
        ),
    },
)
SAFETY_DELTA_WEIGHTS = {
    "collision": 100.0,
    "near_miss": 10.0,
    "lane_violation": 20.0,
    "red_light_violation": 30.0,
    "mean_jerk_mps3": 1.0 / 10.0,
    "mean_lateral_acceleration_mps2": 1.0,
    "progress_loss_m": 2.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline Top-1-preserving counterfactual selector audit. This "
            "does not change online CAMP selection and uses outcomes only as "
            "posterior labels."
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
        for record_index, record in enumerate(payload):
            loaded = _load_record(record, f"{log_path} record {record_index}")
            loaded["context"] = context
            loaded["selection_step"] = int(record.get("selection_step", record_index))
            loaded["record_index"] = int(record_index)
            records.append(loaded)

    reports = []
    for rule in RULES:
        rows = [_evaluate_record(record, rule) for record in records]
        reports.append(_rule_report(rule, rows, max_examples=max_examples))
    return {
        "analysis": {
            "name": "dp_camp_top1_preserving_counterfactual_v1",
            "label": label,
            "role": (
                "offline counterfactual audit before any online Top-1-preserving "
                "finite-candidate selector"
            ),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are posterior labels only",
            "classical_benders_claim": False,
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "rules": [
                {
                    key: value
                    for key, value in rule.items()
                    if key in {"name", "progress_budget_m", "trigger", "description"}
                }
                for rule in RULES
            ],
            "selection_contract": (
                "If candidate0 is feasible, select candidate0 unless a fixed "
                "current-tick certificate admits a nonzero candidate. If "
                "candidate0 is infeasible or all candidates are infeasible, "
                "retain the logged CAMP baseline selection. Tie-breaks are "
                "deterministic over fixed finite candidate diagnostics."
            ),
            "candidate_label_safety_delta": (
                "A posterior outcome-label proxy, not closed-loop run "
                "SafetyCost v1: bool outcome deltas use SafetyCost v1 event "
                "weights; jerk/lateral use the same normalizations; route "
                "shortfall is replaced by candidate outcome progress loss "
                "relative to candidate0."
            ),
            "math_boundary": (
                "All selector inputs are fixed current-tick finite-candidate "
                "constants: feasibility, progress_shortfall, red proxies, "
                "comfort proxies, affine scores, and deterministic indices. "
                "Outcome labels evaluate the counterfactual only and do not "
                "enter online selection or a Benders cut. If the certificate "
                "is atomized with fixed nonnegative scales, the CAMP score "
                "remains affine in the master variable."
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
        "rules": reports,
    }


def _evaluate_record(record: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    candidate0_feasible = bool(record["feasible"].any() and record["feasible"][0])
    logged_selected = int(record["selected_index"])
    progress_budget = _canonical_budget(float(rule["progress_budget_m"]))
    if candidate0_feasible:
        mask = _certificate_mask(record, rule)
        selected = _select_candidate(record, mask)
        retained_baseline_reason = None
    else:
        mask = np.zeros(int(record["candidate_count"]), dtype=bool)
        selected = logged_selected
        retained_baseline_reason = (
            "all_infeasible" if not record["feasible"].any() else "candidate0_infeasible"
        )

    outcome_mask = (
        _outcome_mask_vs_candidate0(record, progress_budget)
        if candidate0_feasible
        else np.zeros(int(record["candidate_count"]), dtype=bool)
    )
    override = bool(candidate0_feasible and selected != 0)
    outcome_available = bool(outcome_mask.any())
    certificate_available = bool(mask.any())
    selected_matches_outcome = bool(
        candidate0_feasible and override and outcome_mask[selected]
    )
    return {
        "context": record["context"],
        "selection_step": int(record["selection_step"]),
        "record_index": int(record["record_index"]),
        "candidate0_feasible": candidate0_feasible,
        "logged_selected": logged_selected,
        "selected": int(selected),
        "override": override,
        "certificate_available": certificate_available,
        "outcome_available": outcome_available,
        "selected_matches_outcome": selected_matches_outcome,
        "false_override": bool(override and not selected_matches_outcome),
        "hidden_outcome": bool(candidate0_feasible and not override and outcome_available),
        "progress_budget_m": progress_budget,
        "retained_baseline_reason": retained_baseline_reason,
        "candidate_label_delta": (
            _candidate_label_delta(record, selected)
            if candidate0_feasible
            else None
        ),
        "certificate_size": int(mask.sum()),
        "outcome_oracle_size": int(outcome_mask.sum()),
        "proxy_delta": (
            _proxy_delta(record, selected) if candidate0_feasible else None
        ),
    }


def _certificate_mask(record: dict[str, Any], rule: dict[str, Any]) -> np.ndarray:
    size = int(record["candidate_count"])
    if str(rule["trigger"]) == "none":
        return np.zeros(size, dtype=bool)
    budget = _canonical_budget(float(rule["progress_budget_m"]))
    mask = record["feasible"].copy()
    mask[0] = False
    mask &= record["progress_shortfall"] <= record["progress_shortfall"][0] + budget + TOL
    mask &= record["union_red"] <= record["union_red"][0] + TOL
    mask &= record["red_stopping"] <= record["red_stopping"][0] + TOL
    mask &= record["proxy_jerk"] <= record["proxy_jerk"][0] + TOL
    mask &= record["proxy_lateral"] <= record["proxy_lateral"][0] + TOL
    joint_comfort = (
        (record["proxy_jerk"] < record["proxy_jerk"][0] - TOL)
        & (record["proxy_lateral"] < record["proxy_lateral"][0] - TOL)
    )
    red_improving = (
        (record["union_red"] < record["union_red"][0] - TOL)
        | (record["red_stopping"] < record["red_stopping"][0] - TOL)
    )
    trigger = str(rule["trigger"])
    if trigger == "joint_comfort":
        mask &= joint_comfort
    elif trigger == "red_or_joint_comfort":
        mask &= joint_comfort | red_improving
    else:
        raise ValueError(f"Unsupported rule trigger: {trigger}")
    return mask


def _select_candidate(record: dict[str, Any], mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return 0
    order = np.lexsort(
        (
            indices,
            record["scores"][indices],
            record["progress_shortfall"][indices],
            record["proxy_jerk"][indices],
            record["proxy_lateral"][indices],
            record["red_stopping"][indices],
            record["union_red"][indices],
        )
    )
    return int(indices[order[0]])


def _candidate_label_delta(record: dict[str, Any], selected: int) -> dict[str, Any]:
    progress_delta = (
        _outcome_float(record, selected, "progress_m")
        - _outcome_float(record, 0, "progress_m")
    )
    jerk_delta = (
        _outcome_float(record, selected, "mean_jerk_mps3")
        - _outcome_float(record, 0, "mean_jerk_mps3")
    )
    lateral_delta = (
        _outcome_float(record, selected, "mean_lateral_acceleration_mps2")
        - _outcome_float(record, 0, "mean_lateral_acceleration_mps2")
    )
    bool_delta = {
        field: int(bool(record["outcomes"][selected].get(field)))
        - int(bool(record["outcomes"][0].get(field)))
        for field in BOOL_OUTCOMES
    }
    cost_delta = (
        SAFETY_DELTA_WEIGHTS["collision"] * bool_delta["collision"]
        + SAFETY_DELTA_WEIGHTS["near_miss"] * bool_delta["near_miss"]
        + SAFETY_DELTA_WEIGHTS["lane_violation"] * bool_delta["lane_violation"]
        + SAFETY_DELTA_WEIGHTS["red_light_violation"] * bool_delta["red_light_violation"]
        + SAFETY_DELTA_WEIGHTS["mean_jerk_mps3"] * jerk_delta
        + SAFETY_DELTA_WEIGHTS["mean_lateral_acceleration_mps2"] * lateral_delta
        + SAFETY_DELTA_WEIGHTS["progress_loss_m"] * max(0.0, -progress_delta)
    )
    return {
        "progress_m": progress_delta,
        "mean_jerk_mps3": jerk_delta,
        "mean_lateral_acceleration_mps2": lateral_delta,
        "bool_delta": bool_delta,
        "candidate_label_safety_delta": float(cost_delta),
        "progress_loss_m": max(0.0, -progress_delta),
    }


def _proxy_delta(record: dict[str, Any], selected: int) -> dict[str, float]:
    return {
        "progress_shortfall": float(
            record["progress_shortfall"][selected] - record["progress_shortfall"][0]
        ),
        "proxy_jerk": float(record["proxy_jerk"][selected] - record["proxy_jerk"][0]),
        "proxy_lateral": float(
            record["proxy_lateral"][selected] - record["proxy_lateral"][0]
        ),
        "union_red": float(record["union_red"][selected] - record["union_red"][0]),
        "red_stopping": float(
            record["red_stopping"][selected] - record["red_stopping"][0]
        ),
        "selection_score": float(record["scores"][selected] - record["scores"][0]),
    }


def _rule_report(
    rule: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    max_examples: int,
) -> dict[str, Any]:
    by_bucket = _rows_by_bucket(rows)
    return {
        "name": str(rule["name"]),
        "progress_budget_m": float(rule["progress_budget_m"]),
        "trigger": str(rule["trigger"]),
        "description": str(rule["description"]),
        "overall": _summarize_rows(rows),
        "by_bucket": [
            {"bucket": bucket, **_summarize_rows(bucket_rows)}
            for bucket, bucket_rows in by_bucket.items()
        ],
        "false_override_examples": _example_rows(
            [row for row in rows if row["false_override"]],
            max_examples=max_examples,
        ),
        "hidden_outcome_examples": _example_rows(
            [row for row in rows if row["hidden_outcome"]],
            max_examples=max_examples,
        ),
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidate0_rows = [row for row in rows if row["candidate0_feasible"]]
    overrides = [row for row in candidate0_rows if row["override"]]
    false_overrides = [row for row in overrides if row["false_override"]]
    true_overrides = [row for row in overrides if row["selected_matches_outcome"]]
    hidden = [row for row in candidate0_rows if row["hidden_outcome"]]
    outcome_available = [row for row in candidate0_rows if row["outcome_available"]]
    certificate_available = [
        row for row in candidate0_rows if row["certificate_available"]
    ]
    retained = Counter(
        str(row["retained_baseline_reason"])
        for row in rows
        if row["retained_baseline_reason"] is not None
    )
    deltas = [row["candidate_label_delta"] for row in candidate0_rows]
    override_deltas = [row["candidate_label_delta"] for row in overrides]
    bool_worse = {
        field: sum(
            int(delta["bool_delta"][field] > 0)
            for delta in override_deltas
            if delta is not None
        )
        for field in BOOL_OUTCOMES
    }
    return {
        "records": len(rows),
        "candidate0_feasible_records": len(candidate0_rows),
        "retained_baseline_reasons": dict(sorted(retained.items())),
        "certificate_available_records": len(certificate_available),
        "certificate_available_rate": len(certificate_available)
        / max(len(candidate0_rows), 1),
        "outcome_available_records": len(outcome_available),
        "outcome_available_rate": len(outcome_available) / max(len(candidate0_rows), 1),
        "override_records": len(overrides),
        "override_rate": len(overrides) / max(len(candidate0_rows), 1),
        "true_override_records": len(true_overrides),
        "true_override_rate_among_overrides": len(true_overrides)
        / max(len(overrides), 1),
        "false_override_records": len(false_overrides),
        "false_override_rate_among_overrides": len(false_overrides)
        / max(len(overrides), 1),
        "hidden_outcome_records": len(hidden),
        "hidden_outcome_rate": len(hidden) / max(len(candidate0_rows), 1),
        "candidate_label_safety_delta_all": _delta_stats(
            deltas,
            "candidate_label_safety_delta",
        ),
        "candidate_label_safety_delta_overrides": _delta_stats(
            override_deltas,
            "candidate_label_safety_delta",
        ),
        "progress_delta_overrides": _delta_stats(override_deltas, "progress_m"),
        "jerk_delta_overrides": _delta_stats(override_deltas, "mean_jerk_mps3"),
        "lateral_delta_overrides": _delta_stats(
            override_deltas,
            "mean_lateral_acceleration_mps2",
        ),
        "progress_loss_gt_certificate_budget_records": sum(
            int(
                delta is not None
                and delta["progress_loss_m"]
                > float(row["progress_budget_m"]) + TOL
            )
            for row, delta in zip(candidate0_rows, deltas, strict=True)
        ),
        "hard_gate_bool_worse_records": bool_worse,
    }


def _delta_stats(deltas: list[dict[str, Any] | None], field: str) -> dict[str, Any]:
    values = [
        float(delta[field])
        for delta in deltas
        if delta is not None and delta.get(field) is not None
    ]
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


def _rows_by_bucket(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets = row["context"].get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            if bucket not in SUPPORTED_SCENARIO_BUCKETS:
                raise ValueError(f"Unsupported scenario bucket: {bucket}")
            grouped[str(bucket)].append(row)
    return {bucket: grouped[bucket] for bucket in _ordered_buckets(grouped)}


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


def _example_rows(rows: list[dict[str, Any]], *, max_examples: int) -> list[dict[str, Any]]:
    if max_examples <= 0:
        return []
    rows = sorted(rows, key=_example_sort_key)
    examples = []
    for row in rows[:max_examples]:
        context = row["context"]
        examples.append(
            {
                "route_name": context["route_name"],
                "scenario_buckets": context["scenario_buckets"],
                "seed": context["seed"],
                "max_npcs": context["max_npcs"],
                "traffic_lights": context["traffic_lights"],
                "selection_step": row["selection_step"],
                "logged_selected": row["logged_selected"],
                "selected": row["selected"],
                "candidate_label_delta": row["candidate_label_delta"],
                "proxy_delta": row["proxy_delta"],
                "certificate_size": row["certificate_size"],
                "outcome_oracle_size": row["outcome_oracle_size"],
                "run_key": context["run_key"],
                "log_path": context["log_path"],
            }
        )
    return examples


def _example_sort_key(row: dict[str, Any]) -> tuple[float, int]:
    delta = row.get("candidate_label_delta") or {}
    cost = delta.get("candidate_label_safety_delta")
    return (float(cost) if cost is not None else 0.0, int(row["selection_step"]))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Top-1 Preserving Counterfactual Audit",
        "",
        "This is an offline audit only. Outcome labels are posterior evidence; "
        "they are not selector inputs.",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Rules",
        "",
        "| Rule | Override | True override | False override | Hidden outcome | "
        "Mean label safety delta | CVaR90 label safety delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rule in report["rules"]:
        overall = rule["overall"]
        safety = overall["candidate_label_safety_delta_overrides"]
        lines.append(
            f"| `{rule['name']}` | "
            f"{overall['override_records']} ({overall['override_rate']:.6f}) | "
            f"{overall['true_override_records']} "
            f"({overall['true_override_rate_among_overrides']:.6f}) | "
            f"{overall['false_override_records']} "
            f"({overall['false_override_rate_among_overrides']:.6f}) | "
            f"{overall['hidden_outcome_records']} "
            f"({overall['hidden_outcome_rate']:.6f}) | "
            f"{_fmt(safety['mean'])} | {_fmt(safety['cvar90'])} |"
        )
    for rule in report["rules"]:
        lines.extend(
            [
                "",
                f"## {rule['name']}",
                "",
                rule["description"],
                "",
                "### Overall",
                "",
                "```json",
                json.dumps(rule["overall"], indent=2, sort_keys=True),
                "```",
                "",
                "### Scenario Buckets",
                "",
                "| Bucket | Override | True override | False override | Hidden outcome | "
                "Mean safety delta |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in rule["by_bucket"]:
            safety = row["candidate_label_safety_delta_overrides"]
            lines.append(
                f"| `{row['bucket']}` | "
                f"{row['override_records']} ({row['override_rate']:.6f}) | "
                f"{row['true_override_records']} "
                f"({row['true_override_rate_among_overrides']:.6f}) | "
                f"{row['false_override_records']} "
                f"({row['false_override_rate_among_overrides']:.6f}) | "
                f"{row['hidden_outcome_records']} "
                f"({row['hidden_outcome_rate']:.6f}) | "
                f"{_fmt(safety['mean'])} |"
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
