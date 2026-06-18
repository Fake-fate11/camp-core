#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_dp_prior_atom_candidate import (  # noqa: E402
    EPS,
    _conditional_rate,
    _nonnegative_float,
    _paired_summary,
    _summary,
)
from scripts.integrations.analyze_diffusion_planner_dp_prior_completion_joint_audit import (  # noqa: E402
    _load_records,
    _record_indices,
    _records_by_bucket,
    _select_with_joint_score,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SAFETY_COST_V1_CLIP,
    SAFETY_COST_V1_NORMALIZATION,
    SAFETY_COST_V1_WEIGHTS,
)


DEFAULT_BUCKETS = ("normal", "red_light_turn", "sharp_turn")
COMPONENTS = (
    "collision",
    "near_miss",
    "lane_violation",
    "realized_red_light",
    "planned_red_light",
    "mean_jerk",
    "mean_lateral_acceleration",
    "route_shortfall",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only attribution for the required buckets that blocked the "
            "DP-prior/progress joint offline screen."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--alpha", type=float, default=0.0)
    parser.add_argument("--beta", type=float, default=0.02)
    parser.add_argument("--prior_scale", type=float, required=True)
    parser.add_argument("--progress_scale", type=float, required=True)
    parser.add_argument("--bucket", action="append", default=None)
    parser.add_argument("--bootstrap_resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=12345)
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
        alpha=args.alpha,
        beta=args.beta,
        prior_scale=args.prior_scale,
        progress_scale=args.progress_scale,
        buckets=tuple(args.bucket) if args.bucket else DEFAULT_BUCKETS,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
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
    alpha: float = 0.0,
    beta: float = 0.02,
    prior_scale: float,
    progress_scale: float,
    buckets: tuple[str, ...] = DEFAULT_BUCKETS,
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
) -> dict[str, Any]:
    if not 0.0 <= float(alpha) < 1.0 or not 0.0 <= float(beta) < 1.0:
        raise ValueError("alpha and beta must be in [0, 1).")
    if float(alpha) + float(beta) >= 1.0:
        raise ValueError("alpha+beta must be < 1.")
    if prior_scale <= 0.0 or progress_scale <= 0.0:
        raise ValueError("prior_scale and progress_scale must be positive.")
    records = _load_records(paths)
    if not records:
        raise ValueError("No outcome-labeled records were found.")
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
    by_bucket = _records_by_bucket(records)
    bucket_reports = {}
    for bucket in buckets:
        bucket_records = by_bucket.get(bucket, [])
        if not bucket_records:
            bucket_reports[bucket] = {"records": 0, "missing": True}
            continue
        indices = _record_indices(records, bucket)
        bucket_reports[bucket] = _bucket_report(
            bucket_records,
            chosen[indices],
            selected[indices],
            top1[indices],
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
    return {
        "analysis": {
            "name": "dp_prior_completion_joint_bucket_failure_attribution_v1",
            "label": label,
            "alpha": float(alpha),
            "beta": float(beta),
            "prior_scale": float(prior_scale),
            "progress_scale": float(progress_scale),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "selection uses logged scores and current-tick atoms only; "
                "outcomes are used for posterior attribution"
            ),
            "math_boundary": (
                "This is a read-only finite-candidate attribution report. It "
                "does not modify DP, CAMP weights, atom schemas, or the robust "
                "master, and it is not classical Benders decomposition."
            ),
        },
        "records": {
            "logs": len({record["context"]["log_path"] for record in records}),
            "total": len(records),
            "candidate_count_values": sorted(
                {record["candidate_count"] for record in records}
            ),
            "buckets_requested": list(buckets),
        },
        "bucket_reports": bucket_reports,
        "decision": _decision(bucket_reports),
    }


def _bucket_report(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
    top1: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    costs = np.asarray([record["safety_cost"] for record in records], dtype=np.float64)
    progress = np.asarray(
        [record["outcome_progress"] for record in records],
        dtype=np.float64,
    )
    planned = np.asarray(
        [record["planned_progress"] for record in records],
        dtype=np.float64,
    )
    rows = np.arange(len(records))
    current_cost = costs[rows, selected]
    chosen_cost = costs[rows, chosen]
    top1_cost = costs[:, 0]
    safety_delta = chosen_cost - current_cost
    changed = chosen != selected
    harmful_change = changed & (safety_delta > EPS)
    beneficial_change = changed & (safety_delta < -EPS)
    current_harmful_vs_top1 = (current_cost - top1_cost) > EPS
    current_beneficial_vs_top1 = (top1_cost - current_cost) > EPS
    component_deltas = _component_delta_report(records, chosen, selected)
    support = _support_report(records, selected)
    return {
        "records": int(len(records)),
        "changed_from_current_rate": float(np.mean(changed)),
        "top1_selected_rate": float(np.mean(chosen == top1)),
        "changed_records": int(np.sum(changed)),
        "harmful_changed_records": int(np.sum(harmful_change)),
        "beneficial_changed_records": int(np.sum(beneficial_change)),
        "current_harmful_vs_top1_records": int(np.sum(current_harmful_vs_top1)),
        "current_beneficial_vs_top1_records": int(np.sum(current_beneficial_vs_top1)),
        "harmful_current_changed_rate": _conditional_rate(
            changed,
            current_harmful_vs_top1,
        ),
        "beneficial_current_preserved_rate": _conditional_rate(
            chosen == selected,
            current_beneficial_vs_top1,
        ),
        "safety_cost_delta_vs_current": _summary_with_cvar(
            safety_delta,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_current": _paired_summary(
            progress[rows, chosen] - progress[rows, selected],
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "planned_progress_delta_vs_current": _paired_summary(
            planned[rows, chosen] - planned[rows, selected],
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "hard_nonworse_vs_current": _hard_nonworse_rate(records, chosen, selected),
        "component_deltas_chosen_minus_current": component_deltas,
        "support": support,
        "worst_changed_records": _worst_records(records, chosen, selected, limit=8),
    }


def _component_delta_report(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
) -> dict[str, Any]:
    rows: dict[str, list[float]] = {key: [] for key in COMPONENTS}
    for record, chosen_idx, selected_idx in zip(records, chosen, selected):
        chosen_components = _candidate_components(record, int(chosen_idx))
        selected_components = _candidate_components(record, int(selected_idx))
        for key in COMPONENTS:
            rows[key].append(chosen_components[key] - selected_components[key])
    return {key: _summary(values) for key, values in rows.items()}


def _candidate_components(record: dict[str, Any], index: int) -> dict[str, float]:
    outcome = record["outcomes"][index]
    progress = record["outcome_progress"]
    feasible = record["feasible"]
    branch = feasible if bool(feasible.any()) else np.ones_like(feasible, dtype=bool)
    progress_ref = float(np.max(progress[branch]))
    progress_denom = max(progress_ref, 1.0)
    planned_red = record.get("planned_red")
    if planned_red is None:
        planned_red = np.zeros(len(progress), dtype=np.float64)
    return {
        "collision": float(bool(outcome["collision"]))
        * SAFETY_COST_V1_WEIGHTS["collision"],
        "near_miss": float(bool(outcome["near_miss"]))
        * SAFETY_COST_V1_WEIGHTS["near_miss"],
        "lane_violation": float(bool(outcome["lane_violation"]))
        * SAFETY_COST_V1_WEIGHTS["lane_violation"],
        "realized_red_light": float(bool(outcome["red_light_violation"]))
        * SAFETY_COST_V1_WEIGHTS["realized_red_light"],
        "planned_red_light": min(max(float(planned_red[index]), 0.0), 1.0)
        * SAFETY_COST_V1_WEIGHTS["planned_red_light"],
        "mean_jerk": min(
            _nonnegative_float(outcome, "mean_jerk_mps3")
            / SAFETY_COST_V1_NORMALIZATION["mean_jerk_magnitude_mps3"],
            SAFETY_COST_V1_CLIP,
        )
        * SAFETY_COST_V1_WEIGHTS["mean_jerk"],
        "mean_lateral_acceleration": min(
            _nonnegative_float(outcome, "mean_lateral_acceleration_mps2")
            / SAFETY_COST_V1_NORMALIZATION["mean_lateral_acceleration_mps2"],
            SAFETY_COST_V1_CLIP,
        )
        * SAFETY_COST_V1_WEIGHTS["mean_lateral_acceleration"],
        "route_shortfall": min(
            max(
                (
                    progress_ref
                    - _nonnegative_float(outcome, "progress_m")
                )
                / progress_denom,
                0.0,
            ),
            1.0,
        )
        * SAFETY_COST_V1_WEIGHTS["route_shortfall"],
    }


def _support_report(records: list[dict[str, Any]], selected: np.ndarray) -> dict[str, Any]:
    rows = []
    for record, selected_idx in zip(records, selected):
        current_cost = float(record["safety_cost"][int(selected_idx)])
        current_progress = float(record["outcome_progress"][int(selected_idx)])
        current_planned = float(record["planned_progress"][int(selected_idx)])
        safer = record["safety_cost"] < current_cost - EPS
        hard_nonworse = np.asarray(
            [
                all(
                    float(bool(outcome[field]))
                    <= float(bool(record["outcomes"][int(selected_idx)][field]))
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
        rows.append(
            {
                "safer": bool(np.any(safer)),
                "safer_hard_nonworse": bool(np.any(safer & hard_nonworse)),
                "safer_progress_nonworse": bool(
                    np.any(safer & hard_nonworse & progress_nonworse)
                ),
                "safer_planned_progress_nonworse": bool(
                    np.any(safer & hard_nonworse & planned_nonworse)
                ),
            }
        )
    return {
        "safer_candidate_rate": float(np.mean([row["safer"] for row in rows])),
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


def _hard_nonworse_rate(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
) -> float:
    rows = []
    for record, chosen_idx, selected_idx in zip(records, chosen, selected):
        chosen_outcome = record["outcomes"][int(chosen_idx)]
        selected_outcome = record["outcomes"][int(selected_idx)]
        rows.append(
            all(
                float(bool(chosen_outcome[field]))
                <= float(bool(selected_outcome[field]))
                for field in (
                    "collision",
                    "near_miss",
                    "lane_violation",
                    "red_light_violation",
                )
            )
        )
    return float(np.mean(rows)) if rows else 0.0


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


def _worst_records(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    rows = []
    for record, chosen_idx, selected_idx in zip(records, chosen, selected):
        delta = float(
            record["safety_cost"][int(chosen_idx)]
            - record["safety_cost"][int(selected_idx)]
        )
        if chosen_idx == selected_idx:
            continue
        rows.append(
            {
                "delta": delta,
                "chosen": int(chosen_idx),
                "selected": int(selected_idx),
                "route": record["context"]["route"],
                "seed": record["context"]["seed"],
                "npc_count": record["context"]["npc_count"],
                "traffic_light": record["context"]["traffic_light"],
                "record_index": record["context"]["record_index"],
                "chosen_planned_progress": float(record["planned_progress"][int(chosen_idx)]),
                "selected_planned_progress": float(
                    record["planned_progress"][int(selected_idx)]
                ),
                "chosen_outcome_progress": float(record["outcome_progress"][int(chosen_idx)]),
                "selected_outcome_progress": float(
                    record["outcome_progress"][int(selected_idx)]
                ),
            }
        )
    rows.sort(key=lambda row: row["delta"], reverse=True)
    return rows[:limit]


def _decision(bucket_reports: dict[str, Any]) -> dict[str, Any]:
    missing = [bucket for bucket, report in bucket_reports.items() if report.get("missing")]
    failed = []
    support_limited = []
    for bucket, report in bucket_reports.items():
        if report.get("missing"):
            continue
        safety_high = report["safety_cost_delta_vs_current"]["ci95_high"]
        if safety_high is None or safety_high >= 0.0:
            failed.append(bucket)
        if report["support"]["safer_hard_nonworse_rate"] < 0.05:
            support_limited.append(bucket)
    return {
        "status": (
            "missing_bucket_data"
            if missing
            else "bucket_failures_attributed"
            if failed
            else "no_bucket_failure_found"
        ),
        "missing_buckets": missing,
        "failed_buckets": failed,
        "support_limited_buckets": support_limited,
        "training_authorized": False,
        "online_selector_change_authorized": False,
        "formal_seeds_authorized": False,
        "next_step": (
            "use component and support attribution to design a predeclared "
            "state-conditioned offline rule; do not run closed-loop smoke yet"
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-Prior Completion Joint Bucket Failure Attribution",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['decision']['status']}`",
        f"- Failed buckets: `{report['decision']['failed_buckets']}`",
        f"- Support-limited buckets: `{report['decision']['support_limited_buckets']}`",
        f"- Training authorized: `{report['decision']['training_authorized']}`",
        f"- Online selector change authorized: `{report['decision']['online_selector_change_authorized']}`",
        f"- Formal seeds authorized: `{report['decision']['formal_seeds_authorized']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Bucket Summary",
        "",
        "| Bucket | Records | Changed | Harmful changed | Beneficial changed | Safety mean | Safety CI high | CVaR90 | Progress CI low | Hard nonworse | Support hard-nonworse | Support progress-nonworse |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for bucket, row in report["bucket_reports"].items():
        if row.get("missing"):
            lines.append(f"| `{bucket}` | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        safety = row["safety_cost_delta_vs_current"]
        progress = row["progress_delta_vs_current"]
        support = row["support"]
        lines.append(
            f"| `{bucket}` | {row['records']} | {_fmt(row['changed_from_current_rate'])} | "
            f"{row['harmful_changed_records']} | {row['beneficial_changed_records']} | "
            f"{_fmt(safety['mean'])} | {_fmt(safety['ci95_high'])} | "
            f"{_fmt(safety['cvar90_worst_tail'])} | {_fmt(progress['ci95_low'])} | "
            f"{_fmt(row['hard_nonworse_vs_current'])} | "
            f"{_fmt(support['safer_hard_nonworse_rate'])} | "
            f"{_fmt(support['safer_progress_nonworse_rate'])} |"
        )
    lines.extend(["", "## Component Deltas", ""])
    for bucket, row in report["bucket_reports"].items():
        if row.get("missing"):
            continue
        lines.extend(
            [
                f"### `{bucket}`",
                "",
                "| Component | Mean chosen-current | P95 | Max |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for component, stats in row["component_deltas_chosen_minus_current"].items():
            lines.append(
                f"| `{component}` | {_fmt(stats['mean'])} | "
                f"{_fmt(stats['p95'])} | {_fmt(stats['max'])} |"
            )
        lines.append("")
    lines.extend(["## Worst Changed Records", ""])
    for bucket, row in report["bucket_reports"].items():
        if row.get("missing"):
            continue
        lines.extend(
            [
                f"### `{bucket}`",
                "",
                "| Delta | Route | Seed | NPC | TL | Record | Selected -> Chosen | Planned progress | Outcome progress |",
                "| ---: | --- | ---: | ---: | --- | ---: | --- | --- | --- |",
            ]
        )
        for item in row["worst_changed_records"]:
            lines.append(
                f"| {_fmt(item['delta'])} | `{item['route']}` | {item['seed']} | "
                f"{item['npc_count']} | `{item['traffic_light']}` | "
                f"{item['record_index']} | {item['selected']} -> {item['chosen']} | "
                f"{_fmt(item['selected_planned_progress'])} -> {_fmt(item['chosen_planned_progress'])} | "
                f"{_fmt(item['selected_outcome_progress'])} -> {_fmt(item['chosen_outcome_progress'])} |"
            )
        lines.append("")
    lines.append(f"Next step: {report['decision']['next_step']}")
    lines.append("")
    return "\n".join(lines)


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
