#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_failure_attribution import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as FAILURE_ATTRIBUTION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
    FORMAL_SEEDS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_design_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_design_static_contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_FAILURE_ATTRIBUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "failure_attribution_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

FAILURE_JSON = "failure_attribution.json"
FAILURE_MD = "failure_attribution.md"

PRIMARY_BLOCKER_FAMILY = "comfort_support_zero_after_hard_support_pass"
RESIDUAL_FAILURE_FAMILY = "jerk_dominated_comfort_gap_after_hard_progress_survival"
TOP_COMFORT_BLOCKER = "route_topology_comfort_blocked_command_jerk"
REQUIRED_AUDIT_AUTHORIZATION = FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK

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
            "Plan-only remediation design after residual comfort diagnostic "
            "failure attribution. This gate does not edit implementation "
            "code, generate candidates, rerun screens, run replay, train "
            "CAMP, or modify DP."
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
    label: Optional[str] = None,
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
                "remediation_design_plan_v1"
            ),
            "label": label,
            "role": "plan-only remediation design for residual comfort failure",
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
                "implementation code, create candidates, rerun the screen, run "
                "DP, run replay, use formal seeds, define runtime atoms, choose "
                "lambda online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "modify DP weights or code, or claim a DP-side classical "
                "Benders decomposition. Any later atom proposal must prove "
                "nonnegativity or use a legal hinge/signed-split form while "
                "remaining affine over the fixed finite candidate set."
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
        "# Residual Comfort Failure Remediation Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary blocker: `{source['primary_blocker_family']}`",
        f"- Residual family: `{source['residual_failure_family']}`",
        f"- Top comfort blocker: `{source['top_comfort_blocker']}`",
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
    lines.extend(["## Static Review Requirements", ""])
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


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / FAILURE_JSON
    markdown_path = root / FAILURE_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": payload_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "json_sha256": _sha256(payload_path),
        "markdown_sha256": _sha256(markdown_path),
        "payload": _read_json(payload_path),
        "markdown_text": _read_text(markdown_path),
    }


