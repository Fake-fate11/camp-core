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


TOTAL_FIELD = "latency_ms_including_candidate_generation"
DEFAULT_MIN_PROGRESS_RATIO = 0.8
DEFAULT_RED_THRESHOLD = 0.5
MAX_EXAMPLES = 12

REWARD_LATENCY_FIELDS = (
    "latency_ms_reward_scoring",
    "latency_ms_reward_batch_compute",
    "latency_ms_reward_sg_smoothing",
    "latency_ms_reward_route_progress",
    "latency_ms_reward_npz_dump",
    "latency_ms_reward_tensor_setup",
    "latency_ms_reward_candidate_tensor_transfer",
    "latency_ms_reward_postprocess",
    "latency_ms_reward_full_horizon_red_light",
    "latency_ms_reward_red_route_points",
    "latency_ms_reward_feasibility",
    "latency_ms_reward_field_extraction",
)

LATENCY_PLAN_FIELDS = {
    "remove_reward_batch_compute": ("latency_ms_reward_batch_compute",),
    "cache_route_progress": ("latency_ms_reward_route_progress",),
    "reuse_sg_smoothed_candidates": ("latency_ms_reward_sg_smoothing",),
    "batch_plus_route_progress": (
        "latency_ms_reward_batch_compute",
        "latency_ms_reward_route_progress",
    ),
    "batch_plus_route_progress_plus_sg": (
        "latency_ms_reward_batch_compute",
        "latency_ms_reward_route_progress",
        "latency_ms_reward_sg_smoothing",
    ),
}

