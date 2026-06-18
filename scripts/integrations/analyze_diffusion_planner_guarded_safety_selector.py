#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    CAMPSelector,
    atom_schema_for_dimension,
)
from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    DEFAULT_REQUIRED_BUCKETS,
    EPS,
    FORMAL_SEEDS,
    _aggregate,
    _coverage_gaps,
    _fmt,
    _log_context,
    _opportunity_gate,
    _record_row,
    _record_summary,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
)
from scripts.integrations.evaluate_diffusion_planner_camp_safety_cost import (  # noqa: E402
    _bucket_aggregates,
    _select_record_index,
    _selection_pair,
    _selector_comparison,
)


TOL = 1e-12


@dataclass(frozen=True)
class GuardConfig:
    progress_shortfall_loss_max: float = 0.05
    target_speed_loss_max_mps: float = 0.10
    h10_distance_loss_max_m: float = 0.10
    absolute_lateral_guard_mps2: float = 2.0
    require_proxy_jerk_nonworse: bool = True
    require_clearance_nonworse: bool = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline guarded selector audit for fixed DP candidate pools. The "
            "guard uses current-tick diagnostics only and posterior outcomes "
            "only for SafetyCost evaluation."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--atom_scales", type=Path, required=True)
    parser.add_argument("--static_weights", type=Path, required=True)
    parser.add_argument("--selector_name", default="evaluated_camp")
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--progress_shortfall_loss_max", type=float, default=0.05)
    parser.add_argument("--target_speed_loss_max_mps", type=float, default=0.10)
    parser.add_argument("--h10_distance_loss_max_m", type=float, default=0.10)
    parser.add_argument("--absolute_lateral_guard_mps2", type=float, default=2.0)
    parser.add_argument(
        "--allow_proxy_jerk_regression",
        action="store_true",
        help="Do not require candidate_dp_prior_jerk_excess_cost nonworse.",
    )
    parser.add_argument(
        "--allow_clearance_regression",
        action="store_true",
        help="Do not require current-tick obstacle-clearance costs nonworse.",
    )
    parser.add_argument(
        "--fail_on_formal_seeds",
        action="store_true",
        help="Exit nonzero if any selection log belongs to seeds 11, 12, or 13.",
    )
    parser.add_argument(
        "--required_bucket",
        action="append",
        choices=sorted(SUPPORTED_SCENARIO_BUCKETS - {"overall"}),
        default=None,
    )
    parser.add_argument("--fail_on_missing_required", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    required_buckets = (
        tuple(args.required_bucket)
        if args.required_bucket is not None
        else DEFAULT_REQUIRED_BUCKETS
    )
    report = analyze(
        [*args.root, *args.selection_log],
        atom_scales=args.atom_scales,
        static_weights=args.static_weights,
        selector_name=args.selector_name,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        guard=GuardConfig(
            progress_shortfall_loss_max=args.progress_shortfall_loss_max,
            target_speed_loss_max_mps=args.target_speed_loss_max_mps,
            h10_distance_loss_max_m=args.h10_distance_loss_max_m,
            absolute_lateral_guard_mps2=args.absolute_lateral_guard_mps2,
            require_proxy_jerk_nonworse=not args.allow_proxy_jerk_regression,
            require_clearance_nonworse=not args.allow_clearance_regression,
        ),
        fail_on_formal_seeds=args.fail_on_formal_seeds,
        required_buckets=required_buckets,
    )
    if args.fail_on_missing_required and report["coverage_gaps"][
        "missing_required_buckets"
    ]:
        missing = ", ".join(report["coverage_gaps"]["missing_required_buckets"])
        raise SystemExit(
            f"Missing required scenario bucket coverage: {missing}"
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
    atom_scales: Path,
    static_weights: Path,
    selector_name: str = "evaluated_camp",
    scenario_bucket_manifest: Path | None = None,
    guard: GuardConfig = GuardConfig(),
    fail_on_formal_seeds: bool = False,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
) -> dict[str, Any]:
    _validate_guard(guard)
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    selector = CAMPSelector.from_files(
        atom_scales_path=atom_scales,
        static_weights_path=static_weights,
        mode="static",
    )
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)

    logs: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    guarded_rows: list[dict[str, Any]] = []
    logged_rows: list[dict[str, Any]] = []
    raw_pairs: list[dict[str, Any]] = []
    guarded_pairs: list[dict[str, Any]] = []
    guard_events: list[dict[str, Any]] = []

    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        formal_seed = context["seed"] in FORMAL_SEEDS
        if formal_seed and fail_on_formal_seeds:
            raise ValueError(f"Formal seed log is forbidden: {log_path}")
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        logs.append(
            {
                "path": str(log_path),
                "run_key": context["run_key"],
                "seed": context["seed"],
                "formal_seed": formal_seed,
                "scenario_buckets": context["scenario_buckets"],
                "records": len(payload),
            }
        )
        for record_index, record in enumerate(payload):
            label = f"{log_path} record {record_index}"
            raw_index, scores, used_fallback = _select_record_index(
                record,
                selector,
                label=label,
            )
            logged_index = int(record.get("selected_index"))
            decision = _guard_decision(
                record,
                raw_index=raw_index,
                logged_index=logged_index,
                guard=guard,
                label=label,
            )
            guarded_index = (
                raw_index if decision["accepted"] else logged_index
            )
            raw_record = {**record, "selected_index": int(raw_index)}
            guarded_record = {**record, "selected_index": int(guarded_index)}

            raw_row = _record_row(
                raw_record,
                label=label,
                log_path=log_path,
                record_index=record_index,
                context=context,
                formal_seed=formal_seed,
            )
            guarded_row = _record_row(
                guarded_record,
                label=label,
                log_path=log_path,
                record_index=record_index,
                context=context,
                formal_seed=formal_seed,
            )
            logged_row = _record_row(
                record,
                label=label,
                log_path=log_path,
                record_index=record_index,
                context=context,
                formal_seed=formal_seed,
            )
            raw_row["evaluated_selector_scores"] = scores.tolist()
            raw_row["evaluated_selector_used_fallback"] = bool(used_fallback)
            guarded_row["guard_decision"] = decision
            raw_rows.append(raw_row)
            guarded_rows.append(guarded_row)
            logged_rows.append(logged_row)
            raw_pairs.append(
                _selection_pair(
                    record,
                    evaluated_row=raw_row,
                    logged_row=logged_row,
                    log_path=log_path,
                    record_index=record_index,
                    context=context,
                )
            )
            guarded_pairs.append(
                _selection_pair(
                    record,
                    evaluated_row=guarded_row,
                    logged_row=logged_row,
                    log_path=log_path,
                    record_index=record_index,
                    context=context,
                )
            )
            guard_events.append(
                _guard_event(
                    decision,
                    raw_row=raw_row,
                    guarded_row=guarded_row,
                    logged_row=logged_row,
                    log_path=log_path,
                    record_index=record_index,
                    context=context,
                )
            )

    formal_seed_logs = [log["path"] for log in logs if log["formal_seed"]]
    coverage_gaps = _coverage_gaps(guarded_rows, required_buckets)
    guarded_overall = _aggregate(guarded_rows, seed_key=f"{selector_name}:guarded")
    return {
        "analysis": {
            "name": "dp_camp_guarded_candidate_branch_safety_selector_v1",
            "role": (
                "offline fail-closed audit for a saved CAMP selector guarded "
                "against the logged baseline selector"
            ),
            "training": False,
            "online_selector_change": False,
            "selector_name": selector_name,
            "selector_artifacts": {
                "atom_scales": str(atom_scales),
                "static_weights": str(static_weights),
            },
            "baseline": "logged_selected_index",
            "guard": guard.__dict__,
            "future_outcome_leakage": (
                "guard predicates use only current-tick finite-candidate "
                "diagnostics; candidate_closed_loop_outcomes are used only for "
                "posterior SafetyCost evaluation"
            ),
            "math_boundary": (
                "The guard is a finite-candidate deterministic filter over "
                "fixed current-tick constants. It does not alter DP, candidate "
                "generation, atoms, affine score semantics, or the "
                "simplex/CVaR/L2 master. If guard diagnostics are atomized "
                "later, they must remain fixed nonnegative candidate costs. "
                "This audit is not a classical Benders subproblem."
            ),
            "formal_seed_policy": (
                "forbidden" if fail_on_formal_seeds else "reported_only"
            ),
            "formal_seed_logs": formal_seed_logs,
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "required_buckets": list(required_buckets),
        },
        "logs": {
            "total": len(logs),
            "formal_seed_logs": len(formal_seed_logs),
            "items": logs,
        },
        "records": _record_summary(guarded_rows),
        "raw_selector": {
            "overall": _aggregate(raw_rows, seed_key=f"{selector_name}:raw"),
            "by_bucket": _bucket_aggregates(raw_rows),
        },
        "guarded_selector": {
            "overall": guarded_overall,
            "by_bucket": _bucket_aggregates(guarded_rows),
        },
        "logged_selector": {
            "overall": _aggregate(logged_rows, seed_key="logged:overall"),
            "by_bucket": _bucket_aggregates(logged_rows),
        },
        "raw_vs_logged": _selector_comparison(raw_pairs),
        "guarded_vs_logged": _selector_comparison(guarded_pairs),
        "guard_summary": _guard_summary(guard_events),
        "coverage_gaps": coverage_gaps,
        "opportunity_gate": _opportunity_gate(
            guarded_overall,
            _bucket_aggregates(guarded_rows),
            coverage_gaps,
            formal_seed_logs=formal_seed_logs,
            required_buckets=required_buckets,
        ),
    }


