#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_outcome_free_alternative_candidates import (  # noqa: E402
    DEFAULT_SCREENS,
    _current_tick_feature_values,
    _selected_screens,
)
from scripts.integrations.analyze_diffusion_planner_outcome_free_bounded_selector import (  # noqa: E402
    BOOL_OUTCOMES,
    TOL,
    _admissible_mask,
    _choose,
    _load_record,
    _outcome_number,
    _result_row,
)


JERK_FEATURES = (
    "raw_jerk",
    "tracker_command_jerk_mps3",
    "prefix_jerk_proxy",
    "rollout_h3_mean_vector_jerk_mps3",
)


@dataclass(frozen=True)
class CalibrationThresholds:
    auc_min: float = 0.65
    jerk_precision_lift_min: float = 0.15
    jerk_recall_min: float = 0.30
    joint_precision_lift_min: float = 0.05
    joint_recall_min: float = 0.10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calibrate current-tick jerk descriptors against posterior labels "
            "inside the bounded admissible finite candidate set. Outcomes are "
            "used only as offline labels."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--screen", action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--auc_min", type=float, default=0.65)
    parser.add_argument("--jerk_precision_lift_min", type=float, default=0.15)
    parser.add_argument("--jerk_recall_min", type=float, default=0.30)
    parser.add_argument("--joint_precision_lift_min", type=float, default=0.05)
    parser.add_argument("--joint_recall_min", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = CalibrationThresholds(
        auc_min=args.auc_min,
        jerk_precision_lift_min=args.jerk_precision_lift_min,
        jerk_recall_min=args.jerk_recall_min,
        joint_precision_lift_min=args.joint_precision_lift_min,
        joint_recall_min=args.joint_recall_min,
    )
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        screen_names=tuple(args.screen) or DEFAULT_SCREENS,
        thresholds=thresholds,
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
    screen_names: tuple[str, ...] = DEFAULT_SCREENS,
    thresholds: CalibrationThresholds = CalibrationThresholds(),
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    screens = _selected_screens(screen_names)
    rows_by_screen = {screen["name"]: [] for screen in screens}
    totals = {"logs": len(log_paths), "total": 0, "nonfallback": 0, "fallback": 0}

    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw_record in enumerate(payload):
            totals["total"] += 1
            record = _load_record(raw_record, f"{log_path} record {record_index}")
            fallback = not record["feasible"].any()
            totals["fallback"] += int(fallback)
            totals["nonfallback"] += int(not fallback)
            if fallback:
                continue
            features = _feature_values(
                raw_record,
                record,
                f"{log_path} record {record_index}",
            )
            for screen in screens:
                admissible = _admissible_mask(record, screen)
                if not admissible.any():
                    continue
                chosen = _choose(record, admissible)
                result = _result_row(record, chosen, opportunity=True, fallback=False)
                failure_tick = bool(
                    result["changed"]
                    and not result["posterior_joint_comfort_improvement"]
                )
                for candidate in np.flatnonzero(admissible):
                    rows_by_screen[screen["name"]].append(
                        _candidate_row(
                            record,
                            features,
                            int(candidate),
                            failure_tick=failure_tick,
                        )
                    )

    return {
        "analysis": {
            "name": "dp_camp_jerk_descriptor_calibration_v1",
            "role": (
                "offline calibration of current-tick jerk descriptors against "
                "posterior labels inside bounded admissible candidate sets"
            ),
            "label": label,
            "screens": [screen["name"] for screen in screens],
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "posterior outcomes are labels only; deployable rules must use "
                "current-tick finite candidate quantities"
            ),
            "convexity_boundary": (
                "All descriptors are fixed finite-candidate constants. If any "
                "descriptor is later atomized, fixed-set CAMP scoring remains "
                "affine in w and compatible with the simplex/CVaR/L2 convex "
                "master. This calibration is not Benders and makes no "
                "trajectory-coordinate convexity claim."
            ),
            "features": list(JERK_FEATURES),
        },
        "thresholds": thresholds.__dict__,
        "records": totals,
        "screens": [
            _screen_report(name, rows, thresholds)
            for name, rows in rows_by_screen.items()
        ],
    }


