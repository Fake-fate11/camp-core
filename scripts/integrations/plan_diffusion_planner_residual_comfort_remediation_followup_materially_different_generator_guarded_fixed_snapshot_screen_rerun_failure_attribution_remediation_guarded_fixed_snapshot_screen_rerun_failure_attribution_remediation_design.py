#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DEFAULT_FAILURE_ATTRIBUTION_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "guarded_fixed_snapshot_screen_rerun_failure_attribution_bff8f8b"
)
FAILURE_ATTRIBUTION_JSON = "material_generator_remediation_rerun_failure_attribution.json"
FAILURE_ATTRIBUTION_MD = "material_generator_remediation_rerun_failure_attribution.md"

EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = (11, 12, 13)

FAILURE_ATTRIBUTION_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_complete"
)
FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_only"
)

READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_static_contract_review_only"
)

PRIMARY_BLOCKER_FAMILY = "hard_support_below_threshold_plus_zero_comfort_support"
REQUIRED_HARD_BLOCKERS = (
    "dp_lane_crossing",
    "dp_kinematic",
    "dp_road_border",
    "dp_red_light",
)
REQUIRED_COMFORT_BLOCKERS = (
    "route_topology_comfort_blocked_command_lateral",
    "route_topology_comfort_blocked_rollout_jerk",
    "route_topology_comfort_blocked_command_jerk",
    "route_topology_comfort_blocked_progress_loss",
    "route_topology_comfort_blocked_rollout_lateral",
    "route_topology_comfort_blocked_smoothness_loss",
)