def _validate_guard(guard: GuardConfig) -> None:
    for name, value in guard.__dict__.items():
        if isinstance(value, bool):
            continue
        numeric = float(value)
        if not np.isfinite(numeric) or numeric < 0.0:
            raise ValueError(f"{name} must be finite and nonnegative.")


def _guard_decision(
    record: dict[str, Any],
    *,
    raw_index: int,
    logged_index: int,
    guard: GuardConfig,
    label: str,
) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if not 0 <= raw_index < candidate_count or not 0 <= logged_index < candidate_count:
        raise ValueError(f"{label} selector indices are out of range.")
    if raw_index == logged_index:
        return {
            "attempted_override": False,
            "accepted": True,
            "stage": "same_as_logged",
            "fail_reasons": [],
            "diagnostics": {},
        }

    fail_reasons: list[str] = []
    diagnostics: dict[str, float | bool | None] = {}
    feasible = _bool_vector(
        record.get("feasible_mask"),
        candidate_count,
        f"{label} feasible_mask",
    )
    if not feasible[raw_index]:
        fail_reasons.append("raw_candidate_infeasible")
    if not feasible[logged_index]:
        fail_reasons.append("logged_candidate_infeasible")

    atom_names = _atom_names(record, candidate_count)
    atoms = _matrix(
        record.get("atoms"),
        candidate_count,
        len(atom_names),
        f"{label} atoms",
    )
    progress_shortfall = atoms[:, atom_names.index("progress_shortfall")]
    diagnostics["progress_shortfall_loss"] = _loss(
        progress_shortfall,
        raw_index,
        logged_index,
    )
    if diagnostics["progress_shortfall_loss"] > guard.progress_shortfall_loss_max + TOL:
        fail_reasons.append("progress_shortfall_loss")

    vector_checks = (
        (
            "union_red",
            "candidate_horizon_union_planned_red_light_cost",
            0.0,
            "nonworse",
        ),
        (
            "red_stopping",
            "candidate_red_stopping_margin_cost",
            0.0,
            "nonworse",
        ),
        (
            "proxy_lateral",
            "candidate_horizon_lateral_acceleration_cost",
            0.0,
            "nonworse",
        ),
        (
            "target_speed_loss",
            "candidate_perfect_tracker_target_speed_mps",
            guard.target_speed_loss_max_mps,
            "loss",
        ),
    )
    for key, field, budget, mode in vector_checks:
        values = _vector(record.get(field), candidate_count, f"{label} {field}")
        if mode == "loss":
            value = _loss(values, raw_index, logged_index, higher_is_better=True)
        else:
            value = _loss(values, raw_index, logged_index)
        diagnostics[key] = value
        if value > budget + TOL:
            fail_reasons.append(key)

    lateral = _vector(
        record.get("candidate_horizon_lateral_acceleration_cost"),
        candidate_count,
        f"{label} candidate_horizon_lateral_acceleration_cost",
    )
    diagnostics["absolute_lateral"] = float(lateral[raw_index])
    if lateral[raw_index] > guard.absolute_lateral_guard_mps2 + TOL:
        fail_reasons.append("absolute_lateral")

    if guard.require_proxy_jerk_nonworse:
        jerk = _vector(
            record.get("candidate_dp_prior_jerk_excess_cost"),
            candidate_count,
            f"{label} candidate_dp_prior_jerk_excess_cost",
        )
        diagnostics["proxy_jerk"] = _loss(jerk, raw_index, logged_index)
        if diagnostics["proxy_jerk"] > TOL:
            fail_reasons.append("proxy_jerk")

    h10_distance = _h10_distance(record, candidate_count, label)
    diagnostics["h10_distance_loss"] = _loss(
        h10_distance,
        raw_index,
        logged_index,
        higher_is_better=True,
    )
    if diagnostics["h10_distance_loss"] > guard.h10_distance_loss_max_m + TOL:
        fail_reasons.append("h10_distance_loss")

    if guard.require_clearance_nonworse:
        clearance = _clearance(record, candidate_count, label)
        if clearance is None:
            fail_reasons.append("clearance_missing")
        else:
            for key, values in (
                ("soft_clearance", clearance["soft_cost"]),
                ("near_miss_clearance", clearance["near_cost"]),
            ):
                diagnostics[key] = _loss(values, raw_index, logged_index)
                if diagnostics[key] > TOL:
                    fail_reasons.append(key)
            min_bound = clearance["min_lower_bound"]
            if min_bound is not None:
                raw_value = min_bound[raw_index]
                logged_value = min_bound[logged_index]
                if raw_value is not None and logged_value is not None:
                    diagnostics["min_clearance_lower_bound_loss"] = (
                        float(logged_value) - float(raw_value)
                    )
                    if diagnostics["min_clearance_lower_bound_loss"] > TOL:
                        fail_reasons.append("min_clearance_lower_bound")

    return {
        "attempted_override": True,
        "accepted": not fail_reasons,
        "stage": "accepted" if not fail_reasons else "fail_closed_to_logged",
        "fail_reasons": fail_reasons,
        "diagnostics": diagnostics,
    }


