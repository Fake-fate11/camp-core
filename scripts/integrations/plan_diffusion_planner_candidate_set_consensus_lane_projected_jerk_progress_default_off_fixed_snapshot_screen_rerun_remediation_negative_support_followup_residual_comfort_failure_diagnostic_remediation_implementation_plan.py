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

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
    FORMAL_SEEDS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_design_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
    REQUIRED_REJECTED_NON_FIXES,
    REQUIRED_TRACKS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_implementation_static_"
    "contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_STATIC_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_design_static_contract_review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

STATIC_REVIEW_JSON = "static_contract_review.json"
STATIC_REVIEW_MD = "static_contract_review.md"

PLANNED_SCREEN_SOURCE = (
    "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py"
)
PLANNED_ROUTE_TEST = "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py"
PLANNED_CONTRACT_TEST = (
    "camp_core/tests/test_diffusion_planner_candidate_set_consensus_lane_"
    "projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_"
    "remediation_negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_implementation_contract.py"
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
            "Plan-only implementation plan after residual comfort remediation "
            "design static review. It does not edit code or execute screens."
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
    label: Optional[str] = None,
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
                "remediation_implementation_plan_v1"
            ),
            "label": label,
            "role": "plan-only implementation plan for residual comfort remediation",
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
                "This implementation plan reads only the completed static "
                "review artifact and audit. It does not edit implementation "
                "code, create candidates, rerun the screen, run DP, run replay, "
                "use formal seeds, define runtime atoms, choose lambda online, "
                "alter score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 "
                "master, train CAMP, change online selection, modify DP "
                "weights or code, or claim a DP-side classical Benders "
                "decomposition."
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
        "remediation_implementation_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["remediation_implementation_plan"]
    lines = [
        "# Residual Comfort Remediation Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Planned Files",
        "",
    ]
    for path in plan["implementation_scope"]["planned_files"]:
        lines.append(f"- `{path}`")
    lines.extend(["", "## Implementation Steps", ""])
    for step in plan["implementation_steps"]:
        lines.append(f"### {step['name']}")
        lines.append("")
        lines.append(step["purpose"])
        lines.append("")
        lines.append(f"- Contract: `{step['contract']}`")
        lines.append("")
    lines.extend(["## Required Tests", ""])
    for name in plan["required_tests"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / STATIC_REVIEW_JSON
    markdown_path = root / STATIC_REVIEW_MD
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


def _static_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    contracts = _list(review.get("contracts"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "remediation_implementation_plan_authorized": bool(
            decision.get("remediation_implementation_plan_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "all_contracts_pass": bool(review.get("all_contracts_pass")),
        "contracts": [
            {
                "name": str(item.get("name")),
                "status": str(item.get("status")),
            }
            for item in contracts
            if isinstance(item, dict)
        ],
    }


def _implementation_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "residual_comfort_failure_diagnostic_remediation_implementation_plan_only",
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "implementation_scope": {
            "planned_files": [
                PLANNED_SCREEN_SOURCE,
                PLANNED_ROUTE_TEST,
                PLANNED_CONTRACT_TEST,
            ],
            "default_off": True,
            "report_only_until_execution_gate": True,
            "current_tick_finite_candidate_features_only": True,
            "preserve_candidate_ordering": True,
            "preserve_candidate0": True,
            "no_candidate_mutation": True,
            "no_selected_index_mutation": True,
            "no_fallback_mutation": True,
            "no_online_selector_change": True,
            "no_deployed_atom_schema_change": True,
            "no_dp_import": True,
            "no_reward_recompute": True,
            "no_tracker_recompute": True,
        },
        "implementation_steps": [
            {
                "name": "default_off_config_pin",
                "purpose": (
                    "Plan a non-default switch for any future residual comfort "
                    "remediation path so current production behavior and "
                    "candidate0 semantics remain unchanged."
                ),
                "contract": (
                    "default path unchanged; no candidate generation execution "
                    "or fixed-snapshot screen rerun in this gate"
                ),
            },
            {
                "name": "command_jerk_descriptor_payload",
                "purpose": (
                    "Plan report-only command-jerk descriptor fields for the "
                    "hard/progress survivor comfort gap using current-tick "
                    "finite candidate features."
                ),
                "contract": (
                    "descriptors remain diagnostics unless a later atom gate "
                    "proves nonnegative or hinge/signed-split legality"
                ),
            },
            {
                "name": "support_intervention_guardrails",
                "purpose": (
                    "Plan explicit guardrails a later implementation-only gate "
                    "must satisfy before any support intervention can be "
                    "screened."
                ),
                "contract": (
                    "no mutation of candidates, scores, selected index, "
                    "fallback, online selector, or deployed atom schema"
                ),
            },
            {
                "name": "contract_tests_before_execution",
                "purpose": (
                    "Plan tests that prove execution, replay, training, formal "
                    "seeds, Full36, promotion, claims, and DP changes remain "
                    "blocked."
                ),
                "contract": "implementation tests must fail closed on authorization leaks",
            },
        ],
        "required_tests": [
            "test_residual_comfort_remediation_default_off_preserves_candidate0",
            "test_residual_comfort_remediation_report_only_descriptor_payload",
            "test_residual_comfort_remediation_blocks_candidate_mutation",
            "test_residual_comfort_remediation_blocks_online_selector_and_atoms",
            "test_residual_comfort_remediation_preserves_affine_score_and_convex_master",
            "test_residual_comfort_remediation_blocks_dp_import_reward_tracker_recompute",
            "test_residual_comfort_remediation_blocks_execution_training_replay_formal_seeds",
            "test_residual_comfort_remediation_cli_contract_artifact",
        ],
        "static_review_requirements": [
            "prove planned implementation files are scoped to the remediation contract",
            "prove default behavior and candidate0 ordering remain unchanged",
            "prove report-only descriptor payload cannot alter candidates, scores, selected index, fallback, online selector, or deployed atom schema",
            "prove any later atom proposal must be nonnegative or legal hinge/signed-split",
            "prove score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master remain unchanged",
            "prove no DP import, reward recompute, tracker recompute, DP code, DP weights, DP config, or DP invocation change is required",
            "prove candidate generation execution, fixed-snapshot screen rerun, replay, Full36, formal seeds 11/12/13, CAMP retraining, promotion, and claims remain unauthorized",
        ],
        "blocked_boundaries": [
            "implementation code edits are not authorized in this plan gate",
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
        _check("audit_records_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_implementation_plan", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_no_implementation_edit", "implementation_code_edit_authorized=False" in audit_text),
        _check("audit_records_no_execution", "candidate_generation_execution_authorized=False" in audit_text),
        _check("audit_records_no_training", "training_execution_authorized=False" in audit_text),
        _check("audit_records_no_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    contracts = {item["name"]: item["status"] for item in source["contracts"]}
    return [
        _check("static_review_status_complete", source["status"] == STATIC_REVIEW_READY_STATUS),
        _check("static_review_passed", source["passed"] is True),
        _check("static_review_failed_checks_empty", not source["failed_checks"]),
        _check("static_review_authorizes_this_plan", source["authorized_next_work"] == STATIC_REVIEW_AUTHORIZED_NEXT_WORK),
        _check("static_review_implementation_plan_authorized", source["remediation_implementation_plan_authorized"] is True),
        _check("static_review_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("static_review_all_contracts_pass", source["all_contracts_pass"] is True),
        *[
            _check(f"static_review_track_contract_{name}", contracts.get("required_tracks_present") == "pass")
            for name in REQUIRED_TRACKS[:1]
        ],
        *[
            _check(f"static_review_nonfix_contract_{name}", contracts.get("rejected_non_fixes_present") == "pass")
            for name in REQUIRED_REJECTED_NON_FIXES[:1]
        ],
        _check("static_review_math_contract", contracts.get("atom_math_contract") == "pass"),
        _check("static_review_convex_contract", contracts.get("convex_master_contract") == "pass"),
        _check("static_review_execution_boundary", contracts.get("execution_training_boundary") == "pass"),
        _check("static_review_dp_boundary", contracts.get("dp_fixed_boundary") == "pass"),
        _check("static_review_claim_boundary", contracts.get("claim_boundary") == "pass"),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    scope = plan["implementation_scope"]
    text = json.dumps(plan, sort_keys=True).lower()
    steps = {item["name"] for item in plan["implementation_steps"]}
    tests = set(plan["required_tests"])
    return [
        _check("plan_selection_type", plan["selection_type"] == "residual_comfort_failure_diagnostic_remediation_implementation_plan_only"),
        _check("plan_selects_static_review", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_includes_screen_source", PLANNED_SCREEN_SOURCE in scope["planned_files"]),
        _check("plan_includes_route_test", PLANNED_ROUTE_TEST in scope["planned_files"]),
        _check("plan_includes_contract_test", PLANNED_CONTRACT_TEST in scope["planned_files"]),
        _check("plan_default_off", scope["default_off"] is True),
        _check("plan_report_only_until_execution_gate", scope["report_only_until_execution_gate"] is True),
        _check("plan_current_tick_finite", scope["current_tick_finite_candidate_features_only"] is True),
        _check("plan_preserves_candidate0", scope["preserve_candidate0"] is True),
        _check("plan_no_candidate_mutation", scope["no_candidate_mutation"] is True),
        _check("plan_no_selected_index_mutation", scope["no_selected_index_mutation"] is True),
        _check("plan_no_fallback_mutation", scope["no_fallback_mutation"] is True),
        _check("plan_no_online_selector_change", scope["no_online_selector_change"] is True),
        _check("plan_no_atom_schema_change", scope["no_deployed_atom_schema_change"] is True),
        _check("plan_no_dp_import", scope["no_dp_import"] is True),
        _check("plan_no_reward_recompute", scope["no_reward_recompute"] is True),
        _check("plan_no_tracker_recompute", scope["no_tracker_recompute"] is True),
        _check("plan_has_default_off_step", "default_off_config_pin" in steps),
        _check("plan_has_descriptor_step", "command_jerk_descriptor_payload" in steps),
        _check("plan_has_guardrail_step", "support_intervention_guardrails" in steps),
        _check("plan_has_tests_step", "contract_tests_before_execution" in steps),
        _check("plan_required_tests_present", len(tests) == 8),
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
        _check("boundary_authorizes_static_review", decision["remediation_implementation_static_contract_review_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_production_edit", decision["production_implementation_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_implementation_plan_ready": passed,
        "remediation_implementation_static_contract_review_authorized": passed,
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
