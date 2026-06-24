#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

_ATTRIBUTION_MODULE = (
    "scripts.integrations.analyze_diffusion_planner_residual_comfort_"
    "remediation_followup_materially_different_generator_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution"
)
_attribution = importlib.import_module(_ATTRIBUTION_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_static_contract_review_only"
)

DEFAULT_ATTRIBUTION_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
ATTRIBUTION_JSON = "failure_attribution.json"
ATTRIBUTION_MD = "failure_attribution.md"

EXPECTED_DP_HEAD = _attribution.EXPECTED_DP_HEAD
FAILURE_ATTRIBUTION_READY_STATUS = _attribution.READY_STATUS
FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK = _attribution.AUTHORIZED_NEXT_WORK
PRIMARY_BLOCKER_FAMILY = "hard_support_below_threshold_plus_zero_comfort_support"
RESIDUAL_FAMILY = "hard_support_below_threshold_plus_zero_comfort_support"
FORMAL_SEEDS = (11, 12, 13)

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
            "Plan-only remediation design after the material generator guarded "
            "fixed-snapshot screen rerun failure attribution."
        )
    )
    parser.add_argument(
        "--failure_attribution_root",
        type=Path,
        default=Path(DEFAULT_ATTRIBUTION_ROOT),
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
    plan = _remediation_design_plan(source)
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
                "design_plan_v1"
            ),
            "label": label,
            "role": "plan-only remediation design for hard-plus-comfort failure",
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
                "This plan consumes only the completed failure-attribution "
                "artifact and audit authorization. It does not edit "
                "implementation code, create candidates, rerun the screen, "
                "run DP, run replay, use formal seeds, define or promote "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T "
                "w, mutate the convex simplex/CVaR/L2 master, train CAMP, "
                "change online selection, modify DP weights or code, or "
                "claim a DP-side classical Benders decomposition. Any later "
                "descriptor or atom proposal must prove current-tick "
                "availability, finite candidate locality, nonnegative or "
                "legal hinge/signed-split form, and affine contribution to "
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
        "# Material Generator Failure Remediation Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        (
            "- Static contract review authorized: "
            f"`{decision['static_contract_review_authorized']}`"
        ),
        f"- Primary blocker: `{source['primary_blocker_family']}`",
        f"- Descriptor coverage: `{source['descriptor_coverage_rate']}`",
        f"- Hard support gap: `{source['hard_support_gap']}`",
        f"- Comfort support gap: `{source['comfort_support_gap']}`",
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


