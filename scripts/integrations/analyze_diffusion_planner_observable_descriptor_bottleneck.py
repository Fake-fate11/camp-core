#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (  # noqa: E402
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    FEATURE_SPECS,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PROGRESS_LOSS_BUDGET_M,
    _candidate_rows,
    _load_json,
    _path_seeds,
)


READY_STATUS = "observable_descriptor_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = "observable_descriptor_bottleneck_source_not_rejected"
REJECTED_SOURCE_STATUS = "matched_observable_descriptor_separability_rejected"
NEXT_WORK = "diagnose_observable_descriptor_bottleneck_before_new_replay"

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
            "Read-only residual diagnostic for rejected observable descriptor "
            "separability screens. It explains allowed harmful and blocked "
            "beneficial alternatives without changing thresholds."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--separability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
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
        separability_report=_load_json(args.separability_json),
        label=args.label,
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
    separability_report: dict[str, Any],
    label: str | None = None,
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
    return analyze_records(items, separability_report=separability_report, label=label)


def analyze_records(
    items: list[dict[str, Any]],
    *,
    separability_report: dict[str, Any],
    label: str | None = None,
) -> dict[str, Any]:
    source = _source_gate(separability_report)
    best_screen = ((separability_report.get("failure_gap") or {}).get("best_screen"))
    rows = []
    for index, item in enumerate(items):
        record_rows, _ = _candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            FEATURE_SPECS,
            min_value_gain=MIN_VALUE_GAIN,
            min_value_loss=MIN_VALUE_LOSS,
            progress_loss_budget_m=PROGRESS_LOSS_BUDGET_M,
        )
        rows.extend(row for row in record_rows if int(row["candidate_index"]) != 0)
    if not isinstance(best_screen, dict):
        allowed = [False for _ in rows]
    else:
        allowed = [_screen_allows(row, best_screen) for row in rows]
    allowed_harmful = [
        row for row, is_allowed in zip(rows, allowed, strict=True)
        if is_allowed and row["class"] == CLASS_HARMFUL
    ]
    blocked_beneficial = [
        row for row, is_allowed in zip(rows, allowed, strict=True)
        if not is_allowed and row["class"] == CLASS_BENEFICIAL
    ]
    allowed_harmful_reasons = _reason_counts(
        _allowed_harmful_reason(row) for row in allowed_harmful
    )
    blocked_beneficial_reasons = _reason_counts(
        _blocked_beneficial_reason(row, best_screen) for row in blocked_beneficial
    )
    dominant_allowed = _dominant_reason(allowed_harmful_reasons)
    dominant_blocked = _dominant_reason(blocked_beneficial_reasons)
    decision = _decision(source, best_screen)
    return {
        "analysis": {
            "name": "dp_camp_observable_descriptor_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_runtime_features": False,
            "future_outcome_labels_used_for_residual_diagnosis": True,
            "comfort_delta_thresholds": {
                "mean_jerk_delta_mps3": COMFORT_JERK_DELTA_MPS3,
                "mean_lateral_acceleration_delta_mps2": COMFORT_LATERAL_DELTA_MPS2,
            },
            "math_boundary": (
                "This diagnostic does not create selector thresholds or atoms. "
                "It uses outcome labels only after a fixed rejected observable "
                "screen to explain residual errors. Runtime-eligible quantities "
                "remain fixed current-tick finite-candidate descriptors; any "
                "later atomization must preserve affine score_k(w)=a_k^T w and "
                "the simplex/CVaR/L2 convex master."
            ),
        },
        "source_separability_gate": source,
        "best_screen": best_screen,
        "counts": {
            "alternative_rows": len(rows),
            "allowed_harmful": len(allowed_harmful),
            "blocked_beneficial": len(blocked_beneficial),
            "allowed_harmful_reasons": allowed_harmful_reasons,
            "blocked_beneficial_reasons": blocked_beneficial_reasons,
            "dominant_allowed_harmful_reason": dominant_allowed,
            "dominant_blocked_beneficial_reason": dominant_blocked,
        },
        "examples": {
            "allowed_harmful": [_example(row) for row in allowed_harmful[:5]],
            "blocked_beneficial": [_example(row) for row in blocked_beneficial[:5]],
        },
        "next_hypothesis": _next_hypothesis(dominant_allowed, dominant_blocked),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    next_work = decision.get("authorized_next_work")
    ready = status == REJECTED_SOURCE_STATUS and next_work == NEXT_WORK
    return {
        "passed": ready,
        "status": status,
        "authorized_next_work": next_work,
        "primary_gap": decision.get("primary_gap"),
    }


def _screen_allows(row: dict[str, Any], screen: dict[str, Any]) -> bool:
    features = screen.get("feature_names") or ()
    directions = screen.get("directions") or ()
    thresholds = screen.get("thresholds") or ()
    if not (len(features) == len(directions) == len(thresholds)):
        return False
    for feature, direction, threshold in zip(features, directions, thresholds, strict=True):
        value = row["features"].get(str(feature))
        if value is None:
            return False
        value = float(value)
        threshold = float(threshold)
        if direction == "allow_low" and value > threshold + 1e-12:
            return False
        if direction == "allow_high" and value < threshold - 1e-12:
            return False
    return True


def _allowed_harmful_reason(row: dict[str, Any]) -> str:
    if row["progress_delta_vs_top1_m"] < -PROGRESS_LOSS_BUDGET_M:
        return "progress_proxy_weakness"
    if (
        row.get("red_light_worse_than_top1")
        or row.get("lane_worse_than_top1")
        or row.get("collision_worse_than_top1")
        or row.get("near_miss_worse_than_top1")
    ):
        return "traffic_support_interaction"
    jerk_delta = row.get("mean_jerk_delta_vs_top1_mps3")
    lateral_delta = row.get("mean_lateral_acceleration_delta_vs_top1_mps2")
    if (
        jerk_delta is not None
        and jerk_delta > COMFORT_JERK_DELTA_MPS3
        or lateral_delta is not None
        and lateral_delta > COMFORT_LATERAL_DELTA_MPS2
    ):
        return "comfort_envelope_insufficiency"
    if row["outcome_value_delta_vs_top1"] < -MIN_VALUE_LOSS:
        return "top1_shape_calibration"
    return "candidate_set_support_limitation"


def _blocked_beneficial_reason(row: dict[str, Any], screen: Any) -> str:
    if not isinstance(screen, dict):
        return "no_screen_available"
    feature_names = [str(name) for name in (screen.get("feature_names") or [])]
    if any("projection" in name for name in feature_names):
        return "progress_proxy_overconservative"
    if any("heading" in name or "segment" in name for name in feature_names):
        return "top1_shape_calibration_overconservative"
    if any("lateral" in name or "obstacle" in name for name in feature_names):
        return "support_envelope_overconservative"
    if any("red" in name for name in feature_names):
        return "traffic_support_interaction_overconservative"
    return "candidate_set_support_limitation"


def _reason_counts(reasons: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for reason in reasons:
        counts[str(reason)] = counts.get(str(reason), 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _dominant_reason(counts: dict[str, int]) -> str | None:
    return next(iter(counts), None)


def _next_hypothesis(allowed_reason: str | None, blocked_reason: str | None) -> str:
    if allowed_reason == "progress_proxy_weakness":
        return "design a stronger current-tick progress/support proxy before new replay"
    if allowed_reason == "comfort_envelope_insufficiency":
        return "test a current-tick comfort-envelope descriptor family before new replay"
    if allowed_reason == "traffic_support_interaction":
        return "test traffic/support interaction descriptors before new replay"
    if allowed_reason == "top1_shape_calibration" or blocked_reason == "top1_shape_calibration_overconservative":
        return "diagnose Top-1 shape calibration and support-envelope conflict before new replay"
    return "treat current observable payload as insufficient unless a new descriptor family is predeclared"


def _decision(source: dict[str, Any], best_screen: Any) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_work = None
    else:
        status = READY_STATUS
        next_work = "predeclare_next_descriptor_family_or_reject_observable_route"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "authorized_next_work": next_work,
        "best_screen_available": isinstance(best_screen, dict),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _example(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "log_path": row["context"].get("log_path"),
        "record_index": row["context"].get("record_index"),
        "candidate_index": row["candidate_index"],
        "class": row["class"],
        "outcome_value_delta_vs_top1": row["outcome_value_delta_vs_top1"],
        "progress_delta_vs_top1_m": row["progress_delta_vs_top1_m"],
        "hard_violation_delta_vs_top1": row["hard_violation_delta_vs_top1"],
        "mean_jerk_delta_vs_top1_mps3": row.get("mean_jerk_delta_vs_top1_mps3"),
        "mean_lateral_acceleration_delta_vs_top1_mps2": row.get(
            "mean_lateral_acceleration_delta_vs_top1_mps2"
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Observable Descriptor Bottleneck",
        "",
        "This read-only diagnostic explains residual errors from a fixed rejected "
        "observable descriptor screen. It does not tune thresholds or authorize "
        "new replay.",
        "",
        "## Decision",
        "",
        f"status=`{report['final_decision']['status']}`",
        f"passed=`{report['final_decision']['passed']}`",
        f"authorized_next_work=`{report['final_decision']['authorized_next_work']}`",
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(report["counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Next Hypothesis",
        "",
        report["next_hypothesis"],
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