MASK_PLANS = (
    {
        "name": "route_progress_underprogress",
        "red_source": "dp_near_red",
        "progress_source": "candidate_route_progress",
        "description": (
            "Keep DP reward hard gates, but replace DP reward progress with "
            "candidate_route_progress for the underprogress gate."
        ),
    },
    {
        "name": "full_red_hard_dp_progress",
        "red_source": "candidate_full_horizon_planned_red_light_cost",
        "progress_source": "dp_reward_progress",
        "description": (
            "Replace DP reward near-red hard gate with full-horizon red-light "
            "cost, while keeping DP reward progress."
        ),
    },
    {
        "name": "full_red_route_progress",
        "red_source": "candidate_full_horizon_planned_red_light_cost",
        "progress_source": "candidate_route_progress",
        "description": (
            "Use full-horizon red-light cost and candidate_route_progress; "
            "non-red hard gates still come from DP reward."
        ),
    },
    {
        "name": "union_red_route_progress_diagnostic",
        "red_source": "candidate_horizon_union_planned_red_light_cost",
        "progress_source": "candidate_route_progress",
        "description": (
            "Diagnostic-only: use the logged union red-light certificate and "
            "candidate_route_progress. Union red still depends on DP near-red "
            "logging in current artifacts."
        ),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only feasibility and latency audit for DP reward scoring "
            "replacement/cache plans. This never selects trajectories."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--min_progress_ratio",
        type=float,
        default=DEFAULT_MIN_PROGRESS_RATIO,
    )
    parser.add_argument("--red_threshold", type=float, default=DEFAULT_RED_THRESHOLD)
    parser.add_argument("--max_examples", type=int, default=MAX_EXAMPLES)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        min_progress_ratio=args.min_progress_ratio,
        red_threshold=args.red_threshold,
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
    label: str | None = None,
    min_progress_ratio: float = DEFAULT_MIN_PROGRESS_RATIO,
    red_threshold: float = DEFAULT_RED_THRESHOLD,
    max_examples: int = MAX_EXAMPLES,
) -> dict[str, Any]:
    if min_progress_ratio < 0.0:
        raise ValueError("min_progress_ratio must be nonnegative.")
    if red_threshold < 0.0:
        raise ValueError("red_threshold must be nonnegative.")
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")

    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    rows: list[dict[str, Any]] = []
    missing: Counter[str] = Counter()
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        for record_index, raw_record in enumerate(payload):
            if not isinstance(raw_record, dict):
                continue
            label_text = f"{log_path}#{record_index}"
            row = _load_row(
                raw_record,
                label=label_text,
                log_path=log_path,
                record_index=record_index,
                min_progress_ratio=min_progress_ratio,
                red_threshold=red_threshold,
                missing=missing,
            )
            if row is not None:
                rows.append(row)

    if not rows:
        raise ValueError("No records with reward candidates were found.")

    baseline = _baseline_report(rows)
    plans = [
        _mask_plan_report(
            rows,
            plan,
            min_progress_ratio=min_progress_ratio,
            red_threshold=red_threshold,
            max_examples=max_examples,
        )
        for plan in MASK_PLANS
    ]
    return {
        "analysis": {
            "name": "dp_camp_reward_replacement_plan_audit_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "dp_modification": False,
            "closed_loop_outcome_labels_used": False,
            "min_progress_ratio": float(min_progress_ratio),
            "red_threshold": float(red_threshold),
            "math_boundary": (
                "This audit compares fixed current-tick logged candidate "
                "quantities. It does not define atoms, constraints, Benders "
                "subproblems, cuts, or online selector inputs."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(rows),
            "candidate_total": int(sum(row["candidate_count"] for row in rows)),
            "fallback_records": int(sum(int(not row["logged_feasible"].any()) for row in rows)),
            "nonfallback_records": int(sum(int(row["logged_feasible"].any()) for row in rows)),
        },
        "field_coverage": _field_coverage(rows),
        "missing": dict(sorted(missing.items())),
        "baseline_dp_reward": baseline,
        "progress_alignment": _progress_alignment(rows),
        "red_alignment": _red_alignment(rows),
        "mask_plans": plans,
        "latency": _latency_report(rows),
        "decision_hint": _decision_hint(plans),
    }


def _load_row(
    record: dict[str, Any],
    *,
    label: str,
    log_path: Path,
    record_index: int,
    min_progress_ratio: float,
    red_threshold: float,
    missing: Counter[str],
) -> dict[str, Any] | None:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or not rewards:
        missing["dp_candidate_rewards"] += 1
        return None
    candidate_count = len(rewards)
    dp_progress = np.asarray(
        [_finite(reward.get("progress")) for reward in rewards],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(dp_progress)):
        missing["dp_reward_progress"] += 1
        return None
    logged_feasible = _bool_vector(
        record.get("feasible_mask"),
        candidate_count,
        "feasible_mask",
        missing,
    )
    if logged_feasible is None:
        logged_feasible = np.ones(candidate_count, dtype=bool)

    hard_mask, hard_reasons = _hard_mask(
        rewards,
        red_cost=_red_cost_vector(record, "dp_near_red", candidate_count, missing),
        red_threshold=red_threshold,
    )
    baseline_mask, baseline_reasons = _apply_underprogress(
        hard_mask,
        hard_reasons,
        dp_progress,
        min_progress_ratio=min_progress_ratio,
        reason="dp_underprogress",
    )

    return {
        "label": label,
        "log_path": str(log_path),
        "record_index": int(record_index),
        "selection_step": int(record.get("selection_step", record_index)),
        "candidate_count": int(candidate_count),
        "selected_index": _optional_int(record.get("selected_index")),
        "logged_feasible": logged_feasible,
        "rewards": rewards,
        "dp_progress": dp_progress,
        "route_progress": _optional_vector(
            record.get("candidate_route_progress"),
            candidate_count,
            "candidate_route_progress",
            missing,
        ),
        "near_red": _red_cost_vector(record, "dp_near_red", candidate_count, missing),
        "full_red": _red_cost_vector(
            record,
            "candidate_full_horizon_planned_red_light_cost",
            candidate_count,
            missing,
        ),
        "union_red": _red_cost_vector(
            record,
            "candidate_horizon_union_planned_red_light_cost",
            candidate_count,
            missing,
        ),
        "hard_mask": hard_mask,
        "hard_reasons": hard_reasons,
        "baseline_mask": baseline_mask,
        "baseline_reasons": baseline_reasons,
        "latencies": {
            field: _finite(record.get(field))
            for field in (TOTAL_FIELD, *REWARD_LATENCY_FIELDS)
        },
    }


def _hard_mask(
    rewards: list[dict[str, Any]],
    *,
    red_cost: np.ndarray | None,
    red_threshold: float,
) -> tuple[np.ndarray, tuple[tuple[str, ...], ...]]:
    feasible = np.ones(len(rewards), dtype=bool)
    reasons: list[list[str]] = [[] for _ in rewards]
    for idx, reward in enumerate(rewards):
        checks = (
            ("dp_collision", reward.get("collision_step") is not None),
            ("dp_road_border", bool(reward.get("rb_crossing", False))),
            ("dp_lane_crossing", bool(reward.get("lane_crossing", False))),
            ("dp_static_collision", bool(reward.get("static_crossing", False))),
            ("dp_kinematic", bool(reward.get("kinematic_violated", False))),
            (
                "dp_red_light",
                bool(red_cost is not None and red_cost[idx] > red_threshold),
            ),
        )
        for reason, failed in checks:
            if failed:
                reasons[idx].append(reason)
        feasible[idx] = not reasons[idx]
    return feasible, tuple(tuple(row) for row in reasons)


def _apply_underprogress(
    hard_mask: np.ndarray,
    hard_reasons: tuple[tuple[str, ...], ...],
    progress: np.ndarray | None,
    *,
    min_progress_ratio: float,
    reason: str,
) -> tuple[np.ndarray, tuple[tuple[str, ...], ...]]:
    feasible = np.asarray(hard_mask, dtype=bool).copy()
    reasons = [list(row) for row in hard_reasons]
    if progress is None or progress.shape != feasible.shape or not np.all(np.isfinite(progress)):
        return feasible, tuple(tuple(row) for row in reasons)
    safe_indices = np.flatnonzero(feasible)
    if safe_indices.size:
        best_progress = float(np.max(progress[safe_indices]))
        if best_progress > 0.0:
            minimum_progress = best_progress * float(min_progress_ratio)
            for idx in safe_indices:
                if float(progress[idx]) < minimum_progress:
                    feasible[idx] = False
                    reasons[idx].append(reason)
    return feasible, tuple(tuple(row) for row in reasons)


def _mask_plan_report(
    rows: list[dict[str, Any]],
    plan: dict[str, str],
    *,
    min_progress_ratio: float,
    red_threshold: float,
    max_examples: int,
) -> dict[str, Any]:
    candidate_mismatches = 0
    false_feasible = 0
    false_infeasible = 0
    record_mismatches = 0
    selected_changes = 0
    examples: list[dict[str, Any]] = []
    missing_records = 0
    reason_counts: Counter[str] = Counter()

    for row in rows:
        progress = _progress_for_plan(row, plan["progress_source"])
        red_cost = _red_for_plan(row, plan["red_source"])
        if progress is None or red_cost is None:
            missing_records += 1
            continue
        hard_mask, hard_reasons = _hard_mask(
            row["rewards"],
            red_cost=red_cost,
            red_threshold=red_threshold,
        )
        candidate_mask, candidate_reasons = _apply_underprogress(
            hard_mask,
            hard_reasons,
            progress,
            min_progress_ratio=min_progress_ratio,
            reason=f"{plan['progress_source']}_underprogress",
        )
        baseline = row["baseline_mask"]
        mismatch = candidate_mask != baseline
        if mismatch.any():
            record_mismatches += 1
            candidate_mismatches += int(mismatch.sum())
            false_feasible += int(np.logical_and(candidate_mask, ~baseline).sum())
            false_infeasible += int(np.logical_and(~candidate_mask, baseline).sum())
            for idx in np.flatnonzero(mismatch):
                direction = "false_feasible_vs_dp_reward" if candidate_mask[idx] else "false_infeasible_vs_dp_reward"
                reason_counts[direction] += 1
                if len(examples) < max_examples:
                    examples.append(
                        {
                            "log_path": row["log_path"],
                            "record_index": row["record_index"],
                            "selection_step": row["selection_step"],
                            "candidate_index": int(idx),
                            "direction": direction,
                            "baseline_reasons": list(row["baseline_reasons"][idx]),
                            "candidate_reasons": list(candidate_reasons[idx]),
                            "dp_progress": float(row["dp_progress"][idx]),
                            "route_progress": (
                                None
                                if row["route_progress"] is None
                                else float(row["route_progress"][idx])
                            ),
                            "near_red": (
                                None
                                if row["near_red"] is None
                                else float(row["near_red"][idx])
                            ),
                            "full_red": (
                                None
                                if row["full_red"] is None
                                else float(row["full_red"][idx])
                            ),
                            "union_red": (
                                None
                                if row["union_red"] is None
                                else float(row["union_red"][idx])
                            ),
                        }
                    )
        selected = row["selected_index"]
        if selected is not None and 0 <= selected < row["candidate_count"]:
            if bool(candidate_mask[selected]) != bool(baseline[selected]):
                selected_changes += 1

    total_candidates = int(sum(row["candidate_count"] for row in rows))
    return {
        "name": plan["name"],
        "description": plan["description"],
        "red_source": plan["red_source"],
        "progress_source": plan["progress_source"],
        "records": len(rows),
        "missing_records": int(missing_records),
        "record_mismatches": int(record_mismatches),
        "candidate_mismatches": int(candidate_mismatches),
        "candidate_mismatch_rate": (
            float(candidate_mismatches / total_candidates) if total_candidates else 0.0
        ),
        "false_feasible_vs_dp_reward": int(false_feasible),
        "false_infeasible_vs_dp_reward": int(false_infeasible),
        "selected_candidate_mask_changes": int(selected_changes),
        "reason_counts": dict(sorted(reason_counts.items())),
        "examples": examples,
        "acceptability_hint": (
            "not_equivalent_to_dp_reward_baseline"
            if candidate_mismatches
            else "mask_equivalent_on_this_artifact"
        ),
    }


def _baseline_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hard_reason_counts: Counter[str] = Counter()
    final_reason_counts: Counter[str] = Counter()
    hard_feasible = 0
    baseline_feasible = 0
    logged_mismatch_records = 0
    for row in rows:
        hard_feasible += int(row["hard_mask"].sum())
        baseline_feasible += int(row["baseline_mask"].sum())
        if row["logged_feasible"].shape == row["baseline_mask"].shape:
            logged_mismatch_records += int(
                not np.array_equal(row["logged_feasible"], row["baseline_mask"])
            )
        for reasons in row["hard_reasons"]:
            hard_reason_counts.update(reasons)
        for reasons in row["baseline_reasons"]:
            final_reason_counts.update(reasons)
    return {
        "hard_feasible_candidates": int(hard_feasible),
        "dp_reward_feasible_candidates": int(baseline_feasible),
        "hard_reason_counts": dict(sorted(hard_reason_counts.items())),
        "final_reason_counts": dict(sorted(final_reason_counts.items())),
        "logged_mask_mismatch_records": int(logged_mismatch_records),
        "note": (
            "logged feasible_mask can include CAMP internal gates, so the "
            "dp_reward baseline is used only for reward replacement comparisons."
        ),
    }


def _progress_alignment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas: list[float] = []
    ratios: list[float] = []
    missing = 0
    for row in rows:
        route = row["route_progress"]
        if route is None:
            missing += 1
            continue
        delta = route - row["dp_progress"]
        deltas.extend(float(value) for value in delta)
        for route_value, dp_value in zip(route, row["dp_progress"], strict=True):
            if abs(float(dp_value)) > 1e-12:
                ratios.append(float(route_value) / float(dp_value))
    return {
        "records_with_missing_route_progress": int(missing),
        "route_minus_dp_progress_m": _summary(deltas),
        "route_over_dp_progress_ratio": _summary(ratios),
    }


def _red_alignment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "full_minus_near_red_cost": _paired_delta(rows, "full_red", "near_red"),
        "union_minus_near_red_cost": _paired_delta(rows, "union_red", "near_red"),
    }


