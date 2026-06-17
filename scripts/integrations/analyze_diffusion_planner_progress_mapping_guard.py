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


DEFAULT_MIN_PROGRESS_RATIO = 0.8
DEFAULT_RED_THRESHOLD = 0.5
DEFAULT_ROUTE_BEST_RATIOS = (0.8, 0.9, 0.95, 0.98, 1.0)
DEFAULT_ROUTE_BEST_LOSS_BUDGETS_M = (0.0, 0.05, 0.1, 0.2, 0.5, 1.0)
DEFAULT_CANDIDATE0_RATIOS = (0.8, 0.9, 0.95, 0.98, 1.0)
DEFAULT_CANDIDATE0_LOSS_BUDGETS_M = (0.0, 0.05, 0.1, 0.2, 0.5, 1.0)
MAX_EXAMPLES = 12
TOL = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit for route-progress-to-DP-progress mapping and "
            "guard candidates. This compares fixed current-tick route progress "
            "guards against the reconstructed DP reward underprogress mask."
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
    parser.add_argument(
        "--route_best_ratio",
        type=float,
        action="append",
        default=[],
        help="Repeat to override route-best ratio guards.",
    )
    parser.add_argument(
        "--route_best_loss_budget_m",
        type=float,
        action="append",
        default=[],
        help="Repeat to override route-best absolute loss-budget guards.",
    )
    parser.add_argument(
        "--candidate0_ratio",
        type=float,
        action="append",
        default=[],
        help="Repeat to override candidate0-relative ratio guards.",
    )
    parser.add_argument(
        "--candidate0_loss_budget_m",
        type=float,
        action="append",
        default=[],
        help="Repeat to override candidate0-relative loss-budget guards.",
    )
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
        route_best_ratios=tuple(args.route_best_ratio) or DEFAULT_ROUTE_BEST_RATIOS,
        route_best_loss_budgets_m=(
            tuple(args.route_best_loss_budget_m)
            or DEFAULT_ROUTE_BEST_LOSS_BUDGETS_M
        ),
        candidate0_ratios=tuple(args.candidate0_ratio) or DEFAULT_CANDIDATE0_RATIOS,
        candidate0_loss_budgets_m=(
            tuple(args.candidate0_loss_budget_m)
            or DEFAULT_CANDIDATE0_LOSS_BUDGETS_M
        ),
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
    route_best_ratios: tuple[float, ...] = DEFAULT_ROUTE_BEST_RATIOS,
    route_best_loss_budgets_m: tuple[float, ...] = DEFAULT_ROUTE_BEST_LOSS_BUDGETS_M,
    candidate0_ratios: tuple[float, ...] = DEFAULT_CANDIDATE0_RATIOS,
    candidate0_loss_budgets_m: tuple[float, ...] = DEFAULT_CANDIDATE0_LOSS_BUDGETS_M,
    max_examples: int = MAX_EXAMPLES,
) -> dict[str, Any]:
    if min_progress_ratio < 0.0:
        raise ValueError("min_progress_ratio must be nonnegative.")
    if red_threshold < 0.0:
        raise ValueError("red_threshold must be nonnegative.")
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")
    _validate_grid("route_best_ratio", route_best_ratios, minimum=0.0)
    _validate_grid("route_best_loss_budget_m", route_best_loss_budgets_m, minimum=0.0)
    _validate_grid("candidate0_ratio", candidate0_ratios, minimum=0.0)
    _validate_grid("candidate0_loss_budget_m", candidate0_loss_budgets_m, minimum=0.0)

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
            row = _load_row(
                raw_record,
                log_path=log_path,
                record_index=record_index,
                min_progress_ratio=min_progress_ratio,
                red_threshold=red_threshold,
                missing=missing,
            )
            if row is not None:
                rows.append(row)

    if not rows:
        raise ValueError("No records with DP reward candidates were found.")

    guard_specs = _guard_specs(
        route_best_ratios=route_best_ratios,
        route_best_loss_budgets_m=route_best_loss_budgets_m,
        candidate0_ratios=candidate0_ratios,
        candidate0_loss_budgets_m=candidate0_loss_budgets_m,
    )
    guard_reports = [
        _guard_report(rows, spec, max_examples=max_examples) for spec in guard_specs
    ]
    return {
        "analysis": {
            "name": "dp_camp_progress_mapping_guard_audit_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "dp_modification": False,
            "closed_loop_outcome_labels_used": False,
            "min_progress_ratio": float(min_progress_ratio),
            "red_threshold": float(red_threshold),
            "route_best_ratios": list(route_best_ratios),
            "route_best_loss_budgets_m": list(route_best_loss_budgets_m),
            "candidate0_ratios": list(candidate0_ratios),
            "candidate0_loss_budgets_m": list(candidate0_loss_budgets_m),
            "math_boundary": (
                "This audit compares fixed current-tick finite-candidate "
                "quantities: DP reward progress, DP hard-gate fields, and "
                "candidate_route_progress. It uses no closed-loop outcome "
                "labels and changes no replay or selector behavior. A route "
                "guard with false-feasible candidates relative to the DP reward "
                "baseline is not an admissible replacement. A conservative "
                "zero-false-feasible guard is still only a finite-candidate "
                "diagnostic unless later atomized with fixed nonnegative "
                "scaling so CAMP scores remain affine in w."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(rows),
            "candidate_total": int(sum(row["candidate_count"] for row in rows)),
            "records_with_route_progress": int(
                sum(row["route_progress"] is not None for row in rows)
            ),
            "fallback_records_by_dp_reward": int(
                sum(int(not row["baseline_mask"].any()) for row in rows)
            ),
            "nonfallback_records_by_dp_reward": int(
                sum(int(row["baseline_mask"].any()) for row in rows)
            ),
        },
        "missing": dict(sorted(missing.items())),
        "baseline_dp_reward": _baseline_report(rows),
        "progress_alignment": _progress_alignment(rows),
        "guard_plans": guard_reports,
        "decision_hint": _decision_hint(guard_reports),
    }


def _validate_grid(name: str, values: tuple[float, ...], *, minimum: float) -> None:
    if not values:
        raise ValueError(f"{name} must contain at least one value.")
    for value in values:
        if not np.isfinite(float(value)) or float(value) < minimum:
            raise ValueError(f"{name} values must be finite and >= {minimum}.")


def _load_row(
    record: dict[str, Any],
    *,
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
    if dp_progress.shape != (candidate_count,) or not np.all(np.isfinite(dp_progress)):
        missing["dp_reward_progress"] += 1
        return None
    near_red = _near_red_cost(rewards)
    hard_mask, hard_reasons = _hard_mask(
        rewards,
        red_cost=near_red,
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
        "log_path": str(log_path),
        "record_index": int(record_index),
        "selection_step": int(record.get("selection_step", record_index)),
        "candidate_count": int(candidate_count),
        "selected_index": _optional_int(record.get("selected_index")),
        "min_progress_ratio": float(min_progress_ratio),
        "rewards": rewards,
        "dp_progress": dp_progress,
        "route_progress": _optional_vector(
            record.get("candidate_route_progress"),
            candidate_count,
            "candidate_route_progress",
            missing,
        ),
        "near_red": near_red,
        "hard_mask": hard_mask,
        "hard_reasons": hard_reasons,
        "baseline_mask": baseline_mask,
        "baseline_reasons": baseline_reasons,
    }


def _guard_specs(
    *,
    route_best_ratios: tuple[float, ...],
    route_best_loss_budgets_m: tuple[float, ...],
    candidate0_ratios: tuple[float, ...],
    candidate0_loss_budgets_m: tuple[float, ...],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for ratio in route_best_ratios:
        specs.append(
            {
                "name": f"route_best_ratio_{_tag(ratio)}",
                "family": "route_best_ratio",
                "parameter": float(ratio),
                "description": (
                    "Keep DP hard gates, then require route progress to be at "
                    "least ratio * best hard-feasible route progress."
                ),
            }
        )
    for budget in route_best_loss_budgets_m:
        specs.append(
            {
                "name": f"route_best_loss_m_{_tag(budget)}",
                "family": "route_best_loss_m",
                "parameter": float(budget),
                "description": (
                    "Keep DP hard gates, then require route progress to be "
                    "within an absolute loss budget of the best hard-feasible "
                    "route progress."
                ),
            }
        )
    for ratio in candidate0_ratios:
        specs.append(
            {
                "name": f"candidate0_route_ratio_{_tag(ratio)}",
                "family": "candidate0_route_ratio",
                "parameter": float(ratio),
                "description": (
                    "Keep DP hard gates, then require route progress to be at "
                    "least ratio * candidate0 route progress."
                ),
            }
        )
    for budget in candidate0_loss_budgets_m:
        specs.append(
            {
                "name": f"candidate0_route_loss_m_{_tag(budget)}",
                "family": "candidate0_route_loss_m",
                "parameter": float(budget),
                "description": (
                    "Keep DP hard gates, then require route progress to be "
                    "within an absolute loss budget of candidate0 route "
                    "progress."
                ),
            }
        )
    return specs


def _guard_report(
    rows: list[dict[str, Any]],
    spec: dict[str, Any],
    *,
    max_examples: int,
) -> dict[str, Any]:
    record_mismatches = 0
    candidate_mismatches = 0
    false_feasible = 0
    false_infeasible = 0
    selected_mask_changes = 0
    missing_records = 0
    pass_candidates = 0
    examples: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()

    for row in rows:
        route = row["route_progress"]
        if route is None:
            missing_records += 1
            continue
        guard_mask, guard_reasons, threshold = _apply_route_guard(row, spec, route)
        pass_candidates += int(guard_mask.sum())
        baseline = row["baseline_mask"]
        mismatch = guard_mask != baseline
        if mismatch.any():
            record_mismatches += 1
            candidate_mismatches += int(mismatch.sum())
            false_feasible += int(np.logical_and(guard_mask, ~baseline).sum())
            false_infeasible += int(np.logical_and(~guard_mask, baseline).sum())
            for idx in np.flatnonzero(mismatch):
                direction = (
                    "false_feasible_vs_dp_reward"
                    if bool(guard_mask[idx])
                    else "false_infeasible_vs_dp_reward"
                )
                reason_counts[direction] += 1
                if len(examples) < max_examples:
                    examples.append(
                        _example(row, idx, direction, guard_reasons[idx], threshold)
                    )
        selected = row["selected_index"]
        if selected is not None and 0 <= selected < row["candidate_count"]:
            selected_mask_changes += int(
                bool(guard_mask[selected]) != bool(baseline[selected])
            )

    compared_records = len(rows) - missing_records
    compared_candidates = int(
        sum(
            row["candidate_count"]
            for row in rows
            if row["route_progress"] is not None
        )
    )
    return {
        "name": spec["name"],
        "family": spec["family"],
        "parameter": float(spec["parameter"]),
        "description": spec["description"],
        "records": len(rows),
        "compared_records": int(compared_records),
        "missing_records": int(missing_records),
        "compared_candidates": int(compared_candidates),
        "passing_candidates": int(pass_candidates),
        "passing_candidate_rate": (
            pass_candidates / compared_candidates if compared_candidates else None
        ),
        "record_mismatches": int(record_mismatches),
        "candidate_mismatches": int(candidate_mismatches),
        "candidate_mismatch_rate": (
            candidate_mismatches / compared_candidates if compared_candidates else None
        ),
        "false_feasible_vs_dp_reward": int(false_feasible),
        "false_infeasible_vs_dp_reward": int(false_infeasible),
        "selected_candidate_mask_changes": int(selected_mask_changes),
        "reason_counts": dict(sorted(reason_counts.items())),
        "examples": examples,
        "acceptability_hint": _acceptability_hint(
            missing_records=missing_records,
            false_feasible=false_feasible,
            false_infeasible=false_infeasible,
        ),
    }


def _apply_route_guard(
    row: dict[str, Any],
    spec: dict[str, Any],
    route: np.ndarray,
) -> tuple[np.ndarray, tuple[tuple[str, ...], ...], float | None]:
    feasible = row["hard_mask"].copy()
    reasons = [list(reason_row) for reason_row in row["hard_reasons"]]
    threshold = _route_threshold(row, spec, route)
    if threshold is None:
        return feasible, tuple(tuple(reason_row) for reason_row in reasons), None
    for idx in np.flatnonzero(feasible):
        if float(route[idx]) + TOL < threshold:
            feasible[idx] = False
            reasons[idx].append(f"{spec['family']}_underprogress")
    return feasible, tuple(tuple(reason_row) for reason_row in reasons), threshold


def _route_threshold(
    row: dict[str, Any],
    spec: dict[str, Any],
    route: np.ndarray,
) -> float | None:
    hard_indices = np.flatnonzero(row["hard_mask"])
    family = str(spec["family"])
    parameter = float(spec["parameter"])
    if family == "route_best_ratio":
        if hard_indices.size == 0:
            return None
        best = float(np.max(route[hard_indices]))
        if best <= 0.0:
            return None
        return best * parameter
    if family == "route_best_loss_m":
        if hard_indices.size == 0:
            return None
        return float(np.max(route[hard_indices])) - parameter
    if family == "candidate0_route_ratio":
        candidate0 = float(route[0])
        if candidate0 <= 0.0:
            return None
        return candidate0 * parameter
    if family == "candidate0_route_loss_m":
        return float(route[0]) - parameter
    raise ValueError(f"Unsupported guard family: {family}")


def _example(
    row: dict[str, Any],
    idx: int,
    direction: str,
    guard_reasons: tuple[str, ...],
    threshold: float | None,
) -> dict[str, Any]:
    hard_indices = np.flatnonzero(row["hard_mask"])
    dp_best = float(np.max(row["dp_progress"][hard_indices])) if hard_indices.size else None
    dp_threshold = (
        None
        if dp_best is None or dp_best <= 0.0
        else dp_best * float(row["min_progress_ratio"])
    )
    route = row["route_progress"]
    return {
        "log_path": row["log_path"],
        "record_index": row["record_index"],
        "selection_step": row["selection_step"],
        "candidate_index": int(idx),
        "direction": direction,
        "baseline_reasons": list(row["baseline_reasons"][idx]),
        "guard_reasons": list(guard_reasons),
        "dp_progress": float(row["dp_progress"][idx]),
        "route_progress": None if route is None else float(route[idx]),
        "near_red": float(row["near_red"][idx]),
        "dp_best_progress": dp_best,
        "dp_threshold_progress": dp_threshold,
        "route_threshold": threshold,
        "selected_index": row["selected_index"],
    }


def _hard_mask(
    rewards: list[dict[str, Any]],
    *,
    red_cost: np.ndarray,
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
            ("dp_red_light", bool(red_cost[idx] > red_threshold)),
        )
        for reason, failed in checks:
            if failed:
                reasons[idx].append(reason)
        feasible[idx] = not reasons[idx]
    return feasible, tuple(tuple(reason_row) for reason_row in reasons)


def _apply_underprogress(
    hard_mask: np.ndarray,
    hard_reasons: tuple[tuple[str, ...], ...],
    progress: np.ndarray,
    *,
    min_progress_ratio: float,
    reason: str,
) -> tuple[np.ndarray, tuple[tuple[str, ...], ...]]:
    feasible = np.asarray(hard_mask, dtype=bool).copy()
    reasons = [list(reason_row) for reason_row in hard_reasons]
    safe_indices = np.flatnonzero(feasible)
    if safe_indices.size:
        best_progress = float(np.max(progress[safe_indices]))
        if best_progress > 0.0:
            minimum_progress = best_progress * float(min_progress_ratio)
            for idx in safe_indices:
                if float(progress[idx]) < minimum_progress:
                    feasible[idx] = False
                    reasons[idx].append(reason)
    return feasible, tuple(tuple(reason_row) for reason_row in reasons)


def _baseline_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hard_reason_counts: Counter[str] = Counter()
    baseline_reason_counts: Counter[str] = Counter()
    hard_feasible = 0
    baseline_feasible = 0
    selected_baseline_infeasible = 0
    for row in rows:
        hard_feasible += int(row["hard_mask"].sum())
        baseline_feasible += int(row["baseline_mask"].sum())
        selected = row["selected_index"]
        if selected is not None and 0 <= selected < row["candidate_count"]:
            selected_baseline_infeasible += int(not bool(row["baseline_mask"][selected]))
        for reasons in row["hard_reasons"]:
            hard_reason_counts.update(reasons)
        for reasons in row["baseline_reasons"]:
            baseline_reason_counts.update(reasons)
    return {
        "hard_feasible_candidates": int(hard_feasible),
        "dp_reward_feasible_candidates": int(baseline_feasible),
        "selected_dp_reward_infeasible_records": int(selected_baseline_infeasible),
        "hard_reason_counts": dict(sorted(hard_reason_counts.items())),
        "final_reason_counts": dict(sorted(baseline_reason_counts.items())),
    }


def _progress_alignment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    route_minus_dp: list[float] = []
    route_delta_minus_dp_delta: list[float] = []
    best_matches = 0
    best_comparable = 0
    pair_counts = Counter()
    missing = 0
    for row in rows:
        route = row["route_progress"]
        if route is None:
            missing += 1
            continue
        dp = row["dp_progress"]
        route_minus_dp.extend(float(value) for value in route - dp)
        route_delta = route - float(route[0])
        dp_delta = dp - float(dp[0])
        route_delta_minus_dp_delta.extend(
            float(value) for value in route_delta - dp_delta
        )
        hard_indices = np.flatnonzero(row["hard_mask"])
        if hard_indices.size:
            best_dp = set(hard_indices[dp[hard_indices] == np.max(dp[hard_indices])])
            best_route = set(
                hard_indices[route[hard_indices] == np.max(route[hard_indices])]
            )
            best_comparable += 1
            best_matches += int(bool(best_dp & best_route))
        pair_counts.update(_pairwise_order_counts(dp, route))
    total_pairs = pair_counts["concordant"] + pair_counts["discordant"]
    return {
        "records_with_missing_route_progress": int(missing),
        "route_minus_dp_progress_m": _summary(route_minus_dp),
        "candidate0_delta_route_minus_dp_m": _summary(route_delta_minus_dp_delta),
        "best_hard_feasible_index_overlap_rate": (
            best_matches / best_comparable if best_comparable else None
        ),
        "pairwise_order": {
            **dict(sorted(pair_counts.items())),
            "strict_pair_concordance_rate": (
                pair_counts["concordant"] / total_pairs if total_pairs else None
            ),
            "strict_pair_discordance_rate": (
                pair_counts["discordant"] / total_pairs if total_pairs else None
            ),
        },
    }


def _pairwise_order_counts(dp: np.ndarray, route: np.ndarray) -> Counter[str]:
    counts: Counter[str] = Counter()
    for i in range(dp.size):
        for j in range(i + 1, dp.size):
            dp_delta = float(dp[i] - dp[j])
            route_delta = float(route[i] - route[j])
            dp_sign = _sign(dp_delta)
            route_sign = _sign(route_delta)
            if dp_sign == 0:
                counts["dp_tied_pairs"] += 1
                continue
            if route_sign == 0:
                counts["route_tied_pairs"] += 1
                continue
            if dp_sign == route_sign:
                counts["concordant"] += 1
            else:
                counts["discordant"] += 1
    return counts


def _decision_hint(guard_reports: list[dict[str, Any]]) -> str:
    zero_false_feasible = [
        report["name"]
        for report in guard_reports
        if report["missing_records"] == 0
        and report["false_feasible_vs_dp_reward"] == 0
    ]
    equivalent = [
        report["name"]
        for report in guard_reports
        if report["missing_records"] == 0
        and report["candidate_mismatches"] == 0
    ]
    if equivalent:
        return (
            "route_guard_mask_equivalent_on_this_artifact_but_requires_broader_"
            f"grid: {', '.join(equivalent)}"
        )
    if zero_false_feasible:
        return (
            "only_conservative_zero_false_feasible_route_guards_found; inspect "
            f"false_infeasible availability before any online use: {', '.join(zero_false_feasible)}"
        )
    return (
        "reject_route_progress_guard_replacement_until_a_zero_false_feasible_"
        "guard_or_separate_progress_certificate_is_found"
    )


def _acceptability_hint(
    *,
    missing_records: int,
    false_feasible: int,
    false_infeasible: int,
) -> str:
    if missing_records:
        return "missing_route_progress_records"
    if false_feasible:
        return "reject_false_feasible_vs_dp_reward"
    if false_infeasible:
        return "conservative_zero_false_feasible_not_equivalent"
    return "mask_equivalent_on_this_artifact"


def _near_red_cost(rewards: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray(
        [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in rewards],
        dtype=np.float64,
    )


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
    if result.shape != (expected,) or not np.all(np.isfinite(result)):
        missing[field] += 1
        return None
    return result


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


def _sign(value: float) -> int:
    if abs(value) <= TOL:
        return 0
    return 1 if value > 0.0 else -1


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


def _tag(value: float) -> str:
    return f"{float(value):.6g}".replace("-", "neg").replace(".", "p")


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    lines = [
        "# DP-CAMP Progress Mapping Guard Audit",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Records",
        "",
        "| Logs | Records | Candidates | Route Available | DP-Reward Nonfallback | DP-Reward Fallback |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| {records['logs']} | {records['total']} | "
            f"{records['candidate_total']} | "
            f"{records['records_with_route_progress']} | "
            f"{records['nonfallback_records_by_dp_reward']} | "
            f"{records['fallback_records_by_dp_reward']} |"
        ),
        "",
        "## Guard Plans",
        "",
        "| Guard | False Feasible | False Infeasible | Mismatches | Selected Changes | Passing Rate | Hint |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for plan in report["guard_plans"]:
        lines.append(
            "| "
            f"`{plan['name']}` | "
            f"{plan['false_feasible_vs_dp_reward']} | "
            f"{plan['false_infeasible_vs_dp_reward']} | "
            f"{plan['candidate_mismatches']} | "
            f"{plan['selected_candidate_mask_changes']} | "
            f"{_fmt(plan['passing_candidate_rate'])} | "
            f"`{plan['acceptability_hint']}` |"
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
        ]
    )
    return "\n".join(lines) + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return "`null`"
    return f"`{float(value):.6f}`"


if __name__ == "__main__":
    main()
