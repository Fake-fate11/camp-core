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
)


HORIZONS = (3, 5, 10)
ROLLOUT_METRICS = {
    "mean_vector_jerk_mps3": "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2": "mean_lateral_acceleration_mps2",
}
EXISTING_FEATURES = {
    "dp_prior_jerk_excess": (
        "candidate_dp_prior_jerk_excess_cost",
        "mean_jerk_mps3",
    ),
    "horizon_lateral_acceleration": (
        "candidate_horizon_lateral_acceleration_cost",
        "mean_lateral_acceleration_mps2",
    ),
    "dp_prior_lateral_acceleration_excess": (
        "candidate_dp_prior_lateral_acceleration_excess_cost",
        "mean_lateral_acceleration_mps2",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit outcome-free PerfectTracker rollout features against "
            "candidate closed-loop labels before versioning the CAMP schema."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def analyze(paths: list[Path]) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    feature_rows: dict[str, list[dict[str, Any]]] = {}
    for name, (_, target) in EXISTING_FEATURES.items():
        feature_rows[name] = _new_feature_rows(target)
    for horizon in HORIZONS:
        for metric, target in ROLLOUT_METRICS.items():
            feature_rows[f"rollout_h{horizon}_{metric}"] = _new_feature_rows(
                target
            )

    total_records = 0
    total_candidates = 0
    fallback_records = 0
    for log_path in log_paths:
        records = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(records, list) or not records:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(records):
            label = f"{log_path} record {record_index}"
            total_records += 1
            outcomes = _outcome_arrays(record, label)
            candidate_count = outcomes["mean_jerk_mps3"].size
            total_candidates += candidate_count
            feasible = _vector(
                record.get("feasible_mask"),
                candidate_count,
                f"{label} feasible_mask",
                boolean=True,
            )
            fallback_records += int(not feasible.any())
            outcome_safe = feasible & outcomes["feasible"]

            rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
            if not isinstance(rollout, dict):
                raise ValueError(f"{label} is missing rollout metrics.")
            for horizon in HORIZONS:
                horizon_metrics = rollout.get(str(horizon), rollout.get(horizon))
                if not isinstance(horizon_metrics, dict):
                    raise ValueError(
                        f"{label} is missing rollout horizon {horizon}."
                    )
                for metric, target in ROLLOUT_METRICS.items():
                    values = _vector(
                        horizon_metrics.get(metric),
                        candidate_count,
                        f"{label} H{horizon} {metric}",
                    )
                    _append_feature_row(
                        feature_rows[f"rollout_h{horizon}_{metric}"],
                        values,
                        outcomes[target],
                        feasible,
                        outcome_safe,
                    )

            for name, (field, target) in EXISTING_FEATURES.items():
                raw_values = record.get(field)
                if raw_values is None:
                    feature_rows[name][0]["missing_records"] += 1
                    continue
                values = _vector(
                    raw_values,
                    candidate_count,
                    f"{label} {field}",
                )
                _append_feature_row(
                    feature_rows[name],
                    values,
                    outcomes[target],
                    feasible,
                    outcome_safe,
                )

    features = {
        name: _summarize_feature(rows, total_records)
        for name, rows in feature_rows.items()
    }
    return {
        "analysis": {
            "name": "dp_camp_rollout_outcome_alignment_v1",
            "horizons": list(HORIZONS),
            "online_feature_provenance": (
                "fixed current-tick candidate PerfectTracker rollout"
            ),
            "outcome_role": "offline label only",
            "future_outcome_leakage": False,
            "convexity_scope": (
                "For a fixed finite candidate set each feature is a "
                "nonnegative constant, so a weighted score is affine in w. "
                "No convexity claim is made in trajectory coordinates."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": total_records,
            "candidates": total_candidates,
            "fallback": fallback_records,
        },
        "features": features,
    }


def _new_feature_rows(target: str) -> list[dict[str, Any]]:
    return [
        {
            "target": target,
            "missing_records": 0,
            "records": [],
        }
    ]


def _append_feature_row(
    rows: list[dict[str, Any]],
    feature: np.ndarray,
    target: np.ndarray,
    feasible: np.ndarray,
    outcome_safe: np.ndarray,
) -> None:
    rows[0]["records"].append(
        {
            "feature": feature,
            "target": target,
            "feasible": feasible,
            "outcome_safe": outcome_safe,
        }
    )


def _outcome_arrays(record: dict[str, Any], label: str) -> dict[str, np.ndarray]:
    outcomes = record.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        raise ValueError(f"{label} is missing candidate closed-loop outcomes.")
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(
                f"{label} outcome candidate indices must be contiguous."
            )
    result: dict[str, np.ndarray] = {}
    for field in ("mean_jerk_mps3", "mean_lateral_acceleration_mps2"):
        result[field] = _vector(
            [outcome.get(field) for outcome in outcomes],
            len(outcomes),
            f"{label} outcome {field}",
        )
    result["feasible"] = _vector(
        [outcome.get("feasible") for outcome in outcomes],
        len(outcomes),
        f"{label} outcome feasible",
        boolean=True,
    )
    return result


def _vector(
    values: Any,
    size: int,
    label: str,
    *,
    boolean: bool = False,
) -> np.ndarray:
    if boolean:
        raw = np.asarray(values, dtype=object).reshape(-1)
        if not all(isinstance(value, (bool, np.bool_)) for value in raw):
            raise ValueError(f"{label} must contain booleans.")
        array = raw.astype(bool)
    else:
        array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    if not boolean:
        if not np.all(np.isfinite(array)):
            raise ValueError(f"{label} must be finite.")
        if np.any(array < 0.0):
            raise ValueError(f"{label} must be nonnegative.")
    return array


def _summarize_feature(
    rows: list[dict[str, Any]],
    total_records: int,
) -> dict[str, Any]:
    state = rows[0]
    records = state["records"]
    all_feature: list[float] = []
    all_target: list[float] = []
    feasible_feature: list[float] = []
    feasible_target: list[float] = []
    safe_feature: list[float] = []
    safe_target: list[float] = []
    gap_feature: list[float] = []
    gap_target: list[float] = []
    variation_records = 0
    eligible_variation_records = 0
    oracle_matches = 0
    oracle_records = 0
    pair_agreements = 0
    pair_total = 0
    pair_possible = 0

    for record in records:
        feature = record["feature"]
        target = record["target"]
        feasible = record["feasible"]
        outcome_safe = record["outcome_safe"]
        all_feature.extend(feature.tolist())
        all_target.extend(target.tolist())
        if feasible.any():
            f_values = feature[feasible]
            t_values = target[feasible]
            feasible_feature.extend(f_values.tolist())
            feasible_target.extend(t_values.tolist())
            gap_feature.extend((f_values - feature[0]).tolist())
            gap_target.extend((t_values - target[0]).tolist())
            eligible_variation_records += 1
            variation_records += int(np.ptp(f_values) > 1e-12)
            oracle_records += 1
            oracle_matches += int(
                _masked_argmin(feature, feasible)
                == _masked_argmin(target, feasible)
            )
            agreements, comparisons = _pairwise_order_agreement(
                f_values,
                t_values,
            )
            pair_agreements += agreements
            pair_total += comparisons
            pair_possible += f_values.size * (f_values.size - 1) // 2
        if outcome_safe.any():
            safe_feature.extend(feature[outcome_safe].tolist())
            safe_target.extend(target[outcome_safe].tolist())

    positive = np.asarray(all_feature, dtype=np.float64)
    positive = positive[positive > 0.0]
    return {
        "target": state["target"],
        "record_availability_rate": len(records) / max(total_records, 1),
        "missing_records": int(state["missing_records"]),
        "finite_nonnegative": True,
        "feasible_records_with_variation": variation_records,
        "feasible_record_variation_rate": (
            variation_records / eligible_variation_records
            if eligible_variation_records
            else None
        ),
        "candidate_pearson": _safe_corr(all_feature, all_target),
        "candidate_spearman": _safe_corr(
            _rankdata(all_feature),
            _rankdata(all_target),
        ),
        "feasible_candidate_pearson": _safe_corr(
            feasible_feature,
            feasible_target,
        ),
        "feasible_candidate_spearman": _safe_corr(
            _rankdata(feasible_feature),
            _rankdata(feasible_target),
        ),
        "outcome_safe_feasible_candidate_pearson": _safe_corr(
            safe_feature,
            safe_target,
        ),
        "feasible_top1_gap_pearson": _safe_corr(gap_feature, gap_target),
        "feasible_oracle_match_rate": (
            oracle_matches / oracle_records if oracle_records else None
        ),
        "feasible_pairwise_order_agreement_rate": (
            pair_agreements / pair_total if pair_total else None
        ),
        "feasible_pairwise_comparable_pairs": int(pair_total),
        "feasible_pairwise_possible_pairs": int(pair_possible),
        "feasible_pairwise_comparable_coverage_rate": (
            pair_total / pair_possible if pair_possible else None
        ),
        "positive_p95_scale": (
            float(np.percentile(positive, 95.0)) if positive.size else 1.0
        ),
    }


def _masked_argmin(values: np.ndarray, mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    return int(indices[np.argmin(values[indices])])


def _pairwise_order_agreement(
    feature: np.ndarray,
    target: np.ndarray,
) -> tuple[int, int]:
    agreements = 0
    total = 0
    for left in range(feature.size):
        for right in range(left + 1, feature.size):
            feature_delta = feature[left] - feature[right]
            target_delta = target[left] - target[right]
            if abs(feature_delta) <= 1e-12 or abs(target_delta) <= 1e-12:
                continue
            agreements += int(np.sign(feature_delta) == np.sign(target_delta))
            total += 1
    return agreements, total


def _rankdata(values: list[float]) -> list[float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return []
    order = np.argsort(array, kind="mergesort")
    ranks = np.empty(array.size, dtype=np.float64)
    start = 0
    while start < array.size:
        end = start + 1
        while end < array.size and array[order[end]] == array[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1)
        start = end
    return ranks.tolist()


def _safe_corr(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    lhs = np.asarray(left, dtype=np.float64)
    rhs = np.asarray(right, dtype=np.float64)
    if np.std(lhs) <= 1e-12 or np.std(rhs) <= 1e-12:
        return None
    return float(np.corrcoef(lhs, rhs)[0, 1])


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    lines = [
        "# DP CAMP Rollout-to-Outcome Alignment",
        "",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Candidates: {records['candidates']}",
        f"- Fallback records: {records['fallback']}",
        "",
        "| Feature | Target | Availability | Variation | Feasible Pearson | "
        "Feasible Spearman | Top-1 gap | Pair agreement | Pair coverage | "
        "Oracle match |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, feature in report["features"].items():
        lines.append(
            f"| `{name}` | `{feature['target']}` | "
            f"{_fmt(feature['record_availability_rate'])} | "
            f"{_fmt(feature['feasible_record_variation_rate'])} | "
            f"{_fmt(feature['feasible_candidate_pearson'])} | "
            f"{_fmt(feature['feasible_candidate_spearman'])} | "
            f"{_fmt(feature['feasible_top1_gap_pearson'])} | "
            f"{_fmt(feature['feasible_pairwise_order_agreement_rate'])} | "
            f"{_fmt(feature['feasible_pairwise_comparable_coverage_rate'])} | "
            f"{_fmt(feature['feasible_oracle_match_rate'])} |"
        )
    lines.extend(
        [
            "",
            "Candidate outcomes are used only as offline labels. Rollout "
            "features are fixed current-tick candidate quantities.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def main() -> None:
    args = parse_args()
    paths = list(args.root) + list(args.selection_log)
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(paths)
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