def _latency_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_values = _values(rows, TOTAL_FIELD)
    baseline_p95 = _percentile(total_values, 95.0) if total_values else None
    component_summaries = {
        field: _summary(_values(rows, field)) for field in REWARD_LATENCY_FIELDS
    }
    plans: dict[str, Any] = {}
    for name, fields in LATENCY_PLAN_FIELDS.items():
        adjusted: list[float] = []
        removed: list[float] = []
        for row in rows:
            total = row["latencies"].get(TOTAL_FIELD)
            if total is None:
                continue
            component_sum = sum(
                float(row["latencies"].get(field) or 0.0) for field in fields
            )
            adjusted.append(max(float(total) - component_sum, 0.0))
            removed.append(component_sum)
        adjusted_summary = _summary(adjusted)
        adjusted_p95 = adjusted_summary["p95"]
        plans[name] = {
            "removed_fields": list(fields),
            "removed_component_ms": _summary(removed),
            "p95_if_removed_ms": adjusted_p95,
            "p95_reduction_ms": (
                None
                if baseline_p95 is None or adjusted_p95 is None
                else float(baseline_p95 - adjusted_p95)
            ),
        }
    return {
        "baseline_total_p95_ms": baseline_p95,
        "components_ms": component_summaries,
        "hypothetical_plans": plans,
        "note": (
            "Latency plans subtract measured logged components only. They are "
            "upper-bound engineering diagnostics, not proof that a replacement "
            "is semantically valid."
        ),
    }


