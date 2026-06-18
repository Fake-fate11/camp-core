#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from itertools import product
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
from scripts.integrations.analyze_diffusion_planner_dp_prior_atom_candidate import (  # noqa: E402
    EPS,
    _candidate_safety_cost,
    _conditional_rate,
    _hard_nonworse_rate,
    _nonnegative_float,
    _paired_summary,
    _planned_red_values,
    _robust_positive_scale,
    _summary,
    _vector,
)
from scripts.integrations.summarize_diffusion_planner_camp_safety_cost_proof import (  # noqa: E402
    DEFAULT_REQUIRED_BUCKETS,
)


ALPHAS = (0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4)
BETAS = (0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only joint audit for DP-prior-deviation and planned-progress "
            "preservation as finite current-tick CAMP atom candidates."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument("--alpha", type=float, action="append", default=[])
    parser.add_argument("--beta", type=float, action="append", default=[])
    parser.add_argument("--bootstrap_resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--min_progress_delta_ci_low", type=float, default=-0.05)
    parser.add_argument(
        "--required_bucket",
        action="append",
        default=None,
        help=(
            "Required bucket for the joint screen. Repeat to override the "
            "default comprehensive bucket list."
        ),
    )
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
        label=args.label,
        scale_percentile=args.scale_percentile,
        alphas=tuple(args.alpha) if args.alpha else ALPHAS,
        betas=tuple(args.beta) if args.beta else BETAS,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
        min_progress_delta_ci_low=args.min_progress_delta_ci_low,
        required_buckets=(
            tuple(args.required_bucket)
            if args.required_bucket is not None
            else DEFAULT_REQUIRED_BUCKETS
        ),
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
    scale_percentile: float = 95.0,
    alphas: tuple[float, ...] = ALPHAS,
    betas: tuple[float, ...] = BETAS,
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    min_progress_delta_ci_low: float = -0.05,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
) -> dict[str, Any]:
    if not 0.0 < scale_percentile < 100.0:
        raise ValueError("scale_percentile must be in (0, 100).")
    if not alphas or not betas:
        raise ValueError("At least one alpha and beta are required.")
    for value in (*alphas, *betas):
        if not 0.0 <= float(value) < 1.0:
            raise ValueError("Every alpha and beta must be in [0, 1).")
    pairs = [
        (float(alpha), float(beta))
        for alpha, beta in product(alphas, betas)
        if float(alpha) + float(beta) < 1.0
    ]
    if not pairs:
        raise ValueError("At least one alpha+beta pair must be < 1.")

    records = _load_records(paths)
    if not records:
        raise ValueError("No outcome-labeled records were found.")
    prior_scale = _robust_positive_scale(
        np.concatenate([record["dp_prior_deviation"] for record in records]),
        scale_percentile,
    )
    progress_scale = _robust_positive_scale(
        np.concatenate([record["planned_progress_shortfall"] for record in records]),
        scale_percentile,
    )
    grid_reports = [
        _grid_report(
            records,
            alpha,
            beta,
            prior_scale=prior_scale,
            progress_scale=progress_scale,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
            min_progress_delta_ci_low=min_progress_delta_ci_low,
            required_buckets=required_buckets,
        )
        for alpha, beta in pairs
    ]
    return {
        "analysis": {
            "name": "dp_prior_completion_joint_atom_audit_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "candidate outcomes are used only for posterior SafetyCost and "
                "progress evaluation; selection uses logged scores, "
                "candidate_dp_prior_deviation_cost, and candidate_route_progress"
            ),
            "candidate_atoms": {
                "dp_prior_deviation_cost": {
                    "definition": (
                        "mean_t ||xy_candidate(t) - xy_DPTop1(t)||_2^2 over "
                        "the logged DP candidate horizon"
                    ),
                    "nonnegative": True,
                    "candidate0_value": 0.0,
                    "scale": float(prior_scale),
                },
                "planned_progress_shortfall_cost": {
                    "definition": (
                        "max(0, max_feasible_candidate_route_progress - "
                        "candidate_route_progress) / max(max_feasible_progress, 1)"
                    ),
                    "nonnegative": True,
                    "scale": float(progress_scale),
                },
            },
            "virtual_score": (
                "score(k) = (1-alpha-beta) * logged_selection_score(k) + "
                "alpha * normalized_dp_prior_deviation(k) + beta * "
                "normalized_planned_progress_shortfall(k), with alpha+beta<1"
            ),
            "math_boundary": (
                "Both virtual atoms are fixed current-tick finite-candidate "
                "coefficients. If appended to CAMP, the score remains affine "
                "in weights a_k^T w and the simplex/CVaR/L2 robust master "
                "remains convex. This is not classical Benders decomposition "
                "because no DP-side subproblem, dual, or valid cuts are built."
            ),
            "alphas": [float(alpha) for alpha in alphas],
            "betas": [float(beta) for beta in betas],
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "min_progress_delta_ci_low": float(min_progress_delta_ci_low),
            "required_buckets": list(required_buckets),
        },
        "records": _record_summary(records),
        "opportunity_coverage": _opportunity_coverage_by_bucket(records),
        "grid": grid_reports,
        "ranked_candidates": _rank(grid_reports),
        "final_decision": _decision(grid_reports, records),
    }


