#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


READY_STATUS = "progress_lane_hard_joint_screen_preflight_ready"
REJECT_STATUS = "progress_lane_hard_joint_screen_preflight_rejected"
SOURCE_BLOCKED_STATUS = "progress_lane_hard_joint_screen_preflight_source_not_ready"

LANE_SOURCE_STATUS = "lane_hard_violation_support_separability_bottleneck_diagnosed"
LANE_SOURCE_NEXT = "reject_lane_hard_standalone_or_design_joint_progress_lane_hard_screen"
PROGRESS_SOURCE_STATUS = "progress_support_separability_bottleneck_diagnosed"
PROGRESS_SOURCE_NEXT = "reject_or_design_new_progress_support_descriptor_family"

AUTHORIZED_NEXT_WORK = "progress_lane_hard_joint_cologged_outcome_plan_only"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "online_optimization_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for a joint progress-support plus "
            "lane/hard-violation support screen. It reads existing bottleneck "
            "artifacts only; it does not run replay, train CAMP, or promote an "
            "online selector."
        )
    )
    parser.add_argument("--progress_bottleneck_json", type=Path, required=True)
    parser.add_argument("--lane_hard_bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        progress_bottleneck_report=_load_json(args.progress_bottleneck_json),
        lane_hard_bottleneck_report=_load_json(args.lane_hard_bottleneck_json),
        label=args.label,
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
    *,
    progress_bottleneck_report: dict[str, Any],
    lane_hard_bottleneck_report: dict[str, Any],
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    progress_source = _source_gate(
        progress_bottleneck_report,
        expected_status=PROGRESS_SOURCE_STATUS,
        expected_next=PROGRESS_SOURCE_NEXT,
    )
    lane_source = _source_gate(
        lane_hard_bottleneck_report,
        expected_status=LANE_SOURCE_STATUS,
        expected_next=LANE_SOURCE_NEXT,
    )
    formal_seed_records = _formal_seed_records(progress_bottleneck_report) + _formal_seed_records(
        lane_hard_bottleneck_report
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    evidence = _complementarity_evidence(
        progress_bottleneck_report,
        lane_hard_bottleneck_report,
    )
    source_ready = progress_source["passed"] and lane_source["passed"]
    if not source_ready:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "source_bottleneck_gate_not_ready"
        next_work = None
    elif not evidence["complementary_blind_spots_established"]:
        status = REJECT_STATUS
        primary_gap = evidence["primary_gap"]
        next_work = None
    else:
        status = READY_STATUS
        primary_gap = "joint_progress_lane_hard_screen_design_preflight_passed"
        next_work = AUTHORIZED_NEXT_WORK

    final = {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_progress_lane_hard_joint_screen_preflight_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_descriptor_definitions": False,
            "future_outcome_labels_used_for_design_evidence": True,
            "predeclared_joint_hypothesis": (
                "A co-logged finite-candidate screen may combine progress-support "
                "risk and lane/hard support risk: progress atoms should reject "
                "posterior progress-loss harmful candidates admitted by "
                "high-retain lane/hard screens, while lane/hard atoms should "
                "cover lane/hard blind spots missed by progress-support atoms."
            ),
            "next_gate_accept_criteria": {
                "requires_same_record_cologged_progress_and_lane_hard_payloads": True,
                "harmful_block_rate": ">= 0.75",
                "beneficial_retain_rate": ">= 0.75",
                "allowed_harmful_rate": "<= 0.10",
                "formal_seed_records": 0,
                "selector_effect": False,
            },
            "math_boundary": (
                "Progress-support and lane/hard support descriptors must be "
                "fixed current-tick finite-candidate quantities available "
                "before outcome evaluation. Concatenating nonnegative atom "
                "vectors preserves affine score_k(w)=a_k^T w for CAMP weights "
                "and keeps the simplex/CVaR/L2 master convex. A finite "
                "candidate intersection or lexicographic screen is not claimed "
                "to be classical Benders; no DP-side master/subproblem, dual, "
                "or valid cut is constructed."
            ),
        },
        "source_gates": {
            "progress_support": progress_source,
            "lane_hard_support": lane_source,
        },
        "formal_seed_records": formal_seed_records,
        "complementarity_evidence": evidence,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _source_gate(
    report: dict[str, Any],
    *,
    expected_status: str,
    expected_next: str,
) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    next_work = decision.get("authorized_next_work")
    passed = (
        bool(decision.get("passed"))
        and status == expected_status
        and next_work == expected_next
        and not bool(decision.get("camp_retraining_authorized"))
        and not bool(decision.get("online_selector_authorized"))
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": next_work,
    }


def _formal_seed_records(report: dict[str, Any]) -> int:
    for key in ("source_records", "records"):
        records = report.get(key)
        if isinstance(records, dict) and records.get("formal_seed_records") is not None:
            return int(records.get("formal_seed_records") or 0)
    if report.get("formal_seed_records") is not None:
        return int(report.get("formal_seed_records") or 0)
    return 0


def _complementarity_evidence(
    progress_report: dict[str, Any],
    lane_report: dict[str, Any],
) -> dict[str, Any]:
    progress_allowed = progress_report.get("allowed_harmful") or {}
    progress_blocked = progress_report.get("blocked_beneficial") or {}
    progress_allowed_outcome = progress_allowed.get("outcome_summary") or {}
    lane_apps = lane_report.get("screen_applications") or {}
    lane_high = lane_apps.get("best_high_retain_screen") or {}
    lane_strict = lane_apps.get("best_strict_safe_screen") or {}
    lane_high_counts = lane_high.get("counts") or {}
    lane_strict_counts = lane_strict.get("counts") or {}
    lane_high_allowed = lane_high.get("allowed_harmful") or {}
    lane_high_reasons = lane_high_allowed.get("reason_counts") or {}
    progress_gap_count = int(lane_high_reasons.get("progress_loss") or 0)
    value_loss_count = int(lane_high_reasons.get("outcome_value_loss") or 0)
    lane_or_hard_progress_blind_spot = (
        int(progress_allowed_outcome.get("lane_worse_count") or 0) > 0
        or float(progress_allowed_outcome.get("hard_violation_delta_mean") or 0.0) > 0.0
    )
    lane_high_admits_progress_harmful = (
        int(lane_high_counts.get("harmful_allowed") or 0) > 0
        and (progress_gap_count > 0 or value_loss_count > 0)
    )
    lane_strict_overblocks = int(lane_strict_counts.get("beneficial_blocked") or 0) > int(
        lane_strict_counts.get("beneficial_retained") or 0
    )
    progress_has_tradeoff = (
        int(progress_allowed.get("count") or 0) > 0
        and int(progress_blocked.get("count") or 0) > 0
    )
    if not progress_has_tradeoff:
        primary_gap = "progress_support_tradeoff_not_established"
    elif not lane_or_hard_progress_blind_spot:
        primary_gap = "progress_support_lane_hard_blind_spot_not_established"
    elif not lane_high_admits_progress_harmful:
        primary_gap = "lane_hard_high_retain_progress_harmful_gap_not_established"
    elif not lane_strict_overblocks:
        primary_gap = "lane_hard_strict_overblocking_not_established"
    else:
        primary_gap = "complementary_blind_spots_established"
    return {
        "primary_gap": primary_gap,
        "complementary_blind_spots_established": (
            primary_gap == "complementary_blind_spots_established"
        ),
        "progress_support_allowed_harmful_count": int(progress_allowed.get("count") or 0),
        "progress_support_blocked_beneficial_count": int(progress_blocked.get("count") or 0),
        "progress_support_allowed_lane_worse_count": int(
            progress_allowed_outcome.get("lane_worse_count") or 0
        ),
        "progress_support_allowed_hard_violation_delta_mean": float(
            progress_allowed_outcome.get("hard_violation_delta_mean") or 0.0
        ),
        "lane_hard_high_retain_harmful_allowed": int(
            lane_high_counts.get("harmful_allowed") or 0
        ),
        "lane_hard_high_retain_progress_loss_harmful": progress_gap_count,
        "lane_hard_high_retain_value_loss_harmful": value_loss_count,
        "lane_hard_strict_beneficial_blocked": int(
            lane_strict_counts.get("beneficial_blocked") or 0
        ),
        "lane_hard_strict_beneficial_retained": int(
            lane_strict_counts.get("beneficial_retained") or 0
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Progress + Lane/Hard Joint Screen Preflight",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Complementarity Evidence",
        "",
        "```json",
        json.dumps(report["complementarity_evidence"], indent=2, sort_keys=True),
        "```",
        "",
        "## Next Gate Accept Criteria",
        "",
        "```json",
        json.dumps(report["analysis"]["next_gate_accept_criteria"], indent=2, sort_keys=True),
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