def _guard_event(
    decision: dict[str, Any],
    *,
    raw_row: dict[str, Any],
    guarded_row: dict[str, Any],
    logged_row: dict[str, Any],
    log_path: Path,
    record_index: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    raw_cost_delta = raw_row["costs"]["camp"] - logged_row["costs"]["camp"]
    guarded_cost_delta = guarded_row["costs"]["camp"] - logged_row["costs"]["camp"]
    return {
        "log_path": str(log_path),
        "record_index": int(record_index),
        "run_key": context["run_key"],
        "scenario_buckets": context["scenario_buckets"],
        "raw_index": int(raw_row["camp_index"]),
        "logged_index": int(logged_row["camp_index"]),
        "guarded_index": int(guarded_row["camp_index"]),
        "attempted_override": bool(decision["attempted_override"]),
        "accepted": bool(decision["accepted"]),
        "stage": str(decision["stage"]),
        "fail_reasons": list(decision["fail_reasons"]),
        "raw_minus_logged_cost": float(raw_cost_delta),
        "guarded_minus_logged_cost": float(guarded_cost_delta),
        "raw_worse_than_logged": bool(raw_cost_delta > EPS),
        "guarded_worse_than_logged": bool(guarded_cost_delta > EPS),
    }


def _guard_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    attempted = [event for event in events if event["attempted_override"]]
    accepted = [event for event in attempted if event["accepted"]]
    rejected = [event for event in attempted if not event["accepted"]]
    raw_worse = [event for event in attempted if event["raw_worse_than_logged"]]
    blocked_worse = [
        event
        for event in raw_worse
        if not event["accepted"] and not event["guarded_worse_than_logged"]
    ]
    return {
        "records": len(events),
        "attempted_overrides": len(attempted),
        "accepted_overrides": len(accepted),
        "rejected_overrides": len(rejected),
        "attempt_rate": _rate(len(attempted), len(events)),
        "accept_rate_given_attempt": _rate(len(accepted), len(attempted)),
        "raw_worse_attempts": len(raw_worse),
        "raw_worse_blocked": len(blocked_worse),
        "raw_worse_block_rate": _rate(len(blocked_worse), len(raw_worse)),
        "accepted_worse_overrides": sum(
            int(event["guarded_worse_than_logged"]) for event in accepted
        ),
        "stage_counts": dict(Counter(event["stage"] for event in events)),
        "fail_reason_counts": dict(
            Counter(reason for event in rejected for reason in event["fail_reasons"])
        ),
    }


def _atom_names(record: dict[str, Any], candidate_count: int) -> tuple[str, ...]:
    names = record.get("atom_names")
    atoms = record.get("atoms")
    if isinstance(names, list) and names:
        return tuple(str(name) for name in names)
    arr = np.asarray(atoms, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != candidate_count:
        raise ValueError("atoms must be [K,R] when atom_names are missing.")
    return atom_schema_for_dimension(arr.shape[1])[1]


def _matrix(values: Any, rows: int, cols: int, label: str) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.shape != (rows, cols) or not np.all(np.isfinite(arr)):
        raise ValueError(f"{label} must have shape {(rows, cols)} and finite values.")
    return arr


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.shape != (size,) or not np.all(np.isfinite(arr)):
        raise ValueError(f"{label} must be a finite vector of length {size}.")
    return arr


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(values, dtype=bool)
    if arr.shape != (size,):
        raise ValueError(f"{label} must be a boolean vector of length {size}.")
    return arr


def _h10_distance(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> np.ndarray:
    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    if not isinstance(rollout, dict):
        raise ValueError(f"{label} missing candidate_perfect_tracker_open_loop_rollout.")
    h10 = rollout.get("10", rollout.get(10))
    if not isinstance(h10, dict):
        raise ValueError(f"{label} missing H10 rollout diagnostics.")
    return _vector(h10.get("distance_m"), candidate_count, f"{label} H10 distance_m")


def _clearance(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, Any] | None:
    payload = record.get("candidate_obstacle_clearance")
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != "candidate_current_tick_obstacle_clearance_v2":
        return None
    return {
        "soft_cost": _vector(
            payload.get("soft_clearance_violation_cost"),
            candidate_count,
            f"{label} soft_clearance_violation_cost",
        ),
        "near_cost": _vector(
            payload.get("near_miss_violation_cost"),
            candidate_count,
            f"{label} near_miss_violation_cost",
        ),
        "min_lower_bound": _nullable_vector(
            payload.get("min_obstacle_clearance_lower_bound_m"),
            candidate_count,
            f"{label} min_obstacle_clearance_lower_bound_m",
        ),
    }


def _nullable_vector(values: Any, size: int, label: str) -> list[float | None] | None:
    if values is None:
        return None
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must be a nullable vector of length {size}.")
    result: list[float | None] = []
    for value in values:
        if value is None:
            result.append(None)
        else:
            numeric = float(value)
            if not np.isfinite(numeric):
                raise ValueError(f"{label} values must be finite or null.")
            result.append(numeric)
    return result


def _loss(
    values: np.ndarray,
    raw_index: int,
    logged_index: int,
    *,
    higher_is_better: bool = False,
) -> float:
    if higher_is_better:
        return float(values[logged_index] - values[raw_index])
    return float(values[raw_index] - values[logged_index])


def _rate(count: int, total: int) -> float | None:
    if total <= 0:
        return None
    return float(count) / float(total)


def render_markdown(report: dict[str, Any]) -> str:
    raw = report["raw_selector"]["overall"]
    guarded = report["guarded_selector"]["overall"]
    logged = report["logged_selector"]["overall"]
    raw_cmp = report["raw_vs_logged"]
    guarded_cmp = report["guarded_vs_logged"]
    guard = report["guard_summary"]
    lines = [
        "# DP-CAMP Guarded Safety Selector Audit",
        "",
        "This is an offline finite-candidate audit. The raw selector scores "
        "current-tick atoms with saved CAMP weights; the guard may fail closed "
        "to the logged baseline using current-tick diagnostics only. Candidate "
        "outcomes are posterior SafetyCost labels.",
        "",
        f"- Selector: `{report['analysis']['selector_name']}`",
        f"- Logs: `{report['logs']['total']}`",
        f"- Records: `{report['records']['total']}`",
        f"- Formal-seed records: `{report['records']['formal_seed_records']}`",
        "",
        "## Overall",
        "",
        "| Metric | Raw selector | Guarded selector | Logged selector |",
        "| --- | ---: | ---: | ---: |",
        f"| Mean branch cost | {_fmt(raw['cost_mean']['camp'])} | {_fmt(guarded['cost_mean']['camp'])} | {_fmt(logged['cost_mean']['camp'])} |",
        f"| Mean delta vs Top-1 | {_fmt(raw['record_delta_mean']['camp_minus_top1'])} | {_fmt(guarded['record_delta_mean']['camp_minus_top1'])} | {_fmt(logged['record_delta_mean']['camp_minus_top1'])} |",
        f"| Gap to hard-guarded oracle | {_fmt(raw['record_delta_mean']['camp_minus_hard_guarded_oracle'])} | {_fmt(guarded['record_delta_mean']['camp_minus_hard_guarded_oracle'])} | {_fmt(logged['record_delta_mean']['camp_minus_hard_guarded_oracle'])} |",
        "",
        "## Guard",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Attempted overrides | `{guard['attempted_overrides']}` |",
        f"| Accepted overrides | `{guard['accepted_overrides']}` |",
        f"| Rejected overrides | `{guard['rejected_overrides']}` |",
        f"| Raw worse attempts | `{guard['raw_worse_attempts']}` |",
        f"| Raw worse blocked | `{guard['raw_worse_blocked']}` |",
        f"| Accepted worse overrides | `{guard['accepted_worse_overrides']}` |",
        f"| Accept rate given attempt | {_fmt(guard['accept_rate_given_attempt'])} |",
        "",
        "## Selector-vs-Logged",
        "",
        "| Metric | Raw selector | Guarded selector |",
        "| --- | ---: | ---: |",
        f"| Changed record rate | {_fmt(raw_cmp['changed_record_rate'])} | {_fmt(guarded_cmp['changed_record_rate'])} |",
        f"| Mean minus logged cost | {_fmt(raw_cmp['evaluated_minus_logged_cost_mean'])} | {_fmt(guarded_cmp['evaluated_minus_logged_cost_mean'])} |",
        f"| CI high minus logged | {_fmt(raw_cmp['run_level_evaluated_minus_logged_cost_ci']['ci95_high'])} | {_fmt(guarded_cmp['run_level_evaluated_minus_logged_cost_ci']['ci95_high'])} |",
        f"| Worse record rate | {_fmt(raw_cmp['cost_delta_record_rates']['evaluated_worse'])} | {_fmt(guarded_cmp['cost_delta_record_rates']['evaluated_worse'])} |",
        "",
        "Fail reason counts:",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ]
    for reason, count in sorted(guard["fail_reason_counts"].items()):
        lines.append(f"| `{reason}` | `{count}` |")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