def _load_records(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for log_path in iter_selection_log_paths(paths):
        metadata = parse_selection_log_metadata(log_path)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        context = {
            "log_path": str(log_path),
            "route": metadata.route,
            "seed": metadata.seed,
            "npc_count": metadata.npc_count,
            "traffic_light": metadata.traffic_light,
            "mode": metadata.mode,
        }
        buckets = _buckets_for_context(context)
        for record_index, raw in enumerate(payload):
            try:
                record = _load_record(raw, f"{log_path} record {record_index}")
            except ValueError as exc:
                if "candidate_closed_loop_outcomes" in str(exc):
                    continue
                raise
            record["context"] = {**context, "record_index": int(record_index)}
            record["buckets"] = buckets
            records.append(record)
    return records


def _load_record(raw: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    outcomes = raw.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        raise ValueError(f"{label} requires complete candidate_closed_loop_outcomes.")
    dp_prior = _vector(
        raw.get("candidate_dp_prior_deviation_cost"),
        candidate_count,
        f"{label} candidate_dp_prior_deviation_cost",
    )
    if abs(float(dp_prior[0])) > 1e-9:
        raise ValueError(f"{label} DP-prior deviation atom must be zero for candidate0.")
    planned_progress = _planned_progress(raw, candidate_count, label)
    planned_red = _planned_red_values(raw, candidate_count)
    scores = _vector(
        raw.get("selection_scores"),
        candidate_count,
        f"{label} selection_scores",
        allow_positive_infinity=True,
    )
    feasible = np.asarray(raw.get("feasible_mask"), dtype=bool).reshape(-1)
    if feasible.shape != (candidate_count,):
        raise ValueError(f"{label} feasible_mask must have shape [{candidate_count}].")
    costs = np.asarray(
        [_candidate_safety_cost(outcome, raw, idx) for idx, outcome in enumerate(outcomes)],
        dtype=np.float64,
    )
    outcome_progress = np.asarray(
        [_nonnegative_float(outcome, "progress_m") for outcome in outcomes],
        dtype=np.float64,
    )
    progress_shortfall = _planned_progress_shortfall(planned_progress, feasible)
    return {
        "selected": selected,
        "candidate_count": candidate_count,
        "feasible": feasible,
        "scores": scores,
        "dp_prior_deviation": dp_prior,
        "planned_progress": planned_progress,
        "planned_progress_shortfall": progress_shortfall,
        "planned_red": planned_red,
        "safety_cost": costs,
        "outcome_progress": outcome_progress,
        "outcomes": outcomes,
    }


def _planned_progress(raw: dict[str, Any], candidate_count: int, label: str) -> np.ndarray:
    for key in ("candidate_route_progress", "candidate_step_reach"):
        if raw.get(key) is None:
            continue
        values = _vector(raw.get(key), candidate_count, f"{label} {key}")
        if np.any(values < 0.0):
            raise ValueError(f"{label} {key} must be nonnegative.")
        return values
    raise ValueError(f"{label} requires candidate_route_progress or candidate_step_reach.")


def _planned_progress_shortfall(
    planned_progress: np.ndarray,
    feasible: np.ndarray,
) -> np.ndarray:
    branch = feasible if bool(feasible.any()) else np.ones_like(feasible, dtype=bool)
    reference = float(np.max(planned_progress[branch]))
    denom = max(reference, 1.0)
    return np.maximum(reference - planned_progress, 0.0) / denom


def _grid_report(
    records: list[dict[str, Any]],
    alpha: float,
    beta: float,
    *,
    prior_scale: float,
    progress_scale: float,
    bootstrap_resamples: int,
    seed: int,
    min_progress_delta_ci_low: float,
    required_buckets: tuple[str, ...],
) -> dict[str, Any]:
    selected = np.asarray([record["selected"] for record in records], dtype=np.int64)
    top1 = np.zeros(len(records), dtype=np.int64)
    chosen = np.asarray(
        [
            _select_with_joint_score(
                record,
                alpha,
                beta,
                prior_scale=prior_scale,
                progress_scale=progress_scale,
            )
            for record in records
        ],
        dtype=np.int64,
    )
    overall = _choice_metrics(
        records,
        chosen,
        selected,
        top1,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    by_bucket = {
        bucket: _choice_metrics(
            bucket_records,
            chosen[_record_indices(records, bucket)],
            selected[_record_indices(records, bucket)],
            top1[_record_indices(records, bucket)],
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
        for bucket, bucket_records in _records_by_bucket(records).items()
    }
    bucket_failures = _bucket_failures(
        by_bucket,
        min_progress_delta_ci_low=min_progress_delta_ci_low,
        required_buckets=required_buckets,
    )
    return {
        "alpha": float(alpha),
        "beta": float(beta),
        "overall": overall,
        "by_bucket": by_bucket,
        "passed_joint_screen": bool(
            _passes_metrics(overall, min_progress_delta_ci_low)
            and not bucket_failures
        ),
        "bucket_failures": bucket_failures,
    }


def _select_with_joint_score(
    record: dict[str, Any],
    alpha: float,
    beta: float,
    *,
    prior_scale: float,
    progress_scale: float,
) -> int:
    if float(alpha) == 0.0 and float(beta) == 0.0:
        return int(record["selected"])
    residual = 1.0 - float(alpha) - float(beta)
    if residual < 0.0:
        raise ValueError("alpha+beta must be <= 1.")
    scores = np.asarray(record["scores"], dtype=np.float64)
    prior = np.clip(record["dp_prior_deviation"] / float(prior_scale), 0.0, 10.0)
    progress = np.clip(
        record["planned_progress_shortfall"] / float(progress_scale),
        0.0,
        10.0,
    )
    mixed = residual * scores + float(alpha) * prior + float(beta) * progress
    return int(np.argmin(mixed))


def _choice_metrics(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
    top1: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    costs = np.asarray([record["safety_cost"] for record in records], dtype=np.float64)
    outcome_progress = np.asarray(
        [record["outcome_progress"] for record in records],
        dtype=np.float64,
    )
    planned_progress = np.asarray(
        [record["planned_progress"] for record in records],
        dtype=np.float64,
    )
    rows = np.arange(len(records))
    current_cost = costs[rows, selected]
    top1_cost = costs[:, 0]
    chosen_cost = costs[rows, chosen]
    current_progress = outcome_progress[rows, selected]
    chosen_progress = outcome_progress[rows, chosen]
    top1_progress = outcome_progress[:, 0]
    current_planned = planned_progress[rows, selected]
    chosen_planned = planned_progress[rows, chosen]
    harmful_current = (current_cost - top1_cost) > EPS
    beneficial_current = (top1_cost - current_cost) > EPS
    safety_delta_current = chosen_cost - current_cost
    safety_delta_top1 = chosen_cost - top1_cost
    return {
        "records": int(len(records)),
        "changed_from_current_rate": float(np.mean(chosen != selected)),
        "top1_selected_rate": float(np.mean(chosen == top1)),
        "harmful_current_records": int(np.sum(harmful_current)),
        "harmful_current_changed_rate": _conditional_rate(
            chosen != selected,
            harmful_current,
        ),
        "beneficial_current_records": int(np.sum(beneficial_current)),
        "beneficial_current_preserved_rate": _conditional_rate(
            chosen == selected,
            beneficial_current,
        ),
        "safety_cost_delta_vs_current": _summary_with_cvar(
            safety_delta_current,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "safety_cost_delta_vs_top1": _summary_with_cvar(
            safety_delta_top1,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_current": _paired_summary(
            chosen_progress - current_progress,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_top1": _paired_summary(
            chosen_progress - top1_progress,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "planned_progress_delta_vs_current": _paired_summary(
            chosen_planned - current_planned,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "hard_nonworse_vs_current": _hard_nonworse_rate(records, chosen, selected),
        "hard_nonworse_vs_top1": _hard_nonworse_rate(records, chosen, top1),
    }


def _summary_with_cvar(
    values: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    summary = _paired_summary(
        values,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return {**summary, "cvar90_worst_tail": None}
    threshold = float(np.percentile(arr, 90.0))
    tail = arr[arr >= threshold]
    return {**summary, "cvar90_worst_tail": float(np.mean(tail))}


def _opportunity_coverage_by_bucket(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        bucket: _opportunity_coverage(bucket_records)
        for bucket, bucket_records in _records_by_bucket(records).items()
    }


def _opportunity_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for record in records:
        selected = int(record["selected"])
        current_cost = float(record["safety_cost"][selected])
        current_progress = float(record["outcome_progress"][selected])
        current_planned = float(record["planned_progress"][selected])
        safer = record["safety_cost"] < current_cost - EPS
        hard_nonworse = np.asarray(
            [
                all(
                    float(bool(outcome[field]))
                    <= float(bool(record["outcomes"][selected][field]))
                    for field in (
                        "collision",
                        "near_miss",
                        "lane_violation",
                        "red_light_violation",
                    )
                )
                for outcome in record["outcomes"]
            ],
            dtype=bool,
        )
        progress_nonworse = record["outcome_progress"] >= current_progress - EPS
        planned_nonworse = record["planned_progress"] >= current_planned - EPS
        top1_delta = float(record["safety_cost"][selected] - record["safety_cost"][0])
        prior_delta = float(
            record["dp_prior_deviation"][selected]
            - record["dp_prior_deviation"][0]
        )
        rows.append(
            {
                "harmful_current": top1_delta > EPS,
                "beneficial_current": top1_delta < -EPS,
                "positive_prior_delta": prior_delta > EPS,
                "safer_candidate": bool(np.any(safer)),
                "safer_hard_nonworse": bool(np.any(safer & hard_nonworse)),
                "safer_progress_nonworse": bool(
                    np.any(safer & hard_nonworse & progress_nonworse)
                ),
                "safer_planned_progress_nonworse": bool(
                    np.any(safer & hard_nonworse & planned_nonworse)
                ),
            }
        )
    harmful = np.asarray([row["harmful_current"] for row in rows], dtype=bool)
    beneficial = np.asarray([row["beneficial_current"] for row in rows], dtype=bool)
    positive_prior = np.asarray([row["positive_prior_delta"] for row in rows], dtype=bool)
    return {
        "records": int(len(records)),
        "harmful_current_records": int(np.sum(harmful)),
        "beneficial_current_records": int(np.sum(beneficial)),
        "harmful_with_positive_prior_rate": _conditional_rate(
            positive_prior,
            harmful,
        ),
        "beneficial_with_positive_prior_rate": _conditional_rate(
            positive_prior,
            beneficial,
        ),
        "safer_candidate_rate": float(np.mean([row["safer_candidate"] for row in rows])),
        "safer_hard_nonworse_rate": float(
            np.mean([row["safer_hard_nonworse"] for row in rows])
        ),
        "safer_progress_nonworse_rate": float(
            np.mean([row["safer_progress_nonworse"] for row in rows])
        ),
        "safer_planned_progress_nonworse_rate": float(
            np.mean([row["safer_planned_progress_nonworse"] for row in rows])
        ),
    }


def _record_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    bucket_counts = {
        bucket: len(bucket_records)
        for bucket, bucket_records in _records_by_bucket(records).items()
    }
    return {
        "logs": len({record["context"]["log_path"] for record in records}),
        "total": len(records),
        "candidates": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
        "bucket_record_counts": bucket_counts,
        "selected_non_top1_rate": float(
            np.mean([record["selected"] != 0 for record in records])
        ),
    }


def _records_by_bucket(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        for bucket in record["buckets"]:
            buckets.setdefault(bucket, []).append(record)
    return {bucket: buckets[bucket] for bucket in sorted(buckets)}


def _record_indices(records: list[dict[str, Any]], bucket: str) -> np.ndarray:
    return np.asarray(
        [idx for idx, record in enumerate(records) if bucket in record["buckets"]],
        dtype=np.int64,
    )


def _buckets_for_context(context: dict[str, Any]) -> list[str]:
    route = str(context.get("route") or "")
    traffic_light = str(context.get("traffic_light") or "").lower() == "on"
    npc_count = int(context.get("npc_count") or 0)
    buckets = {"overall"}
    if route == "sample_map_route_2_to_104" and npc_count == 0 and not traffic_light:
        buckets.add("normal")
    if traffic_light:
        buckets.add("traffic_light")
    if route == "sample_map_tl_route_59_to_86":
        buckets.add("sharp_turn")
        if traffic_light:
            buckets.add("red_light_turn")
    if "nishishinjuku" in route:
        buckets.add("lane_change_or_merge")
    if npc_count > 0:
        buckets.add("npc_interaction")
    if npc_count >= 4:
        buckets.add("dense_scene")
    return sorted(buckets)


def _bucket_failures(
    by_bucket: dict[str, dict[str, Any]],
    *,
    min_progress_delta_ci_low: float,
    required_buckets: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    failures: dict[str, dict[str, Any]] = {}
    for bucket in required_buckets:
        metrics = by_bucket.get(bucket)
        if metrics is None:
            failures[bucket] = {"reason": "missing_bucket"}
        elif not _passes_metrics(metrics, min_progress_delta_ci_low):
            failures[bucket] = {
                "safety_ci_high": metrics["safety_cost_delta_vs_current"][
                    "ci95_high"
                ],
                "progress_ci_low": metrics["progress_delta_vs_current"][
                    "ci95_low"
                ],
                "hard_nonworse": metrics["hard_nonworse_vs_current"],
                "beneficial_preserved": metrics["beneficial_current_preserved_rate"],
            }
    return failures


def _passes_metrics(metrics: dict[str, Any], min_progress_delta_ci_low: float) -> bool:
    safety_high = metrics["safety_cost_delta_vs_current"]["ci95_high"]
    progress_low = metrics["progress_delta_vs_current"]["ci95_low"]
    return bool(
        safety_high is not None
        and safety_high < 0.0
        and progress_low is not None
        and progress_low >= float(min_progress_delta_ci_low)
        and metrics["hard_nonworse_vs_current"] >= 0.99
        and metrics["beneficial_current_preserved_rate"] >= 0.8
    )


def _rank(grid_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for report in grid_reports:
        overall = report["overall"]
        safety = overall["safety_cost_delta_vs_current"]
        progress = overall["progress_delta_vs_current"]
        rows.append(
            {
                "alpha": report["alpha"],
                "beta": report["beta"],
                "passed_joint_screen": report["passed_joint_screen"],
                "bucket_failure_count": len(report["bucket_failures"]),
                "safety_delta_mean": safety["mean"],
                "safety_delta_ci95_high": safety["ci95_high"],
                "safety_delta_cvar90": safety["cvar90_worst_tail"],
                "progress_delta_ci95_low": progress["ci95_low"],
                "changed_from_current_rate": overall["changed_from_current_rate"],
                "top1_selected_rate": overall["top1_selected_rate"],
                "beneficial_current_preserved_rate": overall[
                    "beneficial_current_preserved_rate"
                ],
                "hard_nonworse_vs_current": overall["hard_nonworse_vs_current"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            not row["passed_joint_screen"],
            int(row["bucket_failure_count"]),
            float(row["safety_delta_ci95_high"] or 0.0),
            float(row["changed_from_current_rate"]),
        ),
    )


def _decision(
    grid_reports: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    passed = [report for report in grid_reports if report["passed_joint_screen"]]
    opportunity = _opportunity_coverage(records)
    if passed:
        status = "joint_offline_screen_passed"
        next_step = (
            "inspect the passing rule for leakage and latency, then design a "
            "default-off implementation plan before any closed-loop smoke"
        )
    elif opportunity["safer_hard_nonworse_rate"] >= 0.05:
        status = "score_schema_gap_not_candidate_support_limit"
        next_step = (
            "do not promote this joint score; continue with state-conditioned "
            "or bucket-conditioned current-tick atoms that preserve beneficial "
            "CAMP decisions"
        )
    else:
        status = "candidate_support_limited"
        next_step = (
            "do not train CAMP on this candidate set; inspect DP candidate "
            "generation support before selector work"
        )
    return {
        "status": status,
        "passing_joint_candidates": len(passed),
        "closed_loop_deployment_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "training_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP-Prior Completion Joint Audit",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passing joint candidates: `{decision['passing_joint_candidates']}`",
        f"- Closed-loop deployment authorized: `{decision['closed_loop_deployment_authorized']}`",
        f"- Full36 authorized: `{decision['full36_authorized']}`",
        f"- Formal seeds authorized: `{decision['formal_seeds_authorized']}`",
        f"- Training authorized: `{decision['training_authorized']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Opportunity Coverage",
            "",
            "| Bucket | Records | Harmful | Beneficial | Safer hard-nonworse | Safer progress-nonworse | Harmful positive prior | Beneficial positive prior |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for bucket, row in report["opportunity_coverage"].items():
        lines.append(
            f"| `{bucket}` | {row['records']} | {row['harmful_current_records']} | "
            f"{row['beneficial_current_records']} | "
            f"{_fmt(row['safer_hard_nonworse_rate'])} | "
            f"{_fmt(row['safer_progress_nonworse_rate'])} | "
            f"{_fmt(row['harmful_with_positive_prior_rate'])} | "
            f"{_fmt(row['beneficial_with_positive_prior_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Ranked Joint Candidates",
            "",
            "| Alpha | Beta | Pass | Bucket failures | Safety mean | Safety CI high | CVaR90 | Progress CI low | Changed | Top1 rate | Beneficial preserved | Hard nonworse |",
            "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["ranked_candidates"][:20]:
        lines.append(
            f"| {_fmt(row['alpha'])} | {_fmt(row['beta'])} | "
            f"`{row['passed_joint_screen']}` | {row['bucket_failure_count']} | "
            f"{_fmt(row['safety_delta_mean'])} | "
            f"{_fmt(row['safety_delta_ci95_high'])} | "
            f"{_fmt(row['safety_delta_cvar90'])} | "
            f"{_fmt(row['progress_delta_ci95_low'])} | "
            f"{_fmt(row['changed_from_current_rate'])} | "
            f"{_fmt(row['top1_selected_rate'])} | "
            f"{_fmt(row['beneficial_current_preserved_rate'])} | "
            f"{_fmt(row['hard_nonworse_vs_current'])} |"
        )
    lines.extend(
        [
            "",
            "## Best Candidate Bucket Failures",
            "",
        ]
    )
    best = report["grid"][0] if not report["ranked_candidates"] else _find_grid(
        report["grid"],
        report["ranked_candidates"][0]["alpha"],
        report["ranked_candidates"][0]["beta"],
    )
    lines.append(
        f"Best ranked alpha/beta: `{best['alpha']}` / `{best['beta']}`."
    )
    if best["bucket_failures"]:
        lines.extend(
            [
                "",
                "| Bucket | Safety CI high | Progress CI low | Hard nonworse | Beneficial preserved |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for bucket, failure in best["bucket_failures"].items():
            lines.append(
                f"| `{bucket}` | {_fmt(failure.get('safety_ci_high'))} | "
                f"{_fmt(failure.get('progress_ci_low'))} | "
                f"{_fmt(failure.get('hard_nonworse'))} | "
                f"{_fmt(failure.get('beneficial_preserved'))} |"
            )
    else:
        lines.append("")
        lines.append("No required bucket failures for the best ranked candidate.")
    lines.extend(["", f"Next step: {decision['next_step']}", ""])
    return "\n".join(lines)


def _find_grid(
    grid: list[dict[str, Any]],
    alpha: float,
    beta: float,
) -> dict[str, Any]:
    for row in grid:
        if row["alpha"] == alpha and row["beta"] == beta:
            return row
    raise KeyError((alpha, beta))


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        result = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(result):
        return "n/a"
    return f"`{result:.6g}`"


if __name__ == "__main__":
    main()