def _decision_hint(plans: list[dict[str, Any]]) -> str:
    unsafe = [
        plan["name"]
        for plan in plans
        if plan["false_feasible_vs_dp_reward"] or plan["missing_records"]
    ]
    if unsafe:
        return (
            "reject_direct_reward_replacement_until_false_feasible_and_missing_"
            f"cases_are_resolved: {', '.join(unsafe)}"
        )
    return "candidate_masks_equivalent_on_this_artifact_but_require_broader_grid"


def _field_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    fields = {
        "candidate_route_progress": "route_progress",
        "candidate_full_horizon_planned_red_light_cost": "full_red",
        "candidate_horizon_union_planned_red_light_cost": "union_red",
    }
    result = {}
    for field, key in fields.items():
        records = sum(int(row[key] is not None) for row in rows)
        result[field] = {
            "records": int(records),
            "rate": float(records / max(total, 1)),
        }
    return result


def _red_cost_vector(
    record: dict[str, Any],
    source: str,
    candidate_count: int,
    missing: Counter[str],
) -> np.ndarray | None:
    if source == "dp_near_red":
        rewards = record.get("dp_candidate_rewards")
        if not isinstance(rewards, list) or len(rewards) != candidate_count:
            missing["dp_near_red"] += 1
            return None
        return np.asarray(
            [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in rewards],
            dtype=np.float64,
        )
    return _optional_vector(record.get(source), candidate_count, source, missing)


