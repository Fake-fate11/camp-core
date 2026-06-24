#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
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

_REVIEW_MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_remediation_"
    "followup_materially_different_generator_static_contract"
)
_review = importlib.import_module(_REVIEW_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_implementation_only"
)

DEFAULT_DEVELOPMENT_ROOT = _review.DEFAULT_DEVELOPMENT_ROOT
DEFAULT_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_followup_materially_different_generator_static_contract_"
    "review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

REVIEW_JSON = "static_contract_review.json"
REVIEW_MD = "static_contract_review.md"
REVIEW_READY_STATUS = _review.READY_STATUS
REVIEW_AUTHORIZED_NEXT_WORK = _review.AUTHORIZED_NEXT_WORK
EXPECTED_DP_HEAD = _review.EXPECTED_DP_HEAD
FORMAL_SEEDS = _review.FORMAL_SEEDS

PRODUCTION_FILE = "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py"
ROUTE_TEST_FILE = "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py"
UNIT_TEST_FILE = (
    "camp_core/tests/test_diffusion_planner_residual_comfort_remediation_"
    "followup_materially_different_generator_implementation_contract.py"
)
NEW_PROFILE = "lane_station_jerk_limited_red_stop_support_v1"
NEW_POLICY = "lane_station_jerk_limited_red_stop_material_support"