BLOCKED_ACTIONS = (
    "implementation_code_edit_authorized",
    "production_implementation_edit_authorized",
    "candidate_generation_execution_authorized",
    "fixed_snapshot_candidate_generation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "atom_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only remediation design after the v2 material-generator "
            "guarded fixed-snapshot rerun failure attribution."
        )
    )
    parser.add_argument(
        "--failure_attribution_root",
        type=Path,
        default=Path(DEFAULT_FAILURE_ATTRIBUTION_ROOT),
    )
    parser.add_argument("--audit_path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--camp_head", required=True)
    parser.add_argument("--camp_origin_main", required=True)
    parser.add_argument("--dp_head", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        failure_attribution_root=args.failure_attribution_root,
        audit_path=args.audit_path,
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        dp_head=args.dp_head,
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


def build_report(
    *,
    failure_attribution_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(failure_attribution_root)
    source = _failure_attribution_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    plan = _design_plan(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_source_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_followup_materially_different_generator_guarded_"
                "fixed_snapshot_screen_rerun_failure_attribution_remediation_"
                "guarded_fixed_snapshot_screen_rerun_failure_attribution_"
                "remediation_design_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only design after v2 hard-support-near-threshold and "
                "zero-comfort-support failure"
            ),
            "plan_only": True,
            "implementation_code_edit": False,
            "production_implementation_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan consumes only the completed v2 failure-attribution "
                "artifact and audit authorization. It does not edit production "
                "implementation, create candidates, rerun the fixed-snapshot "
                "screen, run DP, run replay, use formal seeds, define or "
                "promote runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, modify DP weights or "
                "code, or claim a DP-side classical Benders decomposition. "
                "Any later descriptor or atom proposal must prove current-tick "
                "availability, finite candidate locality, nonnegative or legal "
                "hinge/signed-split form, and affine contribution to "
                "score_k(w)=a_k^T w."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "failure_attribution_artifact": _strip_payload(artifact),
        "failure_attribution_summary": source,
        "remediation_design_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["failure_attribution_summary"]
    plan = report["remediation_design_plan"]
    lines = [
        "# Material Generator V2 Failure Remediation Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        (
            "- Static contract review authorized: "
            f"`{decision['static_contract_review_authorized']}`"
        ),
        f"- Primary blocker: `{source['primary_blocker_family']}`",
        f"- Hard support gap: `{source['hard_support_gap']}`",
        f"- Comfort support gap: `{source['comfort_support_gap']}`",
        f"- V2 hard support near threshold: `{source['v2_hard_support_near_threshold']}`",
        f"- V2 zero comfort support: `{source['v2_zero_comfort_support']}`",
        "",
        "## Design Position",
        "",
        plan["design_position"],
        "",
        "## Remediation Tracks",
        "",
    ]
    for item in plan["remediation_tracks"]:
        lines.append(f"### {item['name']}")
        lines.append("")
        lines.append(item["purpose"])
        lines.append("")
        lines.append(f"- Evidence driver: `{item['evidence_driver']}`")
        lines.append(f"- Contract: `{item['contract']}`")
        lines.append("")
    lines.extend(["## Descriptor And Atom Contract", ""])
    for item in plan["descriptor_atom_contract"]:
        lines.append(f"- `{item['name']}`: {item['contract']}")
    lines.extend(["", "## Static Review Requirements", ""])
    for item in plan["static_review_requirements"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Rejected Non-Fixes", ""])
    for item in plan["rejected_non_fixes"]:
        lines.append(f"- `{item['name']}`: {item['reason']}")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _design_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": (
            "material_generator_v2_guarded_fixed_snapshot_screen_rerun_"
            "failure_attribution_remediation_design_plan_only"
        ),
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "target_failure": {
            "primary_blocker_family": source["primary_blocker_family"],
            "candidate_rows": source["candidate_row_count"],
            "descriptor_rows": source["descriptor_row_count"],
            "descriptor_coverage_rate": source["descriptor_coverage_rate"],
            "hard_support_gap": source["hard_support_gap"],
            "comfort_support_gap": source["comfort_support_gap"],
            "v2_hard_support_near_threshold": source[
                "v2_hard_support_near_threshold"
            ],
            "v2_zero_comfort_support": source["v2_zero_comfort_support"],
            "hard_blockers": source["hard_blockers"],
            "comfort_blockers": source["comfort_blockers"],
        },
        "design_position": (
            "The v2 generator nearly closes the hard-support threshold but "
            "still has zero comfort-admissible support. The next admissible "
            "move is therefore a static-contract-reviewed design for a "
            "comfort-first hard-support closure, not another rerun of the same "
            "v2 policy and not training. The design must keep default behavior, "
            "candidate0, DP rows, DP weights/code/config/invocation, online "
            "selector behavior, deployed atom schema, score_k(w)=a_k^T w, and "
            "the convex simplex/CVaR/L2 master unchanged."
        ),
        "remediation_tracks": [
            {
                "name": "near_threshold_hard_support_closure",
                "purpose": (
                    "Target the remaining hard-support gap with deterministic "
                    "current-tick lane/red/kinematic/road-border margin checks "
                    "that close support without widening the support threshold "
                    "or relaxing existing hard gates."
                ),
                "evidence_driver": "hard_support_gap=0.011904761904761918",
                "contract": (
                    "finite default-off candidate append only; current-tick "
                    "geometry and ego state only; no DP mutation"
                ),
            },
            {
                "name": "comfort_first_profile_precheck",
                "purpose": (
                    "Make comfort feasibility a construction precondition rather "
                    "than an after-the-fact rejection by using bounded command "
                    "jerk, rollout jerk, lateral, smoothness, and progress "
                    "proxy hinges before candidate append."
                ),
                "evidence_driver": "comfort_support_gap=0.25 zero_comfort_support=True",
                "contract": (
                    "reportable deterministic proxies only; no comfort budget "
                    "relaxation and no replay labels"
                ),
            },
            {
                "name": "lane_corridor_continuity_tightening",
                "purpose": (
                    "Reduce lane crossing and road-border failures while also "
                    "reducing lateral comfort blockers by clipping support "
                    "points to a continuous current route corridor with bounded "
                    "heading and lateral displacement."
                ),
                "evidence_driver": (
                    "dp_lane_crossing dp_road_border "
                    "route_topology_comfort_blocked_command_lateral"
                ),
                "contract": (
                    "candidate-local route projection only; preserve DP rows, "
                    "candidate0, ordering, fallback, and selector outputs"
                ),
            },
            {
                "name": "stop_creep_progress_balance",
                "purpose": (
                    "Balance red-stop compliance with progress retention so "
                    "hard survivors do not become progress-loss or jerk-loss "
                    "comfort failures."
                ),
                "evidence_driver": (
                    "route_topology_comfort_blocked_progress_loss "
                    "route_topology_comfort_blocked_command_jerk "
                    "route_topology_comfort_blocked_rollout_jerk"
                ),
                "contract": (
                    "bounded acceleration and jerk profiles from current speed "
                    "and stop distance only; existing progress and comfort gates "
                    "must be earned, not relaxed"
                ),
            },
            {
                "name": "positive_support_before_execution_gate",
                "purpose": (
                    "Require static contract review, implementation-only review, "
                    "and then a later guarded nonformal fixed-snapshot screen "
                    "with positive support before replay or training can be "
                    "discussed."
                ),
                "evidence_driver": "training_ready=False positive_support_evidence=False",
                "contract": (
                    "this design gate authorizes only static contract review; "
                    "it does not authorize implementation, screen rerun, replay, "
                    "or training"
                ),
            },
        ],
        "descriptor_atom_contract": [
            {
                "name": "hard_support_margin_hinges_v3",
                "contract": (
                    "nonnegative hinges for lane, road-border, red-timing, and "
                    "kinematic margins; current tick and finite candidate only"
                ),
            },
            {
                "name": "comfort_proxy_hinge_bundle_v3",
                "contract": (
                    "nonnegative command jerk, rollout jerk, lateral, smoothness, "
                    "and progress-loss hinges computed from candidate-local "
                    "current-tick proxies"
                ),
            },
            {
                "name": "lateral_heading_signed_split_v3",
                "contract": (
                    "signed lateral and heading residuals must be represented as "
                    "legal nonnegative signed-split channels"
                ),
            },
            {
                "name": "support_gap_report_only_channels_v3",
                "contract": (
                    "hard-gap and comfort-gap diagnostics are report-only unless "
                    "a later atom promotion proves affine a_k channels"
                ),
            },
            {
                "name": "affine_convex_master_preservation",
                "contract": (
                    "any future scoring use must remain score_k(w)=a_k^T w and "
                    "must not change simplex/CVaR/L2 convexity"
                ),
            },
        ],
        "static_review_requirements": [
            "prove each proposed input is available at the current tick",
            "prove no future outcome, replay label, formal seed, or Full36 leakage",
            "prove finite candidate count and deterministic candidate ordering",
            "prove candidate0, DP rows, fallback, and default behavior preservation",
            "prove DP weights, DP code, DP config, and DP invocation remain fixed",
            "prove no hard, progress, comfort, or support threshold is relaxed",
            "prove no candidate score, selected index, online selector, or deployed atom schema mutation in this design gate",
            "prove descriptors are nonnegative or legal hinge/signed-split channels",
            "prove any future scoring use preserves score_k(w)=a_k^T w",
            "prove simplex/CVaR/L2 master convexity remains unchanged",
            "prove no safety-benefit, CAMP-over-DP-Top-1, or classical Benders claim is made",
        ],
        "rejected_non_fixes": [
            {
                "name": "train_on_negative_support",
                "reason": "positive_support_evidence=False and training_ready=False",
            },
            {
                "name": "rerun_v2_as_is",
                "reason": "the completed v2 fixed-snapshot rerun already failed support",
            },
            {
                "name": "hard_or_comfort_gate_relaxation",
                "reason": "wider gates would not prove generator separability",
            },
            {
                "name": "selector_or_atom_promotion",
                "reason": "promotion is blocked before positive offline support",
            },
            {
                "name": "formal_seed_probe",
                "reason": "formal seeds 11/12/13 remain frozen and unused",
            },
            {
                "name": "dp_side_change",
                "reason": (
                    "DP must remain a fixed black-box trajectory generator at "
                    f"{EXPECTED_DP_HEAD}"
                ),
            },
        ],
        "blocked_boundaries": [
            "implementation edits are not authorized",
            "production implementation edits are not authorized",
            "candidate generation execution is not authorized",
            "fixed-snapshot screen rerun is not authorized",
            "closed-loop replay is not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "CAMP retraining and training execution are not authorized",
            "online selector promotion and atom promotion are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    json_path = root / FAILURE_ATTRIBUTION_JSON
    md_path = root / FAILURE_ATTRIBUTION_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": json_path.is_file(),
        "markdown_exists": md_path.is_file(),
        "json_sha256": _sha256(json_path),
        "markdown_sha256": _sha256(md_path),
        "payload": _read_json(json_path),
        "markdown_text": _read_text(md_path),
    }


def _failure_attribution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    attribution = _dict(payload.get("read_only_attribution"))
    hard_blockers = [
        str(item.get("name"))
        for item in _list(attribution.get("hard_blocker_ranking"))
        if isinstance(item, dict)
    ]
    comfort_blockers = [
        str(item.get("name"))
        for item in _list(attribution.get("comfort_blocker_ranking"))
        if isinstance(item, dict)
    ]
    blocked_authorizations = [
        key
        for key in BLOCKED_ACTIONS
        if bool(decision.get(key) or _dict(payload.get("blocked_actions")).get(key))
    ]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failed_checks": _list(decision.get("failed_checks")),
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "candidate_row_count": _int(attribution.get("candidate_row_count")),
        "descriptor_row_count": _int(attribution.get("descriptor_row_count")),
        "descriptor_coverage_rate": _float(attribution.get("descriptor_coverage_rate")),
        "hard_support_gap": _float(attribution.get("hard_support_gap")),
        "comfort_support_gap": _float(attribution.get("comfort_support_gap")),
        "v2_hard_support_near_threshold": bool(
            attribution.get("v2_hard_support_near_threshold")
        ),
        "v2_zero_comfort_support": bool(attribution.get("v2_zero_comfort_support")),
        "positive_support_evidence": bool(attribution.get("positive_support_evidence")),
        "training_ready": bool(attribution.get("training_ready")),
        "replay_evidence_ready": bool(attribution.get("replay_evidence_ready")),
        "hard_blockers": hard_blockers,
        "comfort_blockers": comfort_blockers,
        "blocked_authorizations": blocked_authorizations,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_root_exists", bool(artifact["exists"])),
        _check("failure_attribution_json_exists", bool(artifact["json_exists"])),
        _check("failure_attribution_md_exists", bool(artifact["markdown_exists"])),
        _check("failure_attribution_json_parseable", bool(artifact["payload"])),
        _check(
            "failure_attribution_markdown_records_status",
            "Failure Attribution" in artifact["markdown_text"]
            or "failure attribution" in artifact["markdown_text"].lower(),
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check(
            "audit_mentions_completed_failure_attribution",
            FAILURE_ATTRIBUTION_READY_STATUS in audit_text,
        ),
        _check(
            "audit_authorizes_this_design_plan",
            FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK in audit_text,
        ),
        _check("audit_records_zero_comfort_support", "zero comfort" in audit_text),
        _check("audit_keeps_formal_seeds_frozen", "formal seeds 11/12/13" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    hard = set(source["hard_blockers"])
    comfort = set(source["comfort_blockers"])
    return [
        _check("failure_attribution_status_complete", source["status"] == FAILURE_ATTRIBUTION_READY_STATUS),
        _check("failure_attribution_passed", source["passed"] is True),
        _check("failure_attribution_no_failed_checks", not source["failed_checks"]),
        _check("failure_attribution_authorizes_this_plan", source["authorized_next_work"] == FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK),
        _check("failure_attribution_primary_blocker", source["primary_blocker_family"] == PRIMARY_BLOCKER_FAMILY),
        _check("failure_attribution_candidate_rows_present", source["candidate_row_count"] > 0),
        _check("failure_attribution_descriptor_rows_present", source["descriptor_row_count"] > 0),
        _check("failure_attribution_descriptor_coverage_complete", source["descriptor_coverage_rate"] == 1.0),
        _check("failure_attribution_hard_gap_positive", source["hard_support_gap"] > 0.0),
        _check("failure_attribution_hard_gap_near_threshold", source["v2_hard_support_near_threshold"] is True),
        _check("failure_attribution_comfort_gap_positive", source["comfort_support_gap"] > 0.0),
        _check("failure_attribution_zero_comfort_support", source["v2_zero_comfort_support"] is True),
        _check("failure_attribution_no_positive_support", source["positive_support_evidence"] is False),
        _check("failure_attribution_training_not_ready", source["training_ready"] is False),
        _check("failure_attribution_replay_not_ready", source["replay_evidence_ready"] is False),
        _check("failure_attribution_no_blocked_authorizations", not source["blocked_authorizations"]),
        *[_check(f"failure_attribution_has_{name}", name in hard) for name in REQUIRED_HARD_BLOCKERS],
        *[_check(f"failure_attribution_has_{name}", name in comfort) for name in REQUIRED_COMFORT_BLOCKERS],
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    tracks = {item["name"] for item in plan["remediation_tracks"]}
    descriptors = {item["name"] for item in plan["descriptor_atom_contract"]}
    rejected = {item["name"] for item in plan["rejected_non_fixes"]}
    return [
        _check(
            "plan_selection_type",
            plan["selection_type"]
            == "material_generator_v2_guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_design_plan_only",
        ),
        _check("plan_selects_static_review", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_targets_near_threshold", plan["target_failure"]["v2_hard_support_near_threshold"] is True),
        _check("plan_targets_zero_comfort", plan["target_failure"]["v2_zero_comfort_support"] is True),
        _check("plan_has_hard_support_closure", "near_threshold_hard_support_closure" in tracks),
        _check("plan_has_comfort_first_precheck", "comfort_first_profile_precheck" in tracks),
        _check("plan_has_lane_corridor_tightening", "lane_corridor_continuity_tightening" in tracks),
        _check("plan_has_stop_creep_balance", "stop_creep_progress_balance" in tracks),
        _check("plan_has_positive_support_gate", "positive_support_before_execution_gate" in tracks),
        _check("plan_has_hard_margin_descriptors", "hard_support_margin_hinges_v3" in descriptors),
        _check("plan_has_comfort_bundle", "comfort_proxy_hinge_bundle_v3" in descriptors),
        _check("plan_has_lateral_signed_split", "lateral_heading_signed_split_v3" in descriptors),
        _check("plan_has_report_only_channels", "support_gap_report_only_channels_v3" in descriptors),
        _check("plan_has_affine_convex_contract", "affine_convex_master_preservation" in descriptors),
        _check("plan_rejects_negative_training", "train_on_negative_support" in rejected),
        _check("plan_rejects_same_v2_rerun", "rerun_v2_as_is" in rejected),
        _check("plan_rejects_gate_relaxation", "hard_or_comfort_gate_relaxation" in rejected),
        _check("plan_rejects_promotion", "selector_or_atom_promotion" in rejected),
        _check("plan_rejects_formal_seed_probe", "formal_seed_probe" in rejected),
        _check("plan_rejects_dp_change", "dp_side_change" in rejected),
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_finite_candidate", "finite" in text and "candidate" in text),
        _check("plan_mentions_no_gate_relaxation", "not relaxed" in text or "no hard" in text),
        _check("plan_mentions_no_mutation", "selected index" in text and "online selector" in text),
        _check("plan_mentions_affine_score", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_blocks_implementation", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_blocks_claims", decision["safety_benefit_claim_authorized"] is False and decision["camp_over_dp_top1_claim_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_design_plan_ready": passed,
        "static_contract_review_authorized": passed,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "payload"}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