def _progress_for_plan(row: dict[str, Any], source: str) -> np.ndarray | None:
    if source == "dp_reward_progress":
        return row["dp_progress"]
    if source == "candidate_route_progress":
        return row["route_progress"]
    raise ValueError(f"Unsupported progress source: {source}")


def _red_for_plan(row: dict[str, Any], source: str) -> np.ndarray | None:
    if source == "dp_near_red":
        return row["near_red"]
    if source == "candidate_full_horizon_planned_red_light_cost":
        return row["full_red"]
    if source == "candidate_horizon_union_planned_red_light_cost":
        return row["union_red"]
    raise ValueError(f"Unsupported red source: {source}")


def _paired_delta(rows: list[dict[str, Any]], lhs: str, rhs: str) -> dict[str, Any]:
    deltas: list[float] = []
    missing = 0
    for row in rows:
        left = row[lhs]
        right = row[rhs]
        if left is None or right is None:
            missing += 1
            continue
        deltas.extend(float(value) for value in left - right)
    return {"missing_records": int(missing), "delta": _summary(deltas)}


def _values(rows: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row["latencies"].get(field)
        if value is not None:
            values.append(float(value))
    return values


def _summary(values: list[float]) -> dict[str, Any]:
    finite = [float(value) for value in values if np.isfinite(value)]
    if not finite:
        return {"n": 0, "mean": None, "p50": None, "p95": None, "min": None, "max": None}
    arr = np.asarray(finite, dtype=np.float64)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def _percentile(values: list[float], percentile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), percentile))


