#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SELECTOR_EXHAUSTED_STATUSES = {
    "support_quality": "no_leak_guarded_candidate_support_insufficient",
    "descriptor_screen": "descriptor_only_offline_screen_rejected",
    "materiality_gap": "postprocess_or_tracker_descriptor_gap_present",
    "postprocess_tracker": "postprocess_tracker_descriptor_signal_insufficient",
}
POSTPROCESS_DESCRIPTOR_SEPARATION_GATE = 0.75
MIN_POSTPROCESS_PRESERVED_RATE = 0.10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only synthesis of DP+CAMP candidate-support, descriptor-screen, "
            "materiality-gap, and postprocess/tracker diagnostics. It consumes "
            "existing JSON artifacts only and does not run DP or change selectors."
        )
    )
    parser.add_argument("--support_quality_json", type=Path, required=True)
    parser.add_argument("--descriptor_screen_json", type=Path, required=True)
    parser.add_argument("--materiality_gap_json", type=Path, required=True)
    parser.add_argument("--postprocess_tracker_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        support_quality=_load_json(args.support_quality_json),
        descriptor_screen=_load_json(args.descriptor_screen_json),
        materiality_gap=_load_json(args.materiality_gap_json),
        postprocess_tracker=_load_json(args.postprocess_tracker_json),
        label=args.label,
        paths={
            "support_quality_json": str(args.support_quality_json),
            "descriptor_screen_json": str(args.descriptor_screen_json),
            "materiality_gap_json": str(args.materiality_gap_json),
            "postprocess_tracker_json": str(args.postprocess_tracker_json),
        },
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


def build_report(
    *,
    support_quality: dict[str, Any],
    descriptor_screen: dict[str, Any],
    materiality_gap: dict[str, Any],
    postprocess_tracker: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    inputs = {
        "support_quality": _artifact_summary(support_quality),
        "descriptor_screen": _artifact_summary(descriptor_screen),
        "materiality_gap": _artifact_summary(materiality_gap),
        "postprocess_tracker": _artifact_summary(postprocess_tracker),
    }
    metrics = _bottleneck_metrics(
        support_quality=support_quality,
        materiality_gap=materiality_gap,
        postprocess_tracker=postprocess_tracker,
    )
    decision = _decision(inputs, metrics)
    return {
        "analysis": {
            "name": "dp_camp_support_bottleneck_synthesis_v1",
            "label": label,
            "role": (
                "read-only synthesis of fixed-DP candidate support, no-leak "
                "selector screens, materiality gap, and postprocess/tracker "
                "descriptor audits"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "this report consumes existing offline JSON diagnostics; any "
                "posterior outcomes remain labels in those source reports only"
            ),
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. This "
                "synthesis does not introduce selector inputs, new atoms, DP "
                "trajectory-coordinate optimization, or a DP-side Benders "
                "subproblem. It is not classical Benders decomposition. Any "
                "future CAMP atom must remain a current-tick fixed "
                "finite-candidate quantity, preferably nonnegative or split "
                "into nonnegative signed parts, so the score stays affine "
                "a_k^T w and the simplex/CVaR/L2 master remains convex."
            ),
            "gates": {
                "postprocess_descriptor_separation_gate": (
                    POSTPROCESS_DESCRIPTOR_SEPARATION_GATE
                ),
                "min_postprocess_preserved_rate": MIN_POSTPROCESS_PRESERVED_RATE,
            },
        },
        "inputs": inputs,
        "metrics": metrics,
        "final_decision": decision,
    }


def _artifact_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    return {
        "analysis_name": _get(report, "analysis", "name"),
        "status": decision.get("status"),
        "reasons": decision.get("reasons") or [],
        "records": report.get("records") or {},
        "online_selector_authorized": bool(decision.get("online_selector_authorized")),
        "closed_loop_smoke_authorized": bool(
            decision.get("closed_loop_smoke_authorized")
        ),
        "full36_authorized": bool(decision.get("full36_authorized")),
        "formal_seeds_authorized": bool(decision.get("formal_seeds_authorized")),
        "camp_retraining_authorized": bool(decision.get("camp_retraining_authorized")),
    }


def _bottleneck_metrics(
    *,
    support_quality: dict[str, Any],
    materiality_gap: dict[str, Any],
    postprocess_tracker: dict[str, Any],
) -> dict[str, Any]:
    support_diag = support_quality.get("support_diagnosis") or {}
    dense_support = support_diag.get("dense_lane_change") or {}
    materiality_records = materiality_gap.get("records") or {}
    materiality_rates = materiality_gap.get("rates") or {}
    post_records = postprocess_tracker.get("records") or {}
    post_decision = postprocess_tracker.get("final_decision") or {}
    top_descriptor = post_decision.get("top_descriptor") or {}
    raw_gain = _number(post_records.get("raw_gain_donor_rows"))
    preserved = _number(post_records.get("preserved_rows"))
    preserved_rate = None
    if raw_gain and raw_gain > 0:
        preserved_rate = preserved / raw_gain
    return {
        "dense_outcome_support_improvement_rate": _number(
            dense_support.get("oracle_outcome_nonregressing_improvement_rate")
        ),
        "dense_strict_guarded_improvement_rate": _number(
            dense_support.get("strict_guarded_improvement_rate")
        ),
        "materiality_oracle_donor_rate": _ratio(
            materiality_records.get("with_oracle_donor"),
            materiality_records.get("nonfallback"),
        ),
        "materiality_raw_jerk_improvement_rate": _number(
            materiality_rates.get("raw_jerk_proxy_improvement_rate")
        ),
        "materiality_tracker_jerk_improvement_rate": _number(
            materiality_rates.get("tracker_jerk_proxy_improvement_rate")
        ),
        "materiality_rollout_h3_jerk_improvement_rate": _number(
            materiality_rates.get("rollout_h3_jerk_improvement_rate")
        ),
        "postprocess_raw_gain_donor_rows": raw_gain,
        "postprocess_preserved_rows": preserved,
        "postprocess_flipped_rows": _number(post_records.get("flipped_rows")),
        "postprocess_preserved_rate": preserved_rate,
        "postprocess_top_descriptor_key": top_descriptor.get("key"),
        "postprocess_top_descriptor_std_abs_diff": _number(
            top_descriptor.get("standardized_abs_difference")
        ),
    }


def _decision(inputs: dict[str, dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    failures = []
    for name, expected in SELECTOR_EXHAUSTED_STATUSES.items():
        observed = inputs[name]["status"]
        if observed != expected:
            failures.append(
                {
                    "artifact": name,
                    "expected_status": expected,
                    "observed_status": observed,
                }
            )
    unauthorized = [
        name
        for name, item in inputs.items()
        if item["online_selector_authorized"]
        or item["closed_loop_smoke_authorized"]
        or item["full36_authorized"]
        or item["formal_seeds_authorized"]
        or item["camp_retraining_authorized"]
    ]
    top_sep = metrics["postprocess_top_descriptor_std_abs_diff"]
    preserved_rate = metrics["postprocess_preserved_rate"]
    low_preservation = (
        preserved_rate is not None and preserved_rate < MIN_POSTPROCESS_PRESERVED_RATE
    )
    weak_descriptor = (
        top_sep is not None and top_sep < POSTPROCESS_DESCRIPTOR_SEPARATION_GATE
    )
    if unauthorized:
        status = "source_artifact_authorization_conflict"
        reasons = ["source_artifact_authorizes_blocked_action"]
        next_step = (
            "Resolve source artifact inconsistency before continuing; do not "
            "promote selector or replay."
        )
    elif failures:
        status = "support_bottleneck_synthesis_inconclusive"
        reasons = ["required_source_statuses_not_all_observed"]
        next_step = (
            "Run or inspect the missing/rejected source diagnostics before "
            "claiming the current selector-calibration route is exhausted."
        )
    elif low_preservation and weak_descriptor:
        status = "current_fixed_dp_selector_calibration_exhausted"
        reasons = [
            "posterior_support_exists_but_no_leak_guarded_support_insufficient",
            "descriptor_only_screen_rejected",
            "raw_signal_not_preserved_by_tracker_or_postprocess",
            "postprocess_tracker_descriptor_signal_insufficient",
        ]
        next_step = (
            "Reject more threshold tuning over the current descriptor family. "
            "The next admissible work is a materially new no-leak atom/schema "
            "definition or candidate-generation/postprocess support design; "
            "online replay, Full36, formal seeds, and CAMP retraining remain "
            "blocked."
        )
    else:
        status = "support_bottleneck_synthesis_requires_review"
        reasons = ["source_statuses_match_but_gate_metrics_do_not_support_rejection"]
        next_step = (
            "Manually inspect the source artifacts; do not promote a selector "
            "without a separate no-leak offline proof."
        )
    return {
        "status": status,
        "reasons": reasons,
        "status_failures": failures,
        "unauthorized_sources": unauthorized,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    metrics = report["metrics"]
    lines = [
        "# DP CAMP Support Bottleneck Synthesis",
        "",
        "This is a read-only synthesis over existing JSON diagnostics. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Online selector authorized: `{decision['online_selector_authorized']}`",
        f"- Closed-loop smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "Reasons:",
    ]
    for reason in decision["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            "## Source Statuses",
            "",
            "| Source | Status | Records |",
            "| --- | --- | ---: |",
        ]
    )
    for name, item in report["inputs"].items():
        records = item.get("records") or {}
        count = records.get("total_records", records.get("total", "n/a"))
        lines.append(f"| `{name}` | `{item['status']}` | `{count}` |")
    lines.extend(
        [
            "",
            "## Gate Metrics",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key in (
        "dense_outcome_support_improvement_rate",
        "dense_strict_guarded_improvement_rate",
        "materiality_oracle_donor_rate",
        "materiality_raw_jerk_improvement_rate",
        "materiality_tracker_jerk_improvement_rate",
        "materiality_rollout_h3_jerk_improvement_rate",
        "postprocess_raw_gain_donor_rows",
        "postprocess_preserved_rows",
        "postprocess_flipped_rows",
        "postprocess_preserved_rate",
        "postprocess_top_descriptor_std_abs_diff",
    ):
        lines.append(f"| `{key}` | {_fmt(metrics.get(key))} |")
    lines.append(
        f"| `postprocess_top_descriptor_key` | `{metrics.get('postprocess_top_descriptor_key')}` |"
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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _get(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _ratio(numerator: Any, denominator: Any) -> float | None:
    numerator_value = _number(numerator)
    denominator_value = _number(denominator)
    if numerator_value is None or denominator_value is None or denominator_value == 0:
        return None
    return numerator_value / denominator_value


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    numeric = _number(value)
    if numeric is None:
        return str(value)
    if abs(numeric) >= 1000 or numeric.is_integer():
        return f"{numeric:.0f}"
    return f"{numeric:.6f}"


if __name__ == "__main__":
    main()
