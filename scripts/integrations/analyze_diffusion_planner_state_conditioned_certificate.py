#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
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
from scripts.integrations.analyze_diffusion_planner_hidden_outcome_gap import (  # noqa: E402
    _log_context,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)


TOL = 1e-12
DEFAULT_TICK_BIN_SIZE = 50
BOOL_OUTCOMES = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
OUTCOME_DELTA_FIELDS = (
    "progress_m",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
    "value",
)
SCREENS: tuple[dict[str, Any], ...] = (
    {
        "name": "state_guard_strict_005",
        "default_budgets": {
            "first_step_loss_m": 0.05,
            "h3_distance_loss_m": 0.05,
            "target_speed_loss_mps": 0.05,
        },
        "bucket_overrides": [],
        "require_raw_jerk_nondegrading": True,
    },
    {
        "name": "state_guard_balanced_010",
        "default_budgets": {
            "first_step_loss_m": 0.10,
            "h3_distance_loss_m": 0.10,
            "target_speed_loss_mps": 0.10,
        },
        "bucket_overrides": [
            {
                "if_any_bucket": ["traffic_light", "red_light_turn"],
                "budgets": {
                    "first_step_loss_m": 0.05,
                    "h3_distance_loss_m": 0.05,
                    "target_speed_loss_mps": 0.05,
                },
            }
        ],
        "require_raw_jerk_nondegrading": True,
    },
    {
        "name": "state_guard_relaxed_noncritical_025",
        "default_budgets": {
            "first_step_loss_m": 0.25,
            "h3_distance_loss_m": 0.10,
            "target_speed_loss_mps": 0.10,
        },
        "bucket_overrides": [
            {
                "if_any_bucket": ["sharp_turn"],
                "budgets": {
                    "first_step_loss_m": 0.10,
                    "h3_distance_loss_m": 0.10,
                    "target_speed_loss_mps": 0.10,
                },
            },
            {
                "if_any_bucket": ["traffic_light", "red_light_turn"],
                "budgets": {
                    "first_step_loss_m": 0.05,
                    "h3_distance_loss_m": 0.05,
                    "target_speed_loss_mps": 0.05,
                },
            },
        ],
        "require_raw_jerk_nondegrading": True,
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only state-conditioned finite-candidate certificate screen. "
            "It uses current-tick candidate descriptors for selection and "
            "candidate outcomes only for posterior audit."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--tick_bin_size", type=int, default=DEFAULT_TICK_BIN_SIZE)
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
        tick_bin_size=args.tick_bin_size,
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
    tick_bin_size: int = DEFAULT_TICK_BIN_SIZE,
) -> dict[str, Any]:
    if tick_bin_size <= 0:
        raise ValueError("tick_bin_size must be positive.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)

    rows_by_screen: dict[str, list[dict[str, Any]]] = {
        screen["name"]: [] for screen in SCREENS
    }
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
            step = int(record.get("selection_step", record_index))
            for screen in SCREENS:
                rows_by_screen[screen["name"]].append(
                    _screen_record(
                        loaded,
                        screen,
                        context=context,
                        selection_step=step,
                        tick_bin=_tick_bin(step, tick_bin_size),
                    )
                )

    return {
        "analysis": {
            "name": "dp_camp_state_conditioned_certificate_screen_v1",
            "role": (
                "offline default-off screen audit before any online "
                "finite-candidate selector"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are posterior labels only",
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "tick_bin_size": int(tick_bin_size),
            "screens": _screen_metadata(),
            "selection_rule": (
                "base feasible, union-red and red-stopping nonworse, first-step "
                "reach/H3 rollout/target-speed losses inside state-conditioned "
                "budgets, strict raw lateral improvement, optional raw jerk "
                "nondegradation; tie-break by raw lateral, raw jerk, descriptor "
                "losses, original CAMP score, then candidate index; retain "
                "baseline if no candidate is admissible"
            ),
            "math_boundary": (
                "All screen inputs are fixed current-tick finite-candidate "
                "constants. If later atomized with fixed nonnegative scales, "
                "CAMP scoring remains affine in w and the simplex/CVaR/L2 "
                "master remains convex. This audit is not classical Benders "
                "and makes no trajectory-coordinate convexity claim."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": total_records,
            "nonfallback": total_records - fallback_records,
            "fallback": fallback_records,
        },
        "screens": [
            _screen_report(screen_name, rows)
            for screen_name, rows in rows_by_screen.items()
        ],
    }


def _screen_metadata() -> list[dict[str, Any]]:
    return [
        {
            "name": screen["name"],
            "default_budgets": screen["default_budgets"],
            "bucket_overrides": screen["bucket_overrides"],
            "require_raw_jerk_nondegrading": screen["require_raw_jerk_nondegrading"],
        }
        for screen in SCREENS
    ]


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(record.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    if not isinstance(rollout, dict) or "3" not in rollout:
        raise ValueError(f"{label} is missing H3 open-loop rollout distance.")
    h3_payload = rollout["3"]
    if not isinstance(h3_payload, dict):
        raise ValueError(f"{label} H3 open-loop rollout must be an object.")
    return {
        "selected_index": selected,
        "feasible": _bool_vector(
            record.get("feasible_mask"),
            candidate_count,
            f"{label} feasible_mask",
        ),
        "outcomes": _outcomes(
            record.get("candidate_closed_loop_outcomes"),
            candidate_count,
            label,
        ),
        "selection_scores": _score_vector(
            record.get("selection_scores"),
            candidate_count,
            f"{label} selection_scores",
        ),
        "union_red": _vector(
            record.get("candidate_horizon_union_planned_red_light_cost"),
            candidate_count,
            f"{label} candidate_horizon_union_planned_red_light_cost",
        ),
        "red_stopping": _vector(
            record.get("candidate_red_stopping_margin_cost"),
            candidate_count,
            f"{label} candidate_red_stopping_margin_cost",
        ),
        "first_step_reach": _vector(
            record.get("candidate_perfect_tracker_first_step_reach_m"),
            candidate_count,
            f"{label} candidate_perfect_tracker_first_step_reach_m",
        ),
        "target_speed": _vector(
            record.get("candidate_perfect_tracker_target_speed_mps"),
            candidate_count,
            f"{label} candidate_perfect_tracker_target_speed_mps",
        ),
        "h3_distance": _vector(
            h3_payload.get("distance_m"),
            candidate_count,
            f"{label} H3 rollout distance_m",
        ),
        "raw_lateral": _vector(
            record.get("candidate_horizon_lateral_acceleration_cost"),
            candidate_count,
            f"{label} candidate_horizon_lateral_acceleration_cost",
        ),
        "raw_jerk": _vector(
            record.get("candidate_dp_prior_jerk_excess_cost"),
            candidate_count,
            f"{label} candidate_dp_prior_jerk_excess_cost",
        ),
    }


def _screen_record(
    record: dict[str, Any],
    screen: dict[str, Any],
    *,
    context: dict[str, Any],
    selection_step: int,
    tick_bin: str,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    fallback = not record["feasible"].any()
    budgets = _state_budgets(screen, context["scenario_buckets"])
    admissible = (
        np.zeros_like(record["feasible"], dtype=bool)
        if fallback
        else _admissible_mask(record, screen, budgets)
    )
    chosen = _choose(record, admissible) if admissible.any() else selected
    row = _result_row(record, chosen, fallback=fallback, opportunity=bool(admissible.any()))
    row.update(
        {
            "context": context,
            "selection_step": int(selection_step),
            "tick_bin": tick_bin,
            "budgets": budgets,
        }
    )
    return row


def _state_budgets(screen: dict[str, Any], buckets: list[str]) -> dict[str, float]:
    budgets = {
        key: float(value)
        for key, value in screen["default_budgets"].items()
    }
    bucket_set = set(buckets)
    for override in screen["bucket_overrides"]:
        if bucket_set & set(override["if_any_bucket"]):
            for key, value in override["budgets"].items():
                budgets[key] = min(budgets[key], float(value))
    return budgets


def _admissible_mask(
    record: dict[str, Any],
    screen: dict[str, Any],
    budgets: dict[str, float],
) -> np.ndarray:
    selected = int(record["selected_index"])
    first_step_loss = _loss(record["first_step_reach"], selected)
    h3_loss = _loss(record["h3_distance"], selected)
    target_loss = _loss(record["target_speed"], selected)
    admissible = (
        record["feasible"].copy()
        & (record["union_red"] <= record["union_red"][selected] + TOL)
        & (record["red_stopping"] <= record["red_stopping"][selected] + TOL)
        & (first_step_loss <= budgets["first_step_loss_m"] + TOL)
        & (h3_loss <= budgets["h3_distance_loss_m"] + TOL)
        & (target_loss <= budgets["target_speed_loss_mps"] + TOL)
        & (record["raw_lateral"] < record["raw_lateral"][selected] - TOL)
    )
    if bool(screen["require_raw_jerk_nondegrading"]):
        admissible &= record["raw_jerk"] <= record["raw_jerk"][selected] + TOL
    admissible[selected] = False
    return admissible


def _choose(record: dict[str, Any], admissible: np.ndarray) -> int:
    indices = np.flatnonzero(admissible)
    selected = int(record["selected_index"])
    first_step_loss = _loss(record["first_step_reach"], selected)
    h3_loss = _loss(record["h3_distance"], selected)
    target_loss = _loss(record["target_speed"], selected)
    order = np.lexsort(
        (
            indices,
            record["selection_scores"][indices],
            target_loss[indices],
            h3_loss[indices],
            first_step_loss[indices],
            record["raw_jerk"][indices],
            record["raw_lateral"][indices],
        )
    )
    return int(indices[order[0]])


def _result_row(
    record: dict[str, Any],
    chosen: int,
    *,
    fallback: bool,
    opportunity: bool,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    row: dict[str, Any] = {
        "fallback": bool(fallback),
        "opportunity": bool(opportunity),
        "changed": bool(chosen != selected),
        "selected_index": selected,
        "chosen_index": int(chosen),
        "first_step_loss_m": float(_loss(record["first_step_reach"], selected)[chosen]),
        "h3_distance_loss_m": float(_loss(record["h3_distance"], selected)[chosen]),
        "target_speed_loss_mps": float(_loss(record["target_speed"], selected)[chosen]),
        "raw_lateral_delta": float(record["raw_lateral"][chosen] - record["raw_lateral"][selected]),
        "raw_jerk_delta": float(record["raw_jerk"][chosen] - record["raw_jerk"][selected]),
        "union_red_delta": float(record["union_red"][chosen] - record["union_red"][selected]),
        "red_stopping_delta": float(record["red_stopping"][chosen] - record["red_stopping"][selected]),
    }
    for field in OUTCOME_DELTA_FIELDS:
        row[f"outcome_{field}_delta"] = _outcome_number(record, chosen, field) - _outcome_number(
            record,
            selected,
            field,
        )
    safety_regressions = _outcome_safety_regressions(record, chosen)
    row["outcome_safety_regression"] = bool(safety_regressions)
    row["outcome_safety_regression_fields"] = safety_regressions
    row["posterior_joint_comfort_improvement"] = (
        row["outcome_mean_jerk_mps3_delta"] < -TOL
        and row["outcome_mean_lateral_acceleration_mps2_delta"] < -TOL
        and not row["outcome_safety_regression"]
    )
    return row


def _screen_report(screen_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    nonfallback = [row for row in rows if not row["fallback"]]
    return {
        "name": screen_name,
        "overall": _summarize_rows(nonfallback),
        "by_bucket": _group_report(
            nonfallback,
            lambda row: row["context"]["scenario_buckets"],
            multi=True,
        ),
        "by_route": _group_report(
            nonfallback,
            lambda row: row["context"]["route_name"],
        ),
        "by_tick_bin": _group_report(nonfallback, lambda row: row["tick_bin"]),
        "changed_delta_summary": _delta_summary(
            [row for row in nonfallback if row["changed"]]
        ),
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    changed = [row for row in rows if row["changed"]]
    safety = [row for row in changed if row["outcome_safety_regression"]]
    posterior_joint = [
        row for row in changed if row["posterior_joint_comfort_improvement"]
    ]
    regression_fields = defaultdict(int)
    for row in safety:
        for field in row["outcome_safety_regression_fields"]:
            regression_fields[field] += 1
    return {
        "records": len(rows),
        "changed": len(changed),
        "opportunity": sum(int(row["opportunity"]) for row in rows),
        "change_rate": len(changed) / max(len(rows), 1),
        "posterior_joint_comfort_improvements": len(posterior_joint),
        "posterior_joint_comfort_rate": len(posterior_joint) / max(len(changed), 1),
        "outcome_safety_regressions": len(safety),
        "outcome_safety_regression_rate": len(safety) / max(len(changed), 1),
        "outcome_safety_regression_fields": dict(sorted(regression_fields.items())),
    }


def _group_report(rows: list[dict[str, Any]], key_fn, *, multi: bool = False) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        keys = key_fn(row)
        if not multi:
            keys = [keys]
        for key in keys:
            groups[str(key)].append(row)
    result = [
        {"group": key, **_summarize_rows(group)}
        for key, group in sorted(groups.items())
    ]
    result.sort(key=lambda item: (-int(item["changed"]), item["group"]))
    return result


def _delta_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields = (
        "outcome_progress_m_delta",
        "outcome_mean_jerk_mps3_delta",
        "outcome_mean_lateral_acceleration_mps2_delta",
        "first_step_loss_m",
        "h3_distance_loss_m",
        "target_speed_loss_mps",
        "raw_lateral_delta",
        "raw_jerk_delta",
        "union_red_delta",
        "red_stopping_delta",
    )
    return {
        field: _stats([float(row[field]) for row in rows])
        for field in fields
    }


def _loss(values: np.ndarray, selected: int) -> np.ndarray:
    return np.maximum(0.0, values[selected] - values)


def _outcome_safety_regressions(record: dict[str, Any], chosen: int) -> list[str]:
    selected = int(record["selected_index"])
    return [
        field
        for field in BOOL_OUTCOMES
        if bool(record["outcomes"][chosen].get(field))
        and not bool(record["outcomes"][selected].get(field))
    ]


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite values.")
    if np.any(array < 0.0):
        raise ValueError(f"{label} must be nonnegative.")
    return array


def _score_vector(values: Any, size: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    return np.nan_to_num(array, nan=1.0e12, posinf=1.0e12, neginf=-1.0e12)


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _outcome_number(record: dict[str, Any], index: int, field: str) -> float:
    value = float(record["outcomes"][index].get(field))
    if not np.isfinite(value):
        raise ValueError(f"Outcome {field} must be finite.")
    return value


def _tick_bin(selection_step: int, tick_bin_size: int) -> str:
    start = (int(selection_step) // tick_bin_size) * tick_bin_size
    end = start + tick_bin_size - 1
    return f"{start:04d}-{end:04d}"


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "p50": None,
            "p90": None,
            "p95": None,
            "min": None,
            "max": None,
        }
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "mean": float(np.mean(array)),
        "p50": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
        "p95": float(np.percentile(array, 95)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    lines = [
        "# DP CAMP State-Conditioned Certificate Screen",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- Fallback records: {records['fallback']}",
        "",
        "This is a read-only default-off audit. It uses fixed current-tick "
        "finite-candidate fields for the screen and candidate outcomes only "
        "for posterior evaluation.",
        "",
        "| Screen | Changed | Change rate | Posterior joint comfort | Safety regressions | Progress delta mean | Jerk delta mean | Lateral delta mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for screen in report["screens"]:
        overall = screen["overall"]
        deltas = screen["changed_delta_summary"]
        lines.append(
            "| `{name}` | {changed} | {change_rate:.6f} | {joint} "
            "({joint_rate:.6f}) | {safety} ({safety_rate:.6f}) | "
            "{progress} | {jerk} | {lateral} |".format(
                name=screen["name"],
                changed=overall["changed"],
                change_rate=overall["change_rate"],
                joint=overall["posterior_joint_comfort_improvements"],
                joint_rate=overall["posterior_joint_comfort_rate"],
                safety=overall["outcome_safety_regressions"],
                safety_rate=overall["outcome_safety_regression_rate"],
                progress=_fmt(deltas["outcome_progress_m_delta"]["mean"]),
                jerk=_fmt(deltas["outcome_mean_jerk_mps3_delta"]["mean"]),
                lateral=_fmt(
                    deltas["outcome_mean_lateral_acceleration_mps2_delta"]["mean"]
                ),
            )
        )
    for screen in report["screens"]:
        lines.extend(
            [
                "",
                f"## {screen['name']}",
                "",
                "### By bucket",
                "",
                _group_table(screen["by_bucket"]),
                "",
                "### By route",
                "",
                _group_table(screen["by_route"]),
                "",
                "### By tick bin",
                "",
                _group_table(screen["by_tick_bin"]),
            ]
        )
    lines.extend(
        [
            "",
            "## Mathematical boundary",
            "",
            str(report["analysis"]["math_boundary"]),
            "",
        ]
    )
    return "\n".join(lines)


def _group_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Group | Records | Changed | Change rate | Posterior joint comfort | Safety regressions |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| `{group}` | {records} | {changed} | {change_rate:.6f} | "
            "{joint} ({joint_rate:.6f}) | {safety} ({safety_rate:.6f}) |".format(
                group=row["group"],
                records=row["records"],
                changed=row["changed"],
                change_rate=row["change_rate"],
                joint=row["posterior_joint_comfort_improvements"],
                joint_rate=row["posterior_joint_comfort_rate"],
                safety=row["outcome_safety_regressions"],
                safety_rate=row["outcome_safety_regression_rate"],
            )
        )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.6f}"


if __name__ == "__main__":
    main()