def _failure_attribution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    attribution = _dict(payload.get("read_only_attribution"))
    ranking = _list(attribution.get("comfort_blocker_ranking"))
    top = attribution.get("top_comfort_blocker")
    if not top and ranking and isinstance(ranking[0], dict):
        top = ranking[0].get("name")
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "remediation_design_plan_authorized": bool(
            decision.get("remediation_design_plan_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "residual_failure_family": attribution.get("residual_failure_family"),
        "top_comfort_blocker": top,
        "hard_progress_survivor_rows": _int(
            attribution.get("hard_progress_survivor_rows")
        ),
        "comfort_admissible_rows": _int(attribution.get("comfort_admissible_rows")),
        "comfort_blocker_ranking": ranking,
        "remediation_design_needed": bool(
            attribution.get("remediation_design_needed")
        ),
        "replay_evidence_ready": bool(attribution.get("replay_evidence_ready")),
        "training_ready": bool(attribution.get("training_ready")),
    }


def _remediation_design_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "residual_comfort_failure_diagnostic_remediation_design_plan_only",
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "target_failure": {
            "primary_blocker_family": source["primary_blocker_family"],
            "residual_failure_family": source["residual_failure_family"],
            "top_comfort_blocker": source["top_comfort_blocker"],
            "hard_progress_survivor_rows": source["hard_progress_survivor_rows"],
            "comfort_admissible_rows": source["comfort_admissible_rows"],
        },
        "design_position": (
            "Do not train CAMP and do not rerun the fixed-snapshot screen. "
            "The evidence says hard/progress survivors exist, but none are "
            "comfort-admissible, with command jerk as the dominant residual "
            "comfort blocker. The next admissible work is a static review of "
            "a default-off remediation design that keeps DP fixed, consumes "
            "only current-tick finite candidate features, and treats any "
            "future support intervention as separate from promotion, replay, "
            "or training."
        ),
        "remediation_tracks": [
            {
                "name": "hard_progress_survivor_comfort_gap_partition",
                "purpose": (
                    "Partition the already observed hard/progress survivors "
                    "by comfort blocker, command-jerk magnitude, red-route "
                    "state, and progress margin before any future support "
                    "intervention is considered."
                ),
                "evidence_driver": (
                    f"{source['hard_progress_survivor_rows']} hard/progress "
                    "survivor rows and zero comfort-admissible rows"
                ),
                "contract": (
                    "read-only current-tick finite candidate features; no "
                    "mutation of candidates, scores, selected index, fallback, "
                    "online selector, or deployed atom schema"
                ),
            },
            {
                "name": "command_jerk_hinge_descriptor_family",
                "purpose": (
                    "Specify a future descriptor family for command-jerk "
                    "comfort gaps that is legal for affine CAMP scoring if a "
                    "later atom gate is separately authorized."
                ),
                "evidence_driver": TOP_COMFORT_BLOCKER,
                "contract": (
                    "descriptors must be nonnegative or legal hinge/signed-"
                    "split terms and must preserve score_k(w)=a_k^T w"
                ),
            },
            {
                "name": "jerk_bounded_support_intervention_boundary",
                "purpose": (
                    "Define the static contract a later default-off support "
                    "intervention would need to satisfy before any execution "
                    "gate could be proposed."
                ),
                "evidence_driver": RESIDUAL_FAILURE_FAMILY,
                "contract": (
                    "plan-only boundary: no candidate construction, no screen "
                    "rerun, no replay, no formal seeds, no DP import, and no "
                    "training authorization in this gate"
                ),
            },
            {
                "name": "positive_support_before_training_gate",
                "purpose": (
                    "Make positive fixed-snapshot support a prerequisite for "
                    "any training plan, because selector learning cannot prove "
                    "benefit when the candidate set has zero comfort support."
                ),
                "evidence_driver": "training_ready=False and replay_evidence_ready=False",
                "contract": (
                    "training, Full36, atom promotion, online selector changes, "
                    "and safety or CAMP-over-DP claims remain blocked"
                ),
            },
            {
                "name": "dp_fixed_black_box_boundary",
                "purpose": (
                    "Keep Diffusion Planner as the pinned black-box trajectory "
                    "source and isolate all future CAMP-side evidence from DP "
                    "code, weights, configs, and invocation."
                ),
                "evidence_driver": EXPECTED_DP_HEAD,
                "contract": (
                    "no DP modification, tuning, import-side reward recompute, "
                    "tracker recompute, or DP-side classical Benders claim"
                ),
            },
        ],
        "static_review_requirements": [
            "prove this design is default-off and plan-only",
            "prove all features are finite, current-tick, and candidate-local",
            "prove diagnostic payloads cannot alter candidates, scores, selected index, fallback, online selector, or deployed atom schema",
            "prove any future command-jerk descriptor is nonnegative or legal hinge/signed-split",
            "prove score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master remain unchanged",
            "prove candidate generation, fixed-snapshot screen rerun, replay, Full36, and formal seeds remain unauthorized",
            "prove CAMP retraining and training execution remain unauthorized until positive support and training contracts exist",
            "prove DP code, weights, configs, and invocation remain fixed at the pinned commit",
            "prove no safety-benefit, CAMP-over-DP-Top-1, or classical Benders claim is introduced",
        ],
        "rejected_non_fixes": [
            {
                "name": "train_on_zero_comfort_support",
                "reason": (
                    "zero comfort-admissible hard/progress survivors cannot "
                    "justify a training execution gate"
                ),
            },
            {
                "name": "rerun_until_positive",
                "reason": (
                    "execution without a reviewed design would not explain the "
                    "jerk-dominated blocker"
                ),
            },
            {
                "name": "relax_jerk_or_comfort_contracts",
                "reason": (
                    "the blocker must drive a legal current-tick descriptor or "
                    "support contract, not a weaker acceptance contract"
                ),
            },
            {
                "name": "online_selector_workaround",
                "reason": (
                    "online lambda selection cannot create missing comfort "
                    "support and is not authorized"
                ),
            },
            {
                "name": "dp_side_fix",
                "reason": (
                    "DP remains a fixed black-box generator at the pinned "
                    "commit and is out of scope"
                ),
            },
        ],
        "acceptance_criteria": [
            "failure attribution is complete and authorizes only this design-plan gate",
            "CAMP HEAD equals origin/main and DP HEAD equals the fixed Tier4 commit",
            "the plan explains the command-jerk residual comfort blocker after hard/progress survival",
            "the plan rejects training, replay, rerun-until-positive, selector workarounds, and DP-side fixes",
            "the next gate is static contract review only and cannot edit implementation code",
        ],
        "blocked_boundaries": [
            "implementation edits are not authorized in this gate",
            "production implementation edits are not authorized",
            "candidate generation execution is not authorized",
            "fixed-snapshot candidate generation and screen rerun are not authorized",
            "replay and closed-loop smoke are not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "atom promotion, CAMP retraining, and online selector changes are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_root_exists", artifact["exists"]),
        _check("failure_attribution_json_exists", artifact["json_exists"]),
        _check("failure_attribution_markdown_exists", artifact["markdown_exists"]),
        _check("failure_attribution_json_parseable", bool(artifact["payload"])),
        _check(
            "failure_attribution_markdown_records_title",
            "Residual Comfort Diagnostic Failure Attribution"
            in artifact["markdown_text"],
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
        _check("audit_present", bool(audit_text)),
        _check(
            "audit_records_failure_attribution_complete",
            FAILURE_ATTRIBUTION_READY_STATUS in audit_text,
        ),
        _check(
            "audit_authorizes_remediation_design",
            REQUIRED_AUDIT_AUTHORIZATION in audit_text,
        ),
        _check(
            "audit_records_residual_family",
            f"residual_failure_family={RESIDUAL_FAILURE_FAMILY}" in audit_text,
        ),
        _check(
            "audit_records_top_comfort_blocker",
            f"top_comfort_blocker={TOP_COMFORT_BLOCKER}" in audit_text,
        ),
        _check(
            "audit_blocks_candidate_generation",
            "candidate_generation_execution_authorized=False" in audit_text,
        ),
        _check(
            "audit_blocks_screen_rerun",
            "fixed_snapshot_screen_rerun_authorized=False" in audit_text,
        ),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_status_complete", source["status"] == FAILURE_ATTRIBUTION_READY_STATUS),
        _check("failure_attribution_passed", source["passed"] is True),
        _check("failure_attribution_failed_checks_empty", not source["failed_checks"]),
        _check(
            "failure_attribution_authorizes_this_plan",
            source["authorized_next_work"] == FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
        ),
        _check(
            "failure_attribution_design_plan_authorized",
            source["remediation_design_plan_authorized"] is True,
        ),
        _check("failure_attribution_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("failure_attribution_primary_blocker", source["primary_blocker_family"] == PRIMARY_BLOCKER_FAMILY),
        _check("failure_attribution_residual_family", source["residual_failure_family"] == RESIDUAL_FAILURE_FAMILY),
        _check("failure_attribution_top_comfort_blocker", source["top_comfort_blocker"] == TOP_COMFORT_BLOCKER),
        _check("failure_attribution_survivors_positive", source["hard_progress_survivor_rows"] > 0),
        _check("failure_attribution_comfort_zero", source["comfort_admissible_rows"] == 0),
        _check("failure_attribution_ranked_blockers_present", bool(source["comfort_blocker_ranking"])),
        _check("failure_attribution_remediation_needed", source["remediation_design_needed"] is True),
        _check("failure_attribution_replay_not_ready", source["replay_evidence_ready"] is False),
        _check("failure_attribution_training_not_ready", source["training_ready"] is False),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    tracks = {item["name"] for item in plan["remediation_tracks"]}
    rejected = {item["name"] for item in plan["rejected_non_fixes"]}
    return [
        _check("plan_selection_type", plan["selection_type"] == "residual_comfort_failure_diagnostic_remediation_design_plan_only"),
        _check("plan_selects_static_review", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_target_residual_family", plan["target_failure"]["residual_failure_family"] == RESIDUAL_FAILURE_FAMILY),
        _check("plan_target_top_blocker", plan["target_failure"]["top_comfort_blocker"] == TOP_COMFORT_BLOCKER),
        _check("plan_has_gap_partition", "hard_progress_survivor_comfort_gap_partition" in tracks),
        _check("plan_has_jerk_descriptor", "command_jerk_hinge_descriptor_family" in tracks),
        _check("plan_has_support_boundary", "jerk_bounded_support_intervention_boundary" in tracks),
        _check("plan_has_positive_support_gate", "positive_support_before_training_gate" in tracks),
        _check("plan_has_dp_boundary", "dp_fixed_black_box_boundary" in tracks),
        _check("plan_rejects_training", "train_on_zero_comfort_support" in rejected),
        _check("plan_rejects_rerun_until_positive", "rerun_until_positive" in rejected),
        _check("plan_rejects_relaxation", "relax_jerk_or_comfort_contracts" in rejected),
        _check("plan_rejects_selector_workaround", "online_selector_workaround" in rejected),
        _check("plan_rejects_dp_fix", "dp_side_fix" in rejected),
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_finite_candidate_features", "finite candidate features" in text),
        _check("plan_mentions_no_candidate_mutation", "no mutation of candidates" in text),
        _check("plan_mentions_nonnegative_or_hinge", "nonnegative" in text and "hinge/signed-split" in text),
        _check("plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_formal_seed_freeze", "formal seeds 11/12/13" in text),
        _check("plan_mentions_dp_fixed", "dp weights" in text and "dp code" in text),
        _check("plan_formal_seed_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_static_review", decision["static_contract_review_authorized"] is True),
        _check("boundary_authorizes_remediation_static_review", decision["remediation_design_static_contract_review_authorized"] is True),
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
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_design_plan_ready": passed,
        "static_contract_review_authorized": passed,
        "remediation_design_static_contract_review_authorized": passed,
        "implementation_code_edit_authorized": False,
        "production_implementation_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


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


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
