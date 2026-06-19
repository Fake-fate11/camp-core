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

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
    parse_selection_log_metadata,
)
from scripts.integrations.analyze_diffusion_planner_first_step_graft_potential import (  # noqa: E402
    HORIZONS,
    TOL,
    _fmt,
    _min_deficit_candidate,
    _safety_joint_comfort_mask,
    _summary,
)
from scripts.integrations.analyze_diffusion_planner_materiality_gap import (  # noqa: E402
    FORMAL_SEEDS,
    ROLLOUT_METRICS,
    VECTOR_FIELDS,
    _load_record,
    _row,
)


GROUP_SIGNAL_KEYS = (
    "tracker_command_jerk_delta_mps3",
    "tracker_command_lateral_delta_mps2",
    "prefix_jerk_proxy_delta",
    "rollout_h3_mean_vector_jerk_mps3_delta",
    "rollout_h3_mean_lateral_acceleration_mps2_delta",
)
RAW_GAIN_KEYS = (
    "raw_dp_prior_jerk_excess_delta",
    "raw_horizon_lateral_delta",
)
OUTCOME_KEYS = (
    "outcome_progress_delta_m",
    "outcome_progress_deficit_m",
    "outcome_jerk_delta_mps3",
    "outcome_lateral_delta_mps2",
    "outcome_value_delta",
)
BASE_DESCRIPTOR_KEYS = (
    "raw_route_progress_delta_m",
    "raw_step_reach_delta_m",
    "raw_dp_prior_jerk_excess_delta",
    "raw_dp_prior_lateral_excess_delta",
    "raw_horizon_lateral_delta",
    "raw_horizon_yaw_delta",
    "tracker_first_step_reach_delta_m",
    "tracker_tail_average_speed_delta_mps",
    "tracker_target_speed_delta_mps",
    "tracker_command_yaw_rate_delta_rps",
    "prefix_max_xy_distance_m",
    "prefix_mean_xy_distance_m",
)
MIN_GROUP_RECORDS = 100
SEPARATION_THRESHOLD = 0.75
EPS = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "State-conditioned postprocess/tracker descriptor audit for DP+CAMP "
            "materiality rows. Posterior outcomes choose oracle donors only; "
            "descriptor separation uses current-tick finite-candidate values."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_group_records", type=int, default=MIN_GROUP_RECORDS)
    parser.add_argument(
        "--separation_threshold",
        type=float,
        default=SEPARATION_THRESHOLD,
    )
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        min_group_records=args.min_group_records,
        separation_threshold=args.separation_threshold,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
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
    min_group_records: int = MIN_GROUP_RECORDS,
    separation_threshold: float = SEPARATION_THRESHOLD,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    rows: list[dict[str, Any]] = []
    total_records = 0
    nonfallback_records = 0
    no_donor_records = 0
    formal_seed_logs = 0
    for log_path in log_paths:
        metadata = parse_selection_log_metadata(log_path)
        formal_seed = metadata.seed in FORMAL_SEEDS
        formal_seed_logs += int(formal_seed)
        if formal_seed and fail_on_formal_seeds:
            raise ValueError(f"Formal seed log is forbidden: {log_path}")
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, raw_record in enumerate(payload):
            total_records += 1
            record = _load_record(raw_record, f"{log_path} record {index}")
            if not record["feasible"].any():
                continue
            nonfallback_records += 1
            donor_mask = _safety_joint_comfort_mask(record)
            if not donor_mask.any():
                no_donor_records += 1
                continue
            donor = _min_deficit_candidate(record, donor_mask)
            row = _row(record, donor)
            row.update(
                {
                    "route": metadata.route,
                    "seed": metadata.seed,
                    "npc_count": metadata.npc_count,
                    "traffic_light": metadata.traffic_light,
                    "mode": metadata.mode,
                }
            )
            rows.append(row)

    counts = {
        "logs": len(log_paths),
        "formal_seed_logs": formal_seed_logs,
        "total": total_records,
        "nonfallback": nonfallback_records,
        "fallback": total_records - nonfallback_records,
        "with_oracle_donor": len(rows),
        "without_oracle_donor": no_donor_records,
    }
    return analyze_materiality_rows(
        rows,
        label=label,
        record_counts=counts,
        min_group_records=min_group_records,
        separation_threshold=separation_threshold,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_materiality_rows(
    rows: list[dict[str, Any]],
    *,
    label: str | None = None,
    record_counts: dict[str, int] | None = None,
    min_group_records: int = MIN_GROUP_RECORDS,
    separation_threshold: float = SEPARATION_THRESHOLD,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if min_group_records < 1:
        raise ValueError("min_group_records must be positive.")
    if separation_threshold < 0.0:
        raise ValueError("separation_threshold must be nonnegative.")
    counts = record_counts or {
        "logs": 0,
        "formal_seed_logs": 0,
        "total": len(rows),
        "nonfallback": len(rows),
        "fallback": 0,
        "with_oracle_donor": len(rows),
        "without_oracle_donor": 0,
    }
    if fail_on_formal_seeds and counts.get("formal_seed_logs", 0):
        raise ValueError("Formal seed logs are forbidden.")

    raw_gain_rows = [row for row in rows if _has_raw_gain(row)]
    preserved = [row for row in raw_gain_rows if _deployable_preserved(row)]
    flipped = [row for row in raw_gain_rows if not _deployable_preserved(row)]
    signal_separation = _separation_report(
        preserved,
        flipped,
        GROUP_SIGNAL_KEYS,
    )
    descriptor_separation = _separation_report(
        preserved,
        flipped,
        _descriptor_keys(),
    )
    decision = _decision(
        rows,
        raw_gain_rows,
        preserved,
        flipped,
        descriptor_separation,
        min_group_records=min_group_records,
        separation_threshold=separation_threshold,
    )
    return {
        "analysis": {
            "name": "dp_camp_postprocess_tracker_descriptor_audit_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "posterior outcomes choose safety-preserving joint-comfort "
                "oracle donors and group labels only; reported descriptor "
                "separation uses fixed current-tick finite-candidate values"
            ),
            "group_definition": (
                "raw-gain donor rows are preserved when tracker jerk, tracker "
                "lateral, postprocessed prefix jerk, H3 rollout jerk, and H3 "
                "rollout lateral all improve. They are flipped when at least "
                "one of those deployable-layer signals fails to improve."
            ),
            "raw_gain_keys": list(RAW_GAIN_KEYS),
            "group_signal_keys": list(GROUP_SIGNAL_KEYS),
            "descriptor_keys": list(_descriptor_keys()),
            "gate": {
                "min_group_records": int(min_group_records),
                "descriptor_standardized_abs_difference_ge": float(
                    separation_threshold
                ),
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. The audit "
                "uses fixed finite candidate quantities available at the "
                "current tick. Signed deltas are diagnostic descriptors; a "
                "future CAMP atom would need to use nonnegative base costs or "
                "split signed deltas into nonnegative parts so the candidate "
                "score remains affine a_k^T w and the simplex/CVaR/L2 master "
                "stays convex. This is not classical Benders decomposition "
                "because no DP-side master/subproblem, dual, or valid cuts are "
                "constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": {
            **counts,
            "raw_gain_donor_rows": len(raw_gain_rows),
            "preserved_rows": len(preserved),
            "flipped_rows": len(flipped),
        },
        "groups": {
            "all_oracle_donors": _group_report(rows),
            "raw_gain_donors": _group_report(raw_gain_rows),
            "preserved_deployable_comfort": _group_report(preserved),
            "flipped_deployable_comfort": _group_report(flipped),
        },
        "group_signal_separation": signal_separation,
        "descriptor_separation": descriptor_separation,
        "final_decision": decision,
    }


def _has_raw_gain(row: dict[str, Any]) -> bool:
    return any(_finite(row.get(key)) < -TOL for key in RAW_GAIN_KEYS)


def _deployable_preserved(row: dict[str, Any]) -> bool:
    return all(_finite(row.get(key)) < -TOL for key in GROUP_SIGNAL_KEYS)


def _descriptor_keys() -> tuple[str, ...]:
    keys = list(BASE_DESCRIPTOR_KEYS)
    for horizon in HORIZONS:
        keys.extend(
            [
                f"prefix_h{horizon}_displacement_delta_m",
                f"prefix_h{horizon}_path_delta_m",
            ]
        )
        for metric in ROLLOUT_METRICS:
            key = f"rollout_h{horizon}_{metric}_delta"
            if key not in GROUP_SIGNAL_KEYS:
                keys.append(key)
    return tuple(dict.fromkeys(keys))


def _group_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "rates": {
            "raw_gain_rate": _rate(rows, _has_raw_gain),
            "deployable_preserved_rate": _rate(rows, _deployable_preserved),
        },
        "outcomes": {
            key: _finite_summary(row.get(key) for row in rows)
            for key in OUTCOME_KEYS
        },
        "signals": {
            key: _finite_summary(row.get(key) for row in rows)
            for key in GROUP_SIGNAL_KEYS
        },
    }


def _separation_report(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    items = []
    for key in keys:
        left = _finite_values(row.get(key) for row in left_rows)
        right = _finite_values(row.get(key) for row in right_rows)
        if not left or not right:
            continue
        left_arr = np.asarray(left, dtype=np.float64)
        right_arr = np.asarray(right, dtype=np.float64)
        left_mean = float(np.mean(left_arr))
        right_mean = float(np.mean(right_arr))
        mean_difference = left_mean - right_mean
        pooled = _pooled_scale(left_arr, right_arr)
        standardized = mean_difference / pooled if pooled > EPS else 0.0
        items.append(
            {
                "key": key,
                "left_count": int(left_arr.size),
                "right_count": int(right_arr.size),
                "preserved_mean": left_mean,
                "flipped_mean": right_mean,
                "mean_difference_preserved_minus_flipped": mean_difference,
                "standardized_difference": standardized,
                "standardized_abs_difference": abs(standardized),
                "preserved": _summary(left),
                "flipped": _summary(right),
            }
        )
    items.sort(
        key=lambda item: (
            -float(item["standardized_abs_difference"]),
            str(item["key"]),
        )
    )
    return {
        "left_label": "preserved_deployable_comfort",
        "right_label": "flipped_deployable_comfort",
        "top": items[:20],
    }


def _decision(
    rows: list[dict[str, Any]],
    raw_gain_rows: list[dict[str, Any]],
    preserved: list[dict[str, Any]],
    flipped: list[dict[str, Any]],
    descriptor_separation: dict[str, Any],
    *,
    min_group_records: int,
    separation_threshold: float,
) -> dict[str, Any]:
    top = descriptor_separation["top"][0] if descriptor_separation["top"] else None
    if not rows:
        status = "postprocess_tracker_audit_no_oracle_donors"
        reasons = ["no_safety_preserving_joint_comfort_oracle_donor"]
        next_step = (
            "Reject descriptor calibration for this artifact and inspect "
            "candidate-generation support."
        )
    elif len(raw_gain_rows) < min_group_records:
        status = "postprocess_tracker_audit_raw_gain_support_insufficient"
        reasons = ["too_few_raw_gain_donor_rows"]
        next_step = (
            "Reject this audit as underpowered; do not promote a selector or "
            "run replay from it."
        )
    elif len(preserved) < min_group_records or len(flipped) < min_group_records:
        status = "postprocess_tracker_audit_group_support_insufficient"
        reasons = ["too_few_preserved_or_flipped_rows"]
        next_step = (
            "Reject state-conditioned selector calibration until both preserved "
            "and flipped donor groups have enough support."
        )
    elif top and float(top["standardized_abs_difference"]) >= separation_threshold:
        status = "state_conditioned_descriptor_signal_present"
        reasons = ["current_tick_descriptor_separates_preserved_and_flipped_rows"]
        next_step = (
            "Predeclare a no-leak offline selector screen using only legally "
            "atomizable current-tick descriptors; do not run online replay yet."
        )
    else:
        status = "postprocess_tracker_descriptor_signal_insufficient"
        reasons = ["no_candidate_descriptor_separates_preserved_and_flipped_rows"]
        next_step = (
            "Reject further selector calibration from this descriptor family and "
            "return to candidate-generation or postprocess support analysis."
        )
    return {
        "status": status,
        "reasons": reasons,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "top_descriptor": top,
        "next_step": next_step,
    }


def _finite_summary(values: Any) -> dict[str, float | int | None]:
    return _summary(_finite_values(values))


def _finite_values(values: Any) -> list[float]:
    finite = []
    for value in values:
        numeric = _finite(value)
        if np.isfinite(numeric):
            finite.append(numeric)
    return finite


def _finite(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return numeric if np.isfinite(numeric) else float("nan")


def _pooled_scale(left: np.ndarray, right: np.ndarray) -> float:
    if left.size + right.size < 3:
        return float(np.std(np.concatenate([left, right])))
    left_var = float(np.var(left, ddof=1)) if left.size > 1 else 0.0
    right_var = float(np.var(right, ddof=1)) if right.size > 1 else 0.0
    denom = left.size + right.size - 2
    pooled = float(
        np.sqrt(((left.size - 1) * left_var + (right.size - 1) * right_var) / denom)
    )
    if pooled > EPS:
        return pooled
    return float(np.std(np.concatenate([left, right])))


def _rate(rows: list[dict[str, Any]], predicate: Any) -> float:
    return sum(bool(predicate(row)) for row in rows) / max(len(rows), 1)


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    decision = report["final_decision"]
    groups = report["groups"]
    top_descriptor = decision.get("top_descriptor")
    lines = [
        "# DP CAMP Postprocess/Tracker Descriptor Audit",
        "",
        "This is a read-only offline diagnostic. It does not run DP, train CAMP, "
        "change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Online selector authorized: `{decision['online_selector_authorized']}`",
        f"- Closed-loop smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        f"- Top descriptor: `{top_descriptor['key'] if top_descriptor else 'n/a'}`",
        "",
        "Reasons:",
    ]
    for reason in decision["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            "## Records",
            "",
            f"- Label: `{label}`",
            f"- Logs: {records['logs']}",
            f"- Formal seed logs: {records['formal_seed_logs']}",
            f"- Records: {records['total']}",
            f"- Nonfallback records: {records['nonfallback']}",
            f"- With oracle donors: {records['with_oracle_donor']}",
            f"- Raw-gain donor rows: {records['raw_gain_donor_rows']}",
            f"- Preserved rows: {records['preserved_rows']}",
            f"- Flipped rows: {records['flipped_rows']}",
            "",
            "Oracle donors are selected with posterior outcome labels for "
            "diagnosis only. Preserved/flipped groups are labels for this audit; "
            "they are not runtime selector inputs.",
            "",
            "## Group Outcomes",
            "",
            "| Group | Count | Progress mean | Jerk mean | Lateral mean | Preserved rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in (
        "all_oracle_donors",
        "raw_gain_donors",
        "preserved_deployable_comfort",
        "flipped_deployable_comfort",
    ):
        group = groups[name]
        outcomes = group["outcomes"]
        lines.append(
            f"| `{name}` | {group['count']} | "
            f"{_fmt(outcomes['outcome_progress_delta_m']['mean'])} | "
            f"{_fmt(outcomes['outcome_jerk_delta_mps3']['mean'])} | "
            f"{_fmt(outcomes['outcome_lateral_delta_mps2']['mean'])} | "
            f"{group['rates']['deployable_preserved_rate']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Top Candidate Descriptors",
            "",
            "| Descriptor | Preserved mean | Flipped mean | Std abs diff |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for item in report["descriptor_separation"]["top"][:10]:
        lines.append(
            f"| `{item['key']}` | {_fmt(item['preserved_mean'])} | "
            f"{_fmt(item['flipped_mean'])} | "
            f"{float(item['standardized_abs_difference']):.6f} |"
        )
    lines.extend(
        [
            "",
            "## Group-Defining Signals",
            "",
            "| Signal | Preserved mean | Flipped mean | Std abs diff |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for item in report["group_signal_separation"]["top"]:
        lines.append(
            f"| `{item['key']}` | {_fmt(item['preserved_mean'])} | "
            f"{_fmt(item['flipped_mean'])} | "
            f"{float(item['standardized_abs_difference']):.6f} |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            f"Next step: {decision['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