def _feature_values(
    raw_record: dict[str, Any],
    record: dict[str, Any],
    label: str,
) -> dict[str, np.ndarray]:
    features = {"raw_jerk": np.asarray(record["raw_jerk"], dtype=np.float64)}
    features.update(
        _current_tick_feature_values(
            raw_record,
            int(raw_record["num_candidates"]),
            label,
        )
    )
    return features


def _candidate_row(
    record: dict[str, Any],
    features: dict[str, np.ndarray],
    candidate: int,
    *,
    failure_tick: bool,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    jerk_delta = (
        _outcome_number(record, candidate, "mean_jerk_mps3")
        - _outcome_number(record, selected, "mean_jerk_mps3")
    )
    lateral_delta = (
        _outcome_number(record, candidate, "mean_lateral_acceleration_mps2")
        - _outcome_number(record, selected, "mean_lateral_acceleration_mps2")
    )
    return {
        "failure_tick": bool(failure_tick),
        "posterior_jerk_improvement": bool(jerk_delta < -TOL),
        "posterior_lateral_improvement": bool(lateral_delta < -TOL),
        "posterior_safety_nonworse": _posterior_safety_nonworse(record, candidate),
        "posterior_joint_comfort_success": bool(
            jerk_delta < -TOL
            and lateral_delta < -TOL
            and _posterior_safety_nonworse(record, candidate)
        ),
        "feature_deltas": {
            feature: float(values[candidate] - values[selected])
            for feature, values in features.items()
            if feature in JERK_FEATURES
        },
    }


def _posterior_safety_nonworse(record: dict[str, Any], candidate: int) -> bool:
    selected = int(record["selected_index"])
    return all(
        float(bool(record["outcomes"][candidate].get(field)))
        <= float(bool(record["outcomes"][selected].get(field)))
        for field in BOOL_OUTCOMES
    )


def _screen_report(
    name: str,
    rows: list[dict[str, Any]],
    thresholds: CalibrationThresholds,
) -> dict[str, Any]:
    failure_rows = [row for row in rows if row["failure_tick"]]
    groups = {
        "all_admissible": rows,
        "failure_tick_admissible": failure_rows,
    }
    group_reports = {
        group: _group_report(group_rows, thresholds)
        for group, group_rows in groups.items()
    }
    return {
        "name": name,
        "records": {
            "candidate_rows": len(rows),
            "failure_tick_candidate_rows": len(failure_rows),
        },
        "groups": group_reports,
        "calibration_gate_pass": bool(
            group_reports["failure_tick_admissible"]["calibration_gate_pass"]
        ),
        "next_step": (
            "consider_outcome_free_threshold_design"
            if group_reports["failure_tick_admissible"]["calibration_gate_pass"]
            else "reject_current_jerk_descriptors_for_online_guard"
        ),
    }


def _group_report(
    rows: list[dict[str, Any]],
    thresholds: CalibrationThresholds,
) -> dict[str, Any]:
    features = {
        feature: _feature_report(rows, feature)
        for feature in JERK_FEATURES
        if any(feature in row["feature_deltas"] for row in rows)
    }
    passing = [
        feature
        for feature, report in features.items()
        if _feature_passes(report, thresholds)
    ]
    best_feature = _best_feature(features)
    return {
        "records": {
            "candidate_rows": len(rows),
            "posterior_jerk_improvements": sum(
                int(row["posterior_jerk_improvement"]) for row in rows
            ),
            "posterior_joint_comfort_successes": sum(
                int(row["posterior_joint_comfort_success"]) for row in rows
            ),
            "posterior_jerk_improvement_rate": _label_rate(
                rows,
                "posterior_jerk_improvement",
            ),
            "posterior_joint_comfort_success_rate": _label_rate(
                rows,
                "posterior_joint_comfort_success",
            ),
        },
        "features": features,
        "best_feature": best_feature,
        "passing_features": passing,
        "calibration_gate_pass": bool(passing),
    }


def _feature_report(rows: list[dict[str, Any]], feature: str) -> dict[str, Any]:
    clean = [row for row in rows if feature in row["feature_deltas"]]
    deltas = [float(row["feature_deltas"][feature]) for row in clean]
    jerk_labels = [bool(row["posterior_jerk_improvement"]) for row in clean]
    joint_labels = [bool(row["posterior_joint_comfort_success"]) for row in clean]
    scores = [-delta for delta in deltas]
    return {
        "candidate_rows": len(clean),
        "delta_summary": {
            "all": _summary(deltas),
            "posterior_jerk_success": _summary(
                [delta for delta, label in zip(deltas, jerk_labels) if label]
            ),
            "posterior_jerk_failure": _summary(
                [delta for delta, label in zip(deltas, jerk_labels) if not label]
            ),
        },
        "auc": {
            "posterior_jerk_improvement": _auc(jerk_labels, scores),
            "posterior_joint_comfort_success": _auc(joint_labels, scores),
        },
        "nonworse_rule": _rule_report(clean, feature, threshold=0.0, strict=False),
        "strict_improvement_rule": _rule_report(
            clean,
            feature,
            threshold=-TOL,
            strict=True,
        ),
    }


def _rule_report(
    rows: list[dict[str, Any]],
    feature: str,
    *,
    threshold: float,
    strict: bool,
) -> dict[str, Any]:
    if strict:
        predicted = [
            row for row in rows if float(row["feature_deltas"][feature]) < threshold
        ]
    else:
        predicted = [
            row for row in rows if float(row["feature_deltas"][feature]) <= threshold
        ]
    return {
        "threshold_delta": threshold,
        "predicted": len(predicted),
        "coverage": len(predicted) / max(len(rows), 1),
        "posterior_jerk_improvement": _classification_metrics(
            rows,
            predicted,
            "posterior_jerk_improvement",
        ),
        "posterior_joint_comfort_success": _classification_metrics(
            rows,
            predicted,
            "posterior_joint_comfort_success",
        ),
    }


def _classification_metrics(
    rows: list[dict[str, Any]],
    predicted: list[dict[str, Any]],
    label: str,
) -> dict[str, float | int | None]:
    positives = sum(int(row[label]) for row in rows)
    true_positives = sum(int(row[label]) for row in predicted)
    base_rate = positives / max(len(rows), 1)
    precision = None if not predicted else true_positives / len(predicted)
    recall = None if positives == 0 else true_positives / positives
    return {
        "positives": positives,
        "true_positives": true_positives,
        "base_rate": base_rate,
        "precision": precision,
        "precision_lift": None if precision is None else precision - base_rate,
        "recall": recall,
    }


def _feature_passes(
    report: dict[str, Any],
    thresholds: CalibrationThresholds,
) -> bool:
    nonworse = report["nonworse_rule"]
    jerk = nonworse["posterior_jerk_improvement"]
    joint = nonworse["posterior_joint_comfort_success"]
    auc = report["auc"]["posterior_jerk_improvement"]
    return bool(
        auc is not None
        and auc >= thresholds.auc_min
        and _at_least(jerk["precision_lift"], thresholds.jerk_precision_lift_min)
        and _at_least(jerk["recall"], thresholds.jerk_recall_min)
        and _at_least(joint["precision_lift"], thresholds.joint_precision_lift_min)
        and _at_least(joint["recall"], thresholds.joint_recall_min)
    )


def _best_feature(features: dict[str, dict[str, Any]]) -> str | None:
    if not features:
        return None

    def key(item: tuple[str, dict[str, Any]]) -> tuple[float, float, float, str]:
        name, report = item
        auc = report["auc"]["posterior_jerk_improvement"]
        jerk_lift = report["nonworse_rule"]["posterior_jerk_improvement"][
            "precision_lift"
        ]
        joint_lift = report["nonworse_rule"]["posterior_joint_comfort_success"][
            "precision_lift"
        ]
        return (
            -1.0 if auc is None else float(auc),
            -1.0 if jerk_lift is None else float(jerk_lift),
            -1.0 if joint_lift is None else float(joint_lift),
            name,
        )

    return max(features.items(), key=key)[0]


def _label_rate(rows: list[dict[str, Any]], label: str) -> float:
    return sum(int(row[label]) for row in rows) / max(len(rows), 1)


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "p50": None, "p90": None, "p95": None}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
        "p95": float(np.percentile(arr, 95.0)),
    }