def _optional_vector(
    value: Any,
    expected: int,
    field: str,
    missing: Counter[str],
) -> np.ndarray | None:
    if not isinstance(value, list) or len(value) != expected:
        missing[field] += 1
        return None
    result = np.asarray([_finite(item) for item in value], dtype=np.float64)
    if not np.all(np.isfinite(result)):
        missing[field] += 1
        return None
    return result


def _bool_vector(
    value: Any,
    expected: int,
    field: str,
    missing: Counter[str],
) -> np.ndarray | None:
    if not isinstance(value, list) or len(value) != expected:
        missing[field] += 1
        return None
    return np.asarray([bool(item) for item in value], dtype=bool)


def _finite(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        return float("nan")
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return result if np.isfinite(result) else float("nan")


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Reward Replacement Plan Audit",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Records",
        "",
        "| Logs | Records | Candidates | Nonfallback | Fallback |",
        "| ---: | ---: | ---: | ---: | ---: |",
        (
            f"| {report['records']['logs']} | {report['records']['total']} | "
            f"{report['records']['candidate_total']} | "
            f"{report['records']['nonfallback_records']} | "
            f"{report['records']['fallback_records']} |"
        ),
        "",
        "## Mask Plans",
        "",
        "| Plan | Candidate Mismatches | False Feasible | False Infeasible | Missing Records | Hint |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for plan in report["mask_plans"]:
        lines.append(
            "| "
            f"`{plan['name']}` | {plan['candidate_mismatches']} | "
            f"{plan['false_feasible_vs_dp_reward']} | "
            f"{plan['false_infeasible_vs_dp_reward']} | "
            f"{plan['missing_records']} | `{plan['acceptability_hint']}` |"
        )
    lines.extend(
        [
            "",
            "## Latency Plans",
            "",
            "| Plan | P95 If Removed | P95 Reduction | Removed Fields |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for name, plan in report["latency"]["hypothetical_plans"].items():
        lines.append(
            "| "
            f"`{name}` | {_fmt(plan['p95_if_removed_ms'])} | "
            f"{_fmt(plan['p95_reduction_ms'])} | "
            f"`{', '.join(plan['removed_fields'])}` |"
        )
    lines.extend(
        [
            "",
            "## Decision Hint",
            "",
            f"`{report['decision_hint']}`",
            "",
            "## Progress Alignment",
            "",
            "```json",
            json.dumps(report["progress_alignment"], indent=2, sort_keys=True),
            "```",
            "",
            "## Red Alignment",
            "",
            "```json",
            json.dumps(report["red_alignment"], indent=2, sort_keys=True),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return "`null`"
    return f"`{float(value):.6f}`"


if __name__ == "__main__":
    main()
