#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
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
from scripts.integrations.analyze_diffusion_planner_constrained_affine_upper_bound import (  # noqa: E402
    REJECT_STATUS as AFFINE_REJECT_STATUS,
    _merged_candidate_rows,
    _risk_oriented_rows,
    _rows_with_affine_score,
)
from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (  # noqa: E402
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PROGRESS_LOSS_BUDGET_M,
    _class_counts,
    _load_json,
    _path_seeds,
)


READY_STATUS = "affine_allowed_harmful_residual_diagnosed"
SOURCE_BLOCKED_STATUS = "affine_allowed_harmful_residual_source_not_ready"
FORMAL_SEED_STATUS = "affine_allowed_harmful_residual_formal_seed_conflict"

AFFINE_FAILURE_GAP = "allowed_harmful_rate_too_high"
NEXT_WORK = "reject_observable_route_or_design_new_logging_preflight"

COMFORT_JERK_DELTA_MPS3 = 1.0
COMFORT_LATERAL_DELTA_MPS2 = 0.5

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only residual diagnostic for harmful candidates allowed by "
            "the best constrained affine DP-CAMP oracle screen."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--constrained_affine_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_value_gain", type=float, default=MIN_VALUE_GAIN)
    parser.add_argument("--min_value_loss", type=float, default=MIN_VALUE_LOSS)
    parser.add_argument("--progress_loss_budget_m", type=float, default=PROGRESS_LOSS_BUDGET_M)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
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
        constrained_affine_report=_load_json(args.constrained_affine_json),
        label=args.label,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    constrained_affine_report: dict[str, Any],
    label: str | None = None,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    items = []
    for log_path in log_paths:
        rows = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw in enumerate(rows):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            items.append(
                {
                    "raw": raw,
                    "context": {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "path_seeds": sorted(_path_seeds(log_path)),
                    },
                }
            )
    return analyze_records(
        items,
        constrained_affine_report=constrained_affine_report,
        label=label,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    constrained_affine_report: dict[str, Any],
    label: str | None = None,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    source = _source_gate(constrained_affine_report)
    selected_screen = _best_screen(constrained_affine_report)
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    for index, item in enumerate(items):
        record_rows, formal_seed = _merged_candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            min_value_gain=min_value_gain,
            min_value_loss=min_value_loss,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        rows.extend(record_rows)
        formal_seed_records += int(formal_seed)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden for this residual gate.")

    alternative_rows = [row for row in rows if int(row["candidate_index"]) != 0]
    risk_rows, descriptors, normalization = _risk_oriented_rows(alternative_rows)
    scored_rows = _apply_selected_screen(risk_rows, selected_screen)
    allowed_flags = [
        _screen_allows(row, selected_screen)
        for row in scored_rows
    ]
    residual = _residual_summary(scored_rows, allowed_flags)
    decision = _decision(source, selected_screen, formal_seed_records)
    return {
        "analysis": {
            "name": "dp_camp_affine_allowed_harmful_residual_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_residual_diagnosis": True,
            "comfort_delta_thresholds": {
                "mean_jerk_delta_mps3": COMFORT_JERK_DELTA_MPS3,
                "mean_lateral_acceleration_delta_mps2": COMFORT_LATERAL_DELTA_MPS2,
            },
            "math_boundary": (
                "The selected affine screen is reconstructed from fixed "
                "current-tick no-leak descriptors and nonnegative simplex "
                "coefficients produced by the prior oracle. Outcome labels are "
                "used only after the fixed screen to explain harmful residuals. "
                "This diagnostic creates no runtime threshold, no trained CAMP "
                "weights, and no DP-side classical Benders master/subproblem, "
                "dual, or cut."
            ),
        },
        "source_constrained_affine_gate": source,
        "selected_screen": selected_screen,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": _class_counts(alternative_rows),
        },
        "descriptor_count": len(descriptors),
        "normalization_kept_count": sum(
            int(value.get("kept")) for value in normalization.values()
        ),
        "screen_application": _screen_application(scored_rows, allowed_flags),
        "residual_allowed_harmful": residual,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    failure = report.get("failure_gap") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    failure_gap = failure.get("primary_gap") if isinstance(failure, dict) else None
    ready = (
        decision.get("status") == AFFINE_REJECT_STATUS
        and not bool(decision.get("passed"))
        and failure_gap == AFFINE_FAILURE_GAP
    )
    return {
        "passed": ready,
        "status": decision.get("status"),
        "decision_primary_gap": decision.get("primary_gap"),
        "failure_gap": failure_gap,
        "authorized_next_work": decision.get("authorized_next_work"),
    }


def _best_screen(report: dict[str, Any]) -> dict[str, Any] | None:
    failure = report.get("failure_gap") if isinstance(report, dict) else None
    if isinstance(failure, dict) and isinstance(failure.get("best_screen"), dict):
        return failure["best_screen"]
    ranked = report.get("ranked_screens") if isinstance(report, dict) else None
    if isinstance(ranked, list) and ranked and isinstance(ranked[0], dict):
        return ranked[0]
    return None


def _apply_selected_screen(
    rows: list[dict[str, Any]],
    screen: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(screen, dict):
        return rows
    feature_names = [str(name) for name in screen.get("feature_names") or []]
    if len(feature_names) != 1:
        return rows
    score_name = feature_names[0]
    if all(score_name in row["features"] for row in rows):
        return rows
    weights = screen.get("nonnegative_simplex_weights")
    if not isinstance(weights, dict) or not weights:
        return rows
    names = tuple(str(name) for name in weights)
    coeffs = tuple(float(weights[name]) for name in names)
    return _rows_with_affine_score(rows, score_name, names, coeffs)


def _screen_allows(row: dict[str, Any], screen: dict[str, Any] | None) -> bool:
    if not isinstance(screen, dict):
        return False
    features = screen.get("feature_names") or ()
    directions = screen.get("directions") or ()
    thresholds = screen.get("thresholds") or ()
    if not (len(features) == len(directions) == len(thresholds)):
        return False
    for feature, direction, threshold in zip(features, directions, thresholds, strict=True):
        value = row["features"].get(str(feature))
        if value is None or not math.isfinite(float(value)):
            return False
        value = float(value)
        threshold = float(threshold)
        if direction == "allow_low" and value > threshold + 1e-12:
            return False
        if direction == "allow_high" and value < threshold - 1e-12:
            return False
    return True


def _screen_application(
    rows: list[dict[str, Any]],
    allowed_flags: list[bool],
) -> dict[str, Any]:
    allowed = [row for row, is_allowed in zip(rows, allowed_flags, strict=True) if is_allowed]
    blocked = [row for row, is_allowed in zip(rows, allowed_flags, strict=True) if not is_allowed]
    return {
        "allowed_candidates": len(allowed),
        "blocked_candidates": len(blocked),
        "allowed_harmful": sum(int(row["class"] == CLASS_HARMFUL) for row in allowed),
        "allowed_beneficial": sum(int(row["class"] == CLASS_BENEFICIAL) for row in allowed),
        "allowed_neutral": sum(int(row["class"] == CLASS_NEUTRAL) for row in allowed),
        "blocked_harmful": sum(int(row["class"] == CLASS_HARMFUL) for row in blocked),
        "blocked_beneficial": sum(int(row["class"] == CLASS_BENEFICIAL) for row in blocked),
        "blocked_neutral": sum(int(row["class"] == CLASS_NEUTRAL) for row in blocked),
    }


def _residual_summary(
    rows: list[dict[str, Any]],
    allowed_flags: list[bool],
) -> dict[str, Any]:
    allowed_harmful = [
        row for row, is_allowed in zip(rows, allowed_flags, strict=True)
        if is_allowed and row["class"] == CLASS_HARMFUL
    ]
    primary_counts = _reason_counts(_primary_reason(row) for row in allowed_harmful)
    label_counts = _multi_label_counts(allowed_harmful)
    examples = [_example(row) for row in allowed_harmful[:8]]
    return {
        "count": len(allowed_harmful),
        "primary_reason_counts": primary_counts,
        "multi_label_counts": label_counts,
        "dominant_primary_reason": next(iter(primary_counts), None),
        "examples": examples,
        "candidate_state_family_hint": _state_family_hint(primary_counts, label_counts),
    }


def _primary_reason(row: dict[str, Any]) -> str:
    if row.get("collision_worse_than_top1") or row.get("near_miss_worse_than_top1"):
        return "collision_or_near_miss"
    if row.get("lane_worse_than_top1"):
        return "lane_violation"
    if row.get("red_light_worse_than_top1"):
        return "red_light_violation"
    if row["progress_delta_vs_top1_m"] < -PROGRESS_LOSS_BUDGET_M:
        return "progress_loss"
    jerk_delta = row.get("mean_jerk_delta_vs_top1_mps3")
    lateral_delta = row.get("mean_lateral_acceleration_delta_vs_top1_mps2")
    if (
        jerk_delta is not None
        and jerk_delta > COMFORT_JERK_DELTA_MPS3
        or lateral_delta is not None
        and lateral_delta > COMFORT_LATERAL_DELTA_MPS2
    ):
        return "comfort_regression"
    if row["outcome_value_delta_vs_top1"] <= -MIN_VALUE_LOSS:
        return "value_loss"
    if row["hard_violation_delta_vs_top1"] > 0:
        return "other_hard_violation"
    return "unclassified_harmful"


def _multi_label_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "collision_or_near_miss": 0,
        "lane_violation": 0,
        "red_light_violation": 0,
        "progress_loss": 0,
        "comfort_regression": 0,
        "value_loss": 0,
        "hard_violation": 0,
    }
    for row in rows:
        counts["collision_or_near_miss"] += int(
            bool(row.get("collision_worse_than_top1"))
            or bool(row.get("near_miss_worse_than_top1"))
        )
        counts["lane_violation"] += int(bool(row.get("lane_worse_than_top1")))
        counts["red_light_violation"] += int(bool(row.get("red_light_worse_than_top1")))
        counts["progress_loss"] += int(
            row["progress_delta_vs_top1_m"] < -PROGRESS_LOSS_BUDGET_M
        )
        jerk_delta = row.get("mean_jerk_delta_vs_top1_mps3")
        lateral_delta = row.get("mean_lateral_acceleration_delta_vs_top1_mps2")
        counts["comfort_regression"] += int(
            (
                jerk_delta is not None
                and jerk_delta > COMFORT_JERK_DELTA_MPS3
            )
            or (
                lateral_delta is not None
                and lateral_delta > COMFORT_LATERAL_DELTA_MPS2
            )
        )
        counts["value_loss"] += int(row["outcome_value_delta_vs_top1"] <= -MIN_VALUE_LOSS)
        counts["hard_violation"] += int(row["hard_violation_delta_vs_top1"] > 0)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _reason_counts(reasons: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for reason in reasons:
        counts[str(reason)] = counts.get(str(reason), 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _state_family_hint(
    primary_counts: dict[str, int],
    label_counts: dict[str, int],
) -> str:
    dominant = next(iter(primary_counts), None)
    if dominant in {"collision_or_near_miss", "lane_violation"}:
        return "investigate current-tick lane/actor occupancy support before new replay"
    if dominant == "red_light_violation":
        return "investigate traffic-light stopline phase/distance support before new replay"
    if dominant == "progress_loss":
        return "investigate no-leak progress-support state or reject observable route"
    if label_counts.get("comfort_regression", 0) > max(0, label_counts.get("progress_loss", 0)):
        return "investigate current-tick comfort envelope support before new replay"
    return "reject current observable route unless a defensible no-leak state family is identified"


def _decision(
    source: dict[str, Any],
    selected_screen: dict[str, Any] | None,
    formal_seed_records: int,
) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_work = None
        primary_gap = "constrained_affine_gate_not_ready"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        next_work = None
        primary_gap = "formal_seed_conflict"
    elif not isinstance(selected_screen, dict):
        status = SOURCE_BLOCKED_STATUS
        next_work = None
        primary_gap = "missing_selected_affine_screen"
    else:
        status = READY_STATUS
        next_work = NEXT_WORK
        primary_gap = "allowed_harmful_residual_classified"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _example(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "log_path": row["context"].get("log_path"),
        "record_index": row["context"].get("record_index"),
        "candidate_index": row["candidate_index"],
        "primary_reason": _primary_reason(row),
        "outcome_value_delta_vs_top1": row["outcome_value_delta_vs_top1"],
        "progress_delta_vs_top1_m": row["progress_delta_vs_top1_m"],
        "hard_violation_delta_vs_top1": row["hard_violation_delta_vs_top1"],
        "mean_jerk_delta_vs_top1_mps3": row.get("mean_jerk_delta_vs_top1_mps3"),
        "mean_lateral_acceleration_delta_vs_top1_mps2": row.get(
            "mean_lateral_acceleration_delta_vs_top1_mps2"
        ),
        "red_light_worse_than_top1": row.get("red_light_worse_than_top1"),
        "lane_worse_than_top1": row.get("lane_worse_than_top1"),
        "collision_worse_than_top1": row.get("collision_worse_than_top1"),
        "near_miss_worse_than_top1": row.get("near_miss_worse_than_top1"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    residual = report["residual_allowed_harmful"]
    lines = [
        "# DP CAMP Affine Allowed Harmful Residual",
        "",
        "This read-only diagnostic explains harmful candidates allowed by a fixed "
        "constrained-affine oracle screen. It does not create a selector, train "
        "CAMP, run DP, or authorize replay.",
        "",
        "## Decision",
        "",
        f"status=`{decision['status']}`",
        f"passed=`{decision['passed']}`",
        f"primary_gap=`{decision['primary_gap']}`",
        f"authorized_next_work=`{decision['authorized_next_work']}`",
        "",
        "## Screen Application",
        "",
        "```json",
        json.dumps(report["screen_application"], indent=2, sort_keys=True),
        "```",
        "",
        "## Allowed Harmful Residual",
        "",
        "```json",
        json.dumps(
            {
                "count": residual["count"],
                "primary_reason_counts": residual["primary_reason_counts"],
                "multi_label_counts": residual["multi_label_counts"],
                "candidate_state_family_hint": residual["candidate_state_family_hint"],
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