def _auc(labels: list[bool], scores: list[float]) -> float | None:
    if len(labels) != len(scores):
        raise ValueError("labels and scores must have the same length.")
    positives = sum(int(label) for label in labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    order = np.argsort(np.asarray(scores, dtype=np.float64), kind="mergesort")
    sorted_scores = np.asarray(scores, dtype=np.float64)[order]
    ranks = np.empty(len(scores), dtype=np.float64)
    start = 0
    while start < len(scores):
        end = start + 1
        while end < len(scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average_rank
        start = end
    positive_rank_sum = float(
        np.sum(ranks[np.asarray(labels, dtype=bool)])
    )
    return (
        positive_rank_sum - positives * (positives + 1) / 2.0
    ) / (positives * negatives)


def _at_least(value: float | int | None, threshold: float) -> bool:
    return value is not None and float(value) >= threshold


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    thresholds = report["thresholds"]
    lines = [
        "# DP CAMP Jerk Descriptor Calibration",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        "",
        "This report calibrates current-tick jerk descriptors against posterior "
        "labels inside the bounded admissible finite candidate set. It is an "
        "offline diagnostic only.",
        "",
        "Gate thresholds: "
        f"AUC >= `{thresholds['auc_min']}`, jerk precision lift >= "
        f"`{thresholds['jerk_precision_lift_min']}`, jerk recall >= "
        f"`{thresholds['jerk_recall_min']}`, joint precision lift >= "
        f"`{thresholds['joint_precision_lift_min']}`, joint recall >= "
        f"`{thresholds['joint_recall_min']}`.",
        "",
    ]
    for screen in report["screens"]:
        lines.extend(
            [
                f"## `{screen['name']}`",
                "",
                f"- Candidate rows: {screen['records']['candidate_rows']}",
                f"- Failure-tick candidate rows: "
                f"{screen['records']['failure_tick_candidate_rows']}",
                f"- Failure-tick calibration gate: "
                f"{_pass_fail(screen['calibration_gate_pass'])}",
                f"- Next step: `{screen['next_step']}`",
                "",
                "### Failure-Tick Admissible Candidates",
                "",
                "| Feature | Rows | Jerk AUC | Joint AUC | Nonworse coverage | "
                "Jerk precision | Jerk lift | Jerk recall | Joint precision | "
                "Joint lift | Joint recall | Gate |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        failure_group = screen["groups"]["failure_tick_admissible"]
        for feature, feature_report in failure_group["features"].items():
            nonworse = feature_report["nonworse_rule"]
            jerk = nonworse["posterior_jerk_improvement"]
            joint = nonworse["posterior_joint_comfort_success"]
            lines.append(
                f"| `{feature}` | {feature_report['candidate_rows']} | "
                f"{_fmt(feature_report['auc']['posterior_jerk_improvement'])} | "
                f"{_fmt(feature_report['auc']['posterior_joint_comfort_success'])} | "
                f"{nonworse['coverage']:.6f} | "
                f"{_fmt(jerk['precision'])} | {_fmt(jerk['precision_lift'])} | "
                f"{_fmt(jerk['recall'])} | {_fmt(joint['precision'])} | "
                f"{_fmt(joint['precision_lift'])} | {_fmt(joint['recall'])} | "
                f"{_pass_fail(_feature_passes(feature_report, CalibrationThresholds(**thresholds)))} |"
            )
        lines.append("")
    lines.extend(
        [
            "Mathematical boundary: descriptors are fixed finite-candidate "
            "constants. This report is not Benders and does not claim "
            "trajectory-coordinate convexity.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | int | None) -> str:
    return "n/a" if value is None else f"{float(value):.6f}"


def _pass_fail(value: bool) -> str:
    return "pass" if value else "fail"


if __name__ == "__main__":
    main()
