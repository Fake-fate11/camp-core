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

_REVIEW_MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_"
    "remediation_followup_materially_different_generator_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution_remediation_design_static_contract"
)
_review = importlib.import_module(_REVIEW_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_only"
)

DEFAULT_STATIC_REVIEW_ROOT = (
    "/root/autodl-tmp/"
    "camp_dp_material_generator_failure_attribution_remediation_design_static_contract_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
STATIC_REVIEW_JSON = "static_contract_review.json"
STATIC_REVIEW_MD = "static_contract_review.md"

STATIC_REVIEW_READY_STATUS = _review.READY_STATUS
STATIC_REVIEW_AUTHORIZED_NEXT_WORK = _review.AUTHORIZED_NEXT_WORK
EXPECTED_DP_HEAD = _review.EXPECTED_DP_HEAD
FORMAL_SEEDS = _review.FORMAL_SEEDS
BLOCKED_ACTIONS = _review.BLOCKED_ACTIONS

PRODUCTION_FILE = "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py"
ROUTE_TEST_FILE = "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py"
UNIT_TEST_FILE = (
    "camp_core/tests/test_diffusion_planner_residual_comfort_remediation_"
    "followup_materially_different_generator_guarded_fixed_snapshot_screen_"
    "rerun_failure_attribution_remediation_implementation_contract.py"
)
NEW_PROFILE = "lane_red_hard_feasible_jerk_lateral_support_v2"
NEW_POLICY = "lane_red_hard_feasible_jerk_lateral_material_support"

REQUIRED_CONTRACTS = (
    "current_tick_input_contract",
    "finite_default_off_append_contract",
    "fixed_dp_black_box_contract",
    "hard_plus_comfort_target_contract",
    "no_gate_relaxation_contract",
    "descriptor_legality_contract",
    "affine_convex_master_contract",
    "positive_support_before_training_contract",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation plan after the material generator "
            "remediation design static contract review."
        )
    )
    parser.add_argument(
        "--static_review_root",
        type=Path,
        default=Path(DEFAULT_STATIC_REVIEW_ROOT),
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
        static_review_root=args.static_review_root,
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
    static_review_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(static_review_root)
    source = _static_review_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    plan = _implementation_plan(source)
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
                "implementation_plan_v1"
            ),
            "label": label,
            "role": "plan-only implementation plan after static contract review",
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
                "This plan reads only the completed static contract review "
                "artifact and audit authorization. It does not edit "
                "implementation code, create candidates, rerun the screen, "
                "run DP, run replay, use formal seeds, define or promote "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T "
                "w, mutate the convex simplex/CVaR/L2 master, train CAMP, "
                "change online selection, modify DP weights or code, or "
                "claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "static_review_artifact": _strip_payload(artifact),
        "static_review_summary": source,
        "implementation_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    lines = [
        "# Material Generator Remediation Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation-only authorized next: `{decision['implementation_only_authorized']}`",
        f"- New default-off profile: `{plan['new_default_off_profile']}`",
        f"- New generator policy: `{plan['new_generator_policy']}`",
        "",
        "## Allowed Files For Next Gate",
        "",
    ]
    for item in plan["allowed_files"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Implementation Slices", ""])
    for item in plan["implementation_slices"]:
        lines.append(f"### {item['name']}")
        lines.append("")
        lines.append(item["purpose"])
        lines.append("")
        lines.append(f"- Contract: `{item['contract']}`")
        lines.append("")
    lines.extend(["## Required Tests", ""])
    for item in plan["required_tests"]:
        lines.append(f"- `{item['name']}`: {item['contract']}")
    lines.extend(["", "## Post-Implementation Gates", ""])
    for item in plan["post_implementation_gates"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Rollback Conditions", ""])
    for item in plan["rollback_conditions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _implementation_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": (
            "material_generator_guarded_fixed_snapshot_screen_rerun_failure_"
            "attribution_remediation_implementation_plan_only"
        ),
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "new_default_off_profile": NEW_PROFILE,
        "new_generator_policy": NEW_POLICY,
        "allowed_files": [PRODUCTION_FILE, ROUTE_TEST_FILE, UNIT_TEST_FILE],
        "target_contract": {
            "fixed_dp_head": EXPECTED_DP_HEAD,
            "formal_seeds": sorted(FORMAL_SEEDS),
            "score_contract": "score_k(w)=a_k^T w",
            "master_contract": "convex simplex/CVaR/L2 master unchanged",
            "required_static_contracts": REQUIRED_CONTRACTS,
        },
        "implementation_slices": [
            {
                "name": "explicit_v2_profile_policy_pair",
                "purpose": (
                    "Add an explicit v2 default-off profile and generator "
                    "policy for the hard-plus-comfort remediation while "
                    "leaving the existing material support profile unchanged."
                ),
                "contract": (
                    "default config remains off; mismatched or invalid profile/"
                    "policy combinations fail closed"
                ),
            },
            {
                "name": "lane_red_hard_feasibility_precheck",
                "purpose": (
                    "Precheck lane crossing, road-border margin, red-light "
                    "timing, and kinematic margins before appending any support "
                    "row."
                ),
                "contract": (
                    "current-tick route and traffic-light geometry only; no DP "
                    "row mutation and no hard-gate relaxation"
                ),
            },
            {
                "name": "jerk_limited_stop_and_creep_profiles",
                "purpose": (
                    "Construct bounded stop/creep profiles to address command "
                    "and rollout jerk blockers while retaining progress."
                ),
                "contract": (
                    "finite deterministic support rows, capped count, no future "
                    "labels, replay outcomes, formal seeds, or DP-side signals"
                ),
            },
            {
                "name": "lateral_heading_continuity_projection",
                "purpose": (
                    "Project support rows onto the current lane corridor with "
                    "bounded lateral and heading residuals before existing "
                    "comfort filters evaluate them."
                ),
                "contract": (
                    "candidate-local rollout features only; selected index, "
                    "fallback, score, and online selector outputs unchanged"
                ),
            },
            {
                "name": "diagnostic_descriptor_payload_v2",
                "purpose": (
                    "Record hard feasibility margin, jerk, lateral, and "
                    "progress diagnostic descriptors for later evidence."
                ),
                "contract": (
                    "report-only payload with nonnegative or legal "
                    "hinge/signed-split channels; no atom promotion and no "
                    "change to score_k(w)=a_k^T w"
                ),
            },
        ],
        "required_tests": [
            {
                "name": "default_off_and_v1_behavior_unchanged",
                "contract": (
                    "off and existing v1 material profiles preserve candidate "
                    "counts, candidate0, selected index, fallback, and online "
                    "selector behavior"
                ),
            },
            {
                "name": "v2_explicit_pair_required",
                "contract": (
                    "v2 support rows appear only when both the v2 policy and "
                    "v2 profile are explicitly selected"
                ),
            },
            {
                "name": "candidate0_and_dp_rows_preserved",
                "contract": (
                    "v2 rows append after all DP rows and never mutate DP "
                    "candidate payloads"
                ),
            },
            {
                "name": "hard_precheck_fail_closed",
                "contract": (
                    "synthetic lane, red, road-border, and kinematic failures "
                    "block support append without relaxing gates"
                ),
            },
            {
                "name": "finite_current_tick_inputs_only",
                "contract": (
                    "fixtures reject future labels, replay outcomes, formal "
                    "seeds, and unavailable tick-plus-one fields"
                ),
            },
            {
                "name": "descriptor_legality_and_affine_contract",
                "contract": (
                    "all descriptor channels are nonnegative or legal "
                    "hinge/signed-split values and preserve affine score "
                    "compatibility"
                ),
            },
        ],
        "post_implementation_gates": [
            "remediation_post_implementation_static_contract_review_only",
            "remediation_fixed_snapshot_screen_rerun_plan_only",
            "remediation_guarded_fixed_snapshot_screen_rerun_only",
            "remediation_guarded_fixed_snapshot_screen_rerun_failure_attribution_only",
        ],
        "rollback_conditions": [
            "any default-off or existing v1 behavior change",
            "candidate0, DP row, selected-index, fallback, score, or online selector mutation",
            "any future-label, replay-outcome, formal-seed, or DP-side dependency",
            "any hard/progress/comfort gate relaxation",
            "any descriptor that is not nonnegative or legal hinge/signed-split",
            "any change to score_k(w)=a_k^T w or convex simplex/CVaR/L2 assumptions",
        ],
        "blocked_boundaries": [
            "this plan gate does not edit implementation code",
            "candidate generation execution is not authorized by this plan gate",
            "fixed-snapshot screen rerun is not authorized by this plan gate",
            "closed-loop replay is not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "CAMP retraining and training execution are not authorized",
            "online selector promotion and atom promotion are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
        "source_contract": source,
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    json_path = root / STATIC_REVIEW_JSON
    md_path = root / STATIC_REVIEW_MD
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


def _static_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    contract = _dict(payload.get("static_contract"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_authorized": bool(
            decision.get("implementation_plan_authorized")
        ),
        "required_contracts_true": all(
            contract.get(key) is True for key in REQUIRED_CONTRACTS
        ),
        "contract_true_keys": sorted(key for key, value in contract.items() if value is True),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_root_exists", bool(artifact["exists"])),
        _check("static_review_json_exists", bool(artifact["json_exists"])),
        _check("static_review_md_exists", bool(artifact["markdown_exists"])),
        _check("static_review_json_parseable", bool(artifact["payload"])),
        _check(
            "static_review_markdown_records_title",
            "Static Contract Review" in artifact["markdown_text"],
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
        _check("audit_records_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_implementation_plan", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_affine_contract", "affine_convex_master_contract=True" in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_status_complete", source["status"] == STATIC_REVIEW_READY_STATUS),
        _check("static_review_passed", source["passed"] is True),
        _check("static_review_failed_checks_empty", not source["failed_checks"]),
        _check("static_review_authorizes_this_plan", source["authorized_next_work"] == STATIC_REVIEW_AUTHORIZED_NEXT_WORK),
        _check("static_review_implementation_plan_authorized", source["implementation_plan_authorized"] is True),
        _check("static_review_required_contracts_true", source["required_contracts_true"]),
        _check("static_review_no_blocked_actions", not source["blocked_action_conflicts"]),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    allowed = set(plan["allowed_files"])
    slices = {item["name"] for item in plan["implementation_slices"]}
    tests = {item["name"] for item in plan["required_tests"]}
    return [
        _check(
            "plan_selection_type",
            plan["selection_type"]
            == "material_generator_guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_implementation_plan_only",
        ),
        _check("plan_selects_implementation_only", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_new_profile_named", plan["new_default_off_profile"] == NEW_PROFILE),
        _check("plan_new_policy_named", plan["new_generator_policy"] == NEW_POLICY),
        _check("plan_allows_production_file", PRODUCTION_FILE in allowed),
        _check("plan_allows_route_test", ROUTE_TEST_FILE in allowed),
        _check("plan_allows_unit_test", UNIT_TEST_FILE in allowed),
        _check("plan_has_v2_pair_slice", "explicit_v2_profile_policy_pair" in slices),
        _check("plan_has_hard_precheck_slice", "lane_red_hard_feasibility_precheck" in slices),
        _check("plan_has_jerk_profile_slice", "jerk_limited_stop_and_creep_profiles" in slices),
        _check("plan_has_lateral_projection_slice", "lateral_heading_continuity_projection" in slices),
        _check("plan_has_descriptor_payload_slice", "diagnostic_descriptor_payload_v2" in slices),
        _check("plan_has_default_off_test", "default_off_and_v1_behavior_unchanged" in tests),
        _check("plan_has_v2_pair_test", "v2_explicit_pair_required" in tests),
        _check("plan_has_candidate0_test", "candidate0_and_dp_rows_preserved" in tests),
        _check("plan_has_hard_precheck_test", "hard_precheck_fail_closed" in tests),
        _check("plan_has_current_tick_test", "finite_current_tick_inputs_only" in tests),
        _check("plan_has_descriptor_test", "descriptor_legality_and_affine_contract" in tests),
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_candidate0", "candidate0" in text),
        _check("plan_mentions_no_future_labels", "future labels" in text),
        _check("plan_mentions_no_gate_relaxation", "gate relaxation" in text),
        _check("plan_mentions_hinge_signed_split", "hinge/signed-split" in text),
        _check("plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_formal_seed_freeze", "formal seeds 11/12/13" in text),
        _check("plan_mentions_dp_fixed", "dp weights" in text and "dp code" in text),
        _check("plan_mentions_camp_over_dp_blocked", "camp-over-dp-top-1" in text),
        _check("plan_mentions_benders_blocked", "classical benders" in text),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_implementation_only_next", decision["implementation_only_authorized"] is True),
        _check("boundary_blocks_current_implementation_edit", decision["implementation_code_edit_authorized"] is False),
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
        _check("boundary_formal_seed_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_implementation_plan_ready": passed,
        "implementation_only_authorized": passed,
        "remediation_implementation_only_authorized": passed,
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


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
