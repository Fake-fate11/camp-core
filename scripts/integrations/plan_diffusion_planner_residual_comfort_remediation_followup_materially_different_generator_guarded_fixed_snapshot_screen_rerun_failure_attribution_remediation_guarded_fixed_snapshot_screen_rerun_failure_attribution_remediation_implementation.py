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
    "snapshot_screen_rerun_failure_attribution_remediation_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution_remediation_design_static_contract"
)
_review = importlib.import_module(_REVIEW_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_only"
)

DEFAULT_STATIC_REVIEW_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "rerun_failure_design_static_review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
STATIC_REVIEW_JSON = (
    "material_generator_remediation_rerun_failure_design_static_contract_review.json"
)
STATIC_REVIEW_MD = (
    "material_generator_remediation_rerun_failure_design_static_contract_review.md"
)

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
    "rerun_failure_attribution_remediation_guarded_fixed_snapshot_screen_"
    "rerun_failure_attribution_remediation_implementation_contract.py"
)
NEW_PROFILE = "lane_red_hard_feasible_comfort_first_support_v3"
NEW_POLICY = "lane_red_hard_feasible_comfort_first_material_support"

REQUIRED_CONTRACTS = (
    "current_tick_input_contract",
    "finite_default_off_append_contract",
    "fixed_dp_black_box_contract",
    "near_threshold_hard_support_contract",
    "zero_comfort_support_contract",
    "no_gate_relaxation_contract",
    "descriptor_legality_contract",
    "report_only_contract",
    "affine_convex_master_contract",
    "positive_support_before_execution_contract",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation plan after the v2 remediation design "
            "static contract review."
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
                "guarded_fixed_snapshot_screen_rerun_failure_attribution_"
                "remediation_implementation_plan_v1"
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
        "# Material Generator V3 Remediation Implementation Plan",
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
            "material_generator_v2_failure_static_review_implementation_plan_only"
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
            "source_contracts": source["contract_true_names"],
        },
        "implementation_slices": [
            {
                "name": "explicit_v3_profile_policy_pair",
                "purpose": (
                    "Add a new default-off v3 profile/policy pair without "
                    "changing off, v1, or v2 behavior."
                ),
                "contract": (
                    "support rows appear only when both the v3 policy and v3 "
                    "profile are explicitly selected; mismatches fail closed"
                ),
            },
            {
                "name": "near_threshold_hard_support_precheck_v3",
                "purpose": (
                    "Close the small remaining hard-support gap with stricter "
                    "current-tick lane, red, road-border, and kinematic margin "
                    "prechecks before append."
                ),
                "contract": (
                    "no hard threshold relaxation, no DP row mutation, no DP "
                    "config/code/weight/invocation change"
                ),
            },
            {
                "name": "comfort_first_profile_precheck_v3",
                "purpose": (
                    "Make command jerk, rollout jerk, lateral, smoothness, and "
                    "progress proxy feasibility part of construction before "
                    "candidate append."
                ),
                "contract": (
                    "current-tick deterministic proxies only; no replay labels, "
                    "future outcomes, formal seeds, or comfort budget relaxation"
                ),
            },
            {
                "name": "lane_corridor_continuity_tightening_v3",
                "purpose": (
                    "Tighten support point projection to a continuous current "
                    "route corridor with bounded lateral and heading residuals."
                ),
                "contract": (
                    "candidate-local features only; selected index, fallback, "
                    "score, and online selector outputs unchanged"
                ),
            },
            {
                "name": "stop_creep_progress_balance_v3",
                "purpose": (
                    "Balance red-stop compliance with bounded creep/progress so "
                    "hard survivors do not become progress-loss comfort failures."
                ),
                "contract": (
                    "bounded acceleration and jerk profiles from current speed "
                    "and stop distance only; existing progress gate must be "
                    "earned, not relaxed"
                ),
            },
            {
                "name": "diagnostic_descriptor_payload_v3_report_only",
                "purpose": (
                    "Record hard margin, comfort proxy, lateral/heading, and "
                    "support-gap descriptors for evidence and future review."
                ),
                "contract": (
                    "report-only nonnegative or legal hinge/signed-split "
                    "channels; no atom promotion and no change to "
                    "score_k(w)=a_k^T w"
                ),
            },
        ],
        "required_tests": [
            {
                "name": "default_off_v1_v2_behavior_unchanged",
                "contract": (
                    "off, v1, and v2 profiles preserve candidate counts, "
                    "candidate0, DP rows, selected index, fallback, and online "
                    "selector behavior"
                ),
            },
            {
                "name": "v3_explicit_pair_required",
                "contract": (
                    "v3 support rows append only under the explicit v3 policy/"
                    "profile pair"
                ),
            },
            {
                "name": "candidate0_and_dp_rows_preserved",
                "contract": "v3 appends after all DP rows and never mutates them",
            },
            {
                "name": "hard_support_precheck_fail_closed",
                "contract": (
                    "lane, red, road-border, and kinematic margin failures block "
                    "v3 support append"
                ),
            },
            {
                "name": "comfort_first_precheck_fail_closed",
                "contract": (
                    "command jerk, rollout jerk, lateral, smoothness, and "
                    "progress proxy failures block v3 support append"
                ),
            },
            {
                "name": "finite_current_tick_inputs_only",
                "contract": (
                    "fixtures reject future labels, replay outcomes, formal "
                    "seeds, and tick-plus-one fields"
                ),
            },
            {
                "name": "descriptor_legality_and_affine_contract",
                "contract": (
                    "descriptor channels remain nonnegative or legal "
                    "hinge/signed-split report-only values and preserve affine "
                    "score_k(w)=a_k^T w plus simplex/CVaR/L2 convexity"
                ),
            },
        ],
        "post_implementation_gates": [
            "implementation-only contract tests",
            "post-implementation static contract review",
            "fixed-snapshot screen rerun plan-only gate",
            "guarded nonformal fixed-snapshot screen rerun only after plan approval",
        ],
        "rollback_conditions": [
            "off, v1, or v2 behavior changes",
            "candidate0 or DP rows mutate",
            "hard/progress/comfort thresholds are relaxed",
            "descriptor payload changes selection, fallback, score, or online selector output",
            "future labels, replay outcomes, formal seeds, Full36, or DP-side signals are required",
            "any score channel cannot remain affine in score_k(w)=a_k^T w",
        ],
        "blocked_boundaries": [
            "this plan gate does not edit implementation code",
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
    blocked_authorizations = [
        key
        for key in BLOCKED_ACTIONS
        if bool(decision.get(key) or _dict(payload.get("blocked_actions")).get(key))
    ]
    contract_true_names = [
        name
        for name in REQUIRED_CONTRACTS
        if contract.get(name) is True
    ]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failed_checks": _list(decision.get("failed_checks")),
        "implementation_plan_authorized": bool(
            decision.get("implementation_plan_authorized")
        ),
        "contract_true_names": contract_true_names,
        "contract_values": {name: bool(contract.get(name)) for name in REQUIRED_CONTRACTS},
        "blocked_authorizations": blocked_authorizations,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_root_exists", bool(artifact["exists"])),
        _check("static_review_json_exists", bool(artifact["json_exists"])),
        _check("static_review_md_exists", bool(artifact["markdown_exists"])),
        _check("static_review_json_parseable", bool(artifact["payload"])),
        _check(
            "static_review_markdown_records_status",
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
        _check("audit_mentions_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_implementation_plan", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_fixed_dp", EXPECTED_DP_HEAD in audit_text),
        _check("audit_records_no_training", "training_execution_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_status_complete", source["status"] == STATIC_REVIEW_READY_STATUS),
        _check("static_review_passed", source["passed"] is True),
        _check("static_review_no_failed_checks", not source["failed_checks"]),
        _check("static_review_authorizes_this_plan", source["authorized_next_work"] == STATIC_REVIEW_AUTHORIZED_NEXT_WORK),
        _check("static_review_implementation_plan_authorized", source["implementation_plan_authorized"] is True),
        _check("static_review_required_contracts_true", set(source["contract_true_names"]) == set(REQUIRED_CONTRACTS)),
        _check("static_review_no_blocked_actions", not source["blocked_authorizations"]),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    slices = {item["name"] for item in plan["implementation_slices"]}
    tests = {item["name"] for item in plan["required_tests"]}
    return [
        _check(
            "plan_selection_type",
            plan["selection_type"]
            == "material_generator_v2_failure_static_review_implementation_plan_only",
        ),
        _check("plan_selects_implementation_only", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_uses_v3_profile", plan["new_default_off_profile"] == NEW_PROFILE),
        _check("plan_uses_v3_policy", plan["new_generator_policy"] == NEW_POLICY),
        _check("plan_allows_production_file", PRODUCTION_FILE in plan["allowed_files"]),
        _check("plan_allows_route_test", ROUTE_TEST_FILE in plan["allowed_files"]),
        _check("plan_allows_unit_test", UNIT_TEST_FILE in plan["allowed_files"]),
        _check("plan_has_explicit_pair_slice", "explicit_v3_profile_policy_pair" in slices),
        _check("plan_has_hard_slice", "near_threshold_hard_support_precheck_v3" in slices),
        _check("plan_has_comfort_slice", "comfort_first_profile_precheck_v3" in slices),
        _check("plan_has_lateral_slice", "lane_corridor_continuity_tightening_v3" in slices),
        _check("plan_has_progress_slice", "stop_creep_progress_balance_v3" in slices),
        _check("plan_has_descriptor_slice", "diagnostic_descriptor_payload_v3_report_only" in slices),
        _check("plan_tests_default_off", "default_off_v1_v2_behavior_unchanged" in tests),
        _check("plan_tests_explicit_pair", "v3_explicit_pair_required" in tests),
        _check("plan_tests_dp_rows", "candidate0_and_dp_rows_preserved" in tests),
        _check("plan_tests_hard_precheck", "hard_support_precheck_fail_closed" in tests),
        _check("plan_tests_comfort_precheck", "comfort_first_precheck_fail_closed" in tests),
        _check("plan_tests_current_tick", "finite_current_tick_inputs_only" in tests),
        _check("plan_tests_affine_contract", "descriptor_legality_and_affine_contract" in tests),
        _check("plan_mentions_no_dp_change", "dp weights" in text and "dp code" in text and "dp config" in text),
        _check("plan_mentions_formal_seeds_frozen", "formal seeds 11/12/13 remain frozen" in text),
        _check("plan_mentions_affine_score", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_no_claims", "camp-over-dp-top-1" in text and "safety-benefit" in text),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_implementation_only", decision["implementation_only_authorized"] is True),
        _check("boundary_blocks_implementation_edit_in_plan", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
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