BLOCKED_ACTIONS = _review.BLOCKED_ACTIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation plan for the follow-up materially "
            "different generator. It does not edit implementation code."
        )
    )
    parser.add_argument("--review_root", type=Path, default=Path(DEFAULT_REVIEW_ROOT))
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
        review_root=args.review_root,
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
    review_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(review_root)
    source = _review_summary(artifact["payload"])
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
                "remediation_followup_materially_different_generator_"
                "implementation_plan_v1"
            ),
            "label": label,
            "role": "plan-only implementation plan for reviewed generator",
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
        "# Residual Comfort Materially Different Generator Implementation Plan",
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
    lines.extend(["", "## Implementation Steps", ""])
    for item in plan["implementation_steps"]:
        lines.append(f"- `{item['name']}`: {item['contract']}")
    lines.extend(["", "## Required Tests", ""])
    for item in plan["required_tests"]:
        lines.append(f"- `{item['name']}`: {item['contract']}")
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
            "residual_comfort_remediation_followup_materially_different_"
            "generator_implementation_plan_only"
        ),
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "new_default_off_profile": NEW_PROFILE,
        "new_generator_policy": NEW_POLICY,
        "allowed_files": [PRODUCTION_FILE, ROUTE_TEST_FILE, UNIT_TEST_FILE],
        "implementation_steps": [
            {
                "name": "add_default_off_profile_constants",
                "contract": (
                    "add a new explicit profile and generator policy, both "
                    "default-off; invalid profile or policy must fail closed"
                ),
            },
            {
                "name": "candidate0_preserving_append_path",
                "contract": (
                    "preserve candidate0, existing DP rows, fallback behavior, "
                    "selected index, online selector behavior, and deployed "
                    "atom schema; append only bounded support rows when the "
                    "new profile is explicitly selected"
                ),
            },
            {
                "name": "lane_station_jerk_limited_generation",
                "contract": (
                    "synthesize deterministic finite current-tick support "
                    "rows from lane-station geometry, current ego state, "
                    "traffic-light state, and stop-line geometry; no future "
                    "labels or replay outcomes"
                ),
            },
            {
                "name": "lateral_continuity_projection",
                "contract": (
                    "project support rows onto current route geometry with "
                    "bounded lateral and heading residuals before existing "
                    "hard/progress/comfort gates evaluate them"
                ),
            },
            {
                "name": "descriptor_payload_default_off",
                "contract": (
                    "record only diagnostic descriptor payloads with "
                    "nonnegative or legal hinge/signed-split channels; do not "
                    "promote atoms or alter score_k(w)=a_k^T w"
                ),
            },
        ],
        "required_tests": [
            {
                "name": "default_off_no_behavior_change",
                "contract": (
                    "baseline profile produces byte-equivalent candidate "
                    "counts, selected index, fallback, and online selector "
                    "signals in synthetic fixtures"
                ),
            },
            {
                "name": "candidate0_and_dp_rows_preserved",
                "contract": (
                    "new support rows append after existing rows and never "
                    "replace candidate0 or mutate DP candidate payloads"
                ),
            },
            {
                "name": "finite_current_tick_inputs_only",
                "contract": (
                    "fixtures reject future labels, replay outcomes, formal "
                    "seeds, and any unavailable tick-plus-one fields"
                ),
            },
            {
                "name": "descriptor_legality",
                "contract": (
                    "all new diagnostic descriptor channels are nonnegative "
                    "or legal hinge/signed-split values and preserve affine "
                    "score compatibility"
                ),
            },
            {
                "name": "support_cap_and_fail_closed",
                "contract": (
                    "support candidate count is capped, deterministic, and "
                    "invalid profile/policy values fail closed"
                ),
            },
        ],
        "post_implementation_gates": [
            "materially_different_generator_post_implementation_static_contract_review_only",
            "materially_different_generator_fixed_snapshot_screen_rerun_plan_only",
            "materially_different_generator_guarded_fixed_snapshot_screen_rerun_only",
            "materially_different_generator_guarded_fixed_snapshot_screen_rerun_failure_attribution_only",
        ],
        "rollback_conditions": [
            "any default-off behavior change outside the explicit profile",
            "candidate0, DP row, selected-index, fallback, or online selector mutation",
            "any future-label, replay-outcome, formal-seed, or DP-side dependency",
            "any descriptor that is not nonnegative or legal hinge/signed-split",
            "any change to score_k(w)=a_k^T w or convex simplex/CVaR/L2 assumptions",
        ],
        "blocked_boundaries": [
            "this gate does not edit implementation code",
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
    json_path = root / REVIEW_JSON
    md_path = root / REVIEW_MD
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


def _review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    contract = _dict(payload.get("static_contract"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_authorized": decision.get("implementation_plan_authorized"),
        "contract_true_keys": sorted(key for key, value in contract.items() if value is True),
        "all_required_contracts_true": all(
            contract.get(key) is True
            for key in (
                "current_tick_input_contract",
                "finite_default_off_append_contract",
                "material_difference_contract",
                "hard_progress_comfort_gate_contract",
                "descriptor_legality_contract",
                "affine_convex_master_contract",
                "dp_fixed_black_box_contract",
                "execution_boundary_contract",
                "positive_support_before_training_contract",
            )
        ),
        "blocked_action_conflicts": sorted(
            key for key in BLOCKED_ACTIONS if decision.get(key) is True
        ),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_root_exists", artifact["exists"]),
        _check("static_review_json_exists", artifact["json_exists"]),
        _check("static_review_markdown_exists", artifact["markdown_exists"]),
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
        _check("audit_records_static_review_complete", REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_implementation_plan", REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_contract_verdict", "affine_convex_master_contract=True" in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_status_complete", source["status"] == REVIEW_READY_STATUS),
        _check("static_review_passed", source["passed"] is True),
        _check("static_review_failed_checks_empty", not source["failed_checks"]),
        _check("static_review_authorizes_this_plan", source["authorized_next_work"] == REVIEW_AUTHORIZED_NEXT_WORK),
        _check("static_review_implementation_plan_authorized", source["implementation_plan_authorized"] is True),
        _check("static_review_required_contracts_true", source["all_required_contracts_true"]),
        _check("static_review_no_blocked_actions", not source["blocked_action_conflicts"]),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    allowed = set(plan["allowed_files"])
    steps = {item["name"] for item in plan["implementation_steps"]}
    tests = {item["name"] for item in plan["required_tests"]}
    return [
        _check(
            "plan_selection_type",
            plan["selection_type"]
            == "residual_comfort_remediation_followup_materially_different_generator_implementation_plan_only",
        ),
        _check("plan_selects_implementation_only", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_new_profile_named", plan["new_default_off_profile"] == NEW_PROFILE),
        _check("plan_new_policy_named", plan["new_generator_policy"] == NEW_POLICY),
        _check("plan_allows_production_file", PRODUCTION_FILE in allowed),
        _check("plan_allows_route_test", ROUTE_TEST_FILE in allowed),
        _check("plan_allows_unit_test", UNIT_TEST_FILE in allowed),
        _check("plan_has_profile_constants_step", "add_default_off_profile_constants" in steps),
        _check("plan_has_candidate0_step", "candidate0_preserving_append_path" in steps),
        _check("plan_has_lane_station_step", "lane_station_jerk_limited_generation" in steps),
        _check("plan_has_lateral_projection_step", "lateral_continuity_projection" in steps),
        _check("plan_has_descriptor_payload_step", "descriptor_payload_default_off" in steps),
        _check("plan_has_default_off_test", "default_off_no_behavior_change" in tests),
        _check("plan_has_candidate0_test", "candidate0_and_dp_rows_preserved" in tests),
        _check("plan_has_current_tick_test", "finite_current_tick_inputs_only" in tests),
        _check("plan_has_descriptor_test", "descriptor_legality" in tests),
        _check("plan_has_cap_test", "support_cap_and_fail_closed" in tests),
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_candidate0", "candidate0" in text),
        _check("plan_mentions_no_future_labels", "future labels" in text),
        _check("plan_mentions_hinge_signed_split", "hinge/signed-split" in text),
        _check("plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_formal_seed_freeze", "formal seeds 11/12/13" in text),
        _check("plan_mentions_dp_fixed", "dp weights" in text and "dp code" in text),
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
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "materially_different_generator_implementation_plan_ready": passed,
        "implementation_only_authorized": passed,
        "materially_different_generator_implementation_only_authorized": passed,
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


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