def _remediation_design_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": (
            "material_generator_guarded_fixed_snapshot_screen_rerun_failure_"
            "attribution_remediation_design_plan_only"
        ),
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "target_failure": {
            "residual_family": RESIDUAL_FAMILY,
            "primary_blocker_family": source["primary_blocker_family"],
            "candidate_rows": source["candidate_row_count"],
            "descriptor_rows": source["descriptor_row_count"],
            "descriptor_coverage_rate": source["descriptor_coverage_rate"],
            "candidate_coverage_rate": source["candidate_coverage_rate"],
            "hard_support_gap": source["hard_support_gap"],
            "comfort_support_gap": source["comfort_support_gap"],
            "hard_blockers": source["hard_blockers"],
            "comfort_blockers": source["comfort_blockers"],
        },
        "design_position": (
            "The next admissible move is a static-contract-reviewed "
            "remediation design for the existing materially different "
            "generator. The previous screen already produced 306 descriptor "
            "covered candidates, so the failure is not missing descriptor "
            "payload. It is a dual support failure: hard support remains below "
            "threshold and comfort support is zero. The plan therefore targets "
            "current-tick lane/red/kinematic/road-border feasibility before "
            "comfort shaping, then jerk, lateral, rollout, smoothness, and "
            "progress blockers. It must keep candidate0, default behavior, DP "
            "weights/code/config/invocation, online selector behavior, deployed "
            "atom schema, and score_k(w)=a_k^T w unchanged."
        ),
        "remediation_tracks": [
            {
                "name": "lane_red_hard_feasibility_precheck",
                "purpose": (
                    "Screen planned support points in lane-station space before "
                    "candidate append so the generator avoids known lane "
                    "crossing, road-border, red-light, and DP kinematic "
                    "failure regions without editing DP output."
                ),
                "evidence_driver": "dp_lane_crossing dp_road_border dp_red_light dp_kinematic",
                "contract": (
                    "current-tick route and signal geometry only; deterministic "
                    "bounded append; no hard-gate relaxation"
                ),
            },
            {
                "name": "jerk_limited_stop_and_creep_profiles",
                "purpose": (
                    "Generate stop or creep profiles with bounded acceleration "
                    "and jerk from the current speed, stop distance, and red "
                    "state so hard/progress survivors have a chance to pass "
                    "command and rollout jerk filters."
                ),
                "evidence_driver": (
                    "route_topology_comfort_blocked_command_jerk "
                    "route_topology_comfort_blocked_rollout_jerk"
                ),
                "contract": (
                    "profile parameters must be finite, static, default-off, "
                    "and reviewed before implementation; no replay labels"
                ),
            },
            {
                "name": "lateral_heading_continuity_projection",
                "purpose": (
                    "Project support candidates onto the current route corridor "
                    "with bounded lateral displacement, heading continuity, and "
                    "road-border margin before comfort evaluation."
                ),
                "evidence_driver": (
                    "route_topology_comfort_blocked_command_lateral "
                    "route_topology_comfort_blocked_rollout_lateral"
                ),
                "contract": (
                    "candidate-local rollout features only; no selector, "
                    "score, fallback, or deployed atom schema mutation"
                ),
            },
            {
                "name": "progress_retention_without_gate_relaxation",
                "purpose": (
                    "Keep enough forward station progress in stop/creep "
                    "profiles to reduce progress-loss blockers while preserving "
                    "the existing progress gate as evidence."
                ),
                "evidence_driver": "route_topology_comfort_blocked_progress_loss",
                "contract": (
                    "the generator must earn progress support under existing "
                    "checks; comfort and progress thresholds are not widened"
                ),
            },
            {
                "name": "positive_support_before_training_gate",
                "purpose": (
                    "Require a later nonformal fixed-snapshot screen to show "
                    "positive, reproducible, no-leakage support before replay "
                    "or CAMP training can be discussed."
                ),
                "evidence_driver": "positive_support_evidence=False training_ready=False",
                "contract": (
                    "this design gate authorizes only static contract review; "
                    "it does not authorize implementation, screen rerun, replay, "
                    "or training"
                ),
            },
        ],
        "descriptor_atom_contract": [
            {
                "name": "hard_feasibility_margin_hinges",
                "contract": (
                    "nonnegative hinges for lane, road-border, red-timing, and "
                    "kinematic margins; current tick only"
                ),
            },
            {
                "name": "command_jerk_hinge",
                "contract": (
                    "nonnegative max(0, command_jerk_delta - budget), "
                    "candidate-local and finite"
                ),
            },
            {
                "name": "rollout_jerk_hinge",
                "contract": (
                    "nonnegative max(0, rollout_jerk_delta - budget), no "
                    "future outcome labels"
                ),
            },
            {
                "name": "lateral_error_signed_split",
                "contract": (
                    "signed lateral or heading errors must be encoded as legal "
                    "nonnegative signed-split channels"
                ),
            },
            {
                "name": "progress_loss_hinge",
                "contract": (
                    "nonnegative progress-loss hinge over candidate-local "
                    "current route station; affine if later included in a_k"
                ),
            },
        ],
        "static_review_requirements": [
            "prove each proposed input is available at the current tick",
            "prove no future outcome, replay label, formal seed, or Full36 leakage",
            "prove finite candidate count and deterministic candidate ordering",
            "prove candidate0 and default behavior preservation",
            "prove DP weights, DP code, DP config, and DP invocation remain fixed",
            "prove existing hard, progress, and comfort gates are not relaxed",
            "prove no candidate score, selected index, fallback, online selector, or deployed atom schema mutation in this design gate",
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
                "name": "rerun_same_generator",
                "reason": "the completed fixed-snapshot rerun is already negative",
            },
            {
                "name": "comfort_budget_relaxation",
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
    json_path = root / ATTRIBUTION_JSON
    md_path = root / ATTRIBUTION_MD
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
        "descriptor_coverage_rate": _float(
            attribution.get("descriptor_coverage_rate")
        ),
        "candidate_coverage_rate": _float(attribution.get("candidate_coverage_rate")),
        "hard_support_gap": _float(attribution.get("hard_support_gap")),
        "comfort_support_gap": _float(attribution.get("comfort_support_gap")),
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


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_mentions_completed_failure_attribution", FAILURE_ATTRIBUTION_READY_STATUS in audit_text),
        _check("audit_authorizes_this_design_plan", FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_negative_support", "not training-ready evidence" in audit_text),
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
        _check("failure_attribution_candidate_coverage_positive", source["candidate_coverage_rate"] > 0.0),
        _check("failure_attribution_hard_gap_positive", source["hard_support_gap"] > 0.0),
        _check("failure_attribution_comfort_gap_positive", source["comfort_support_gap"] > 0.0),
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
            == "material_generator_guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_design_plan_only",
        ),
        _check("plan_selects_static_review", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_targets_residual_family", plan["target_failure"]["residual_family"] == RESIDUAL_FAMILY),
        _check("plan_has_hard_precheck", "lane_red_hard_feasibility_precheck" in tracks),
        _check("plan_has_jerk_profiles", "jerk_limited_stop_and_creep_profiles" in tracks),
        _check("plan_has_lateral_projection", "lateral_heading_continuity_projection" in tracks),
        _check("plan_has_progress_retention", "progress_retention_without_gate_relaxation" in tracks),
        _check("plan_has_positive_support_gate", "positive_support_before_training_gate" in tracks),
        _check("plan_has_hard_margin_descriptors", "hard_feasibility_margin_hinges" in descriptors),
        _check("plan_has_command_jerk_descriptor", "command_jerk_hinge" in descriptors),
        _check("plan_has_rollout_jerk_descriptor", "rollout_jerk_hinge" in descriptors),
        _check("plan_has_lateral_signed_split", "lateral_error_signed_split" in descriptors),
        _check("plan_has_progress_descriptor", "progress_loss_hinge" in descriptors),
        _check("plan_rejects_negative_training", "train_on_negative_support" in rejected),
        _check("plan_rejects_same_rerun", "rerun_same_generator" in rejected),
        _check("plan_rejects_comfort_relaxation", "comfort_budget_relaxation" in rejected),
        _check("plan_rejects_promotion", "selector_or_atom_promotion" in rejected),
        _check("plan_rejects_formal_seed_probe", "formal_seed_probe" in rejected),
        _check("plan_rejects_dp_change", "dp_side_change" in rejected),
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_finite_candidate", "finite candidate" in text),
        _check("plan_mentions_candidate_local", "candidate-local" in text),
        _check("plan_mentions_no_gate_relaxation", "not widened" in text or "not relaxed" in text),
        _check("plan_mentions_no_mutation", "selected index" in text and "online selector" in text),
        _check("plan_mentions_nonnegative_or_hinge", "nonnegative" in text and "hinge/signed-split" in text),
        _check("plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_formal_seed_freeze", "formal seeds 11/12/13" in text),
        _check("plan_mentions_dp_fixed", "dp weights" in text and "dp code" in text),
        _check("plan_mentions_camp_over_dp_blocked", "camp-over-dp-top-1" in text),
        _check("plan_mentions_benders_blocked", "classical benders" in text),
        _check("plan_formal_seed_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_static_review", decision["static_contract_review_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_production_edit", decision["production_implementation_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_full36", decision["full36_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_blocks_safety_claim", decision["safety_benefit_claim_authorized"] is False),
        _check("boundary_blocks_camp_over_dp", decision["camp_over_dp_top1_claim_authorized"] is False),
        _check("boundary_blocks_benders", decision["classic_benders_claim_authorized"] is False),
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
        "remediation_design_static_contract_review_authorized": passed,
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
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"payload", "markdown_text"}
    }


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
