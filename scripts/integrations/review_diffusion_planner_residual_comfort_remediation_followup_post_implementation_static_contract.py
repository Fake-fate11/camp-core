#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "analyze_diffusion_planner_route_topology_candidate_screen.py"
)
DEFAULT_ROUTE_TEST_PATH = (
    ROOT / "camp_core" / "tests" / "test_diffusion_planner_route_topology_candidate_screen.py"
)
DEFAULT_CONTRACT_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_residual_comfort_remediation_followup_implementation_contract.py"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = (11, 12, 13)
IMPLEMENTATION_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_implementation_"
    "complete"
)
CURRENT_GATE = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_post_"
    "implementation_static_contract_review_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_post_"
    "implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_post_"
    "implementation_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_fixed_snapshot_"
    "screen_rerun_plan_only"
)
TAIL_BYTES = 36000

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
            "Read-only post-implementation static contract review for residual "
            "comfort remediation follow-up."
        )
    )
    parser.add_argument("--audit_path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--source_path", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--route_test_path", type=Path, default=DEFAULT_ROUTE_TEST_PATH)
    parser.add_argument(
        "--contract_test_path",
        type=Path,
        default=DEFAULT_CONTRACT_TEST_PATH,
    )
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
        audit_path=args.audit_path,
        source_path=args.source_path,
        route_test_path=args.route_test_path,
        contract_test_path=args.contract_test_path,
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
    audit_path: Path,
    source_path: Path,
    route_test_path: Path,
    contract_test_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    audit_text = _read_text(audit_path)
    source_text = _read_text(source_path)
    route_test_text = _read_text(route_test_path)
    contract_test_text = _read_text(contract_test_path)
    audit_tail = audit_text[-TAIL_BYTES:]
    descriptor_body = _function_body(source_text, "_command_jerk_descriptor_payload")
    comfort_admissible_body = _function_body(source_text, "_comfort_admissible")
    comfort_failure_body = _function_body(source_text, "_comfort_failure_classes")
    validate_body = _function_body(source_text, "_validate_config")
    review = _static_review(
        source_text=source_text,
        route_test_text=route_test_text,
        contract_test_text=contract_test_text,
        descriptor_body=descriptor_body,
        comfort_admissible_body=comfort_admissible_body,
        comfort_failure_body=comfort_failure_body,
        validate_body=validate_body,
    )
    checks = [
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_tail),
        *_source_checks(review["source_contract"]),
        *_route_test_checks(review["route_test_contract"]),
        *_contract_test_checks(review["contract_test_contract"]),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_followup_post_implementation_static_review_v1"
            ),
            "label": label,
            "role": "read-only post-implementation static contract review",
            "read_only": True,
            "source_inspection_only": True,
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
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
            "formal_seeds": list(FORMAL_SEEDS),
        },
        "inputs": {
            "audit_path": _file_summary(audit_path),
            "source_path": _file_summary(source_path),
            "route_test_path": _file_summary(route_test_path),
            "contract_test_path": _file_summary(contract_test_path),
        },
        "static_contract_review": review,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# Residual Comfort Remediation Follow-Up Post-Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Findings",
        "",
    ]
    for item in review["findings"]:
        lines.append(f"- `{item['name']}`: {item['finding']}")
    lines.extend(["", "## Boundary", ""])
    lines.append(
        "DP remains a fixed black-box candidate generator; this review does not "
        "authorize rerun, replay, formal seeds, Full36, promotion, or training."
    )
    return "\n".join(lines)


def _static_review(
    *,
    source_text: str,
    route_test_text: str,
    contract_test_text: str,
    descriptor_body: str,
    comfort_admissible_body: str,
    comfort_failure_body: str,
    validate_body: str,
) -> dict[str, Any]:
    source_contract = {
        "default_profile_constant": 'REMEDIATION_PROFILE_OFF = "off"' in source_text,
        "support_profile_constant": (
            'REMEDIATION_PROFILE_SUPPORT_V1 = "lane_projected_jerk_progress_support_v1"'
            in source_text
        ),
        "config_profile_default_off": (
            "default_off_remediation_profile: str = REMEDIATION_PROFILE_OFF"
            in source_text
        ),
        "cli_profile_arg": "--default_off_remediation_profile" in source_text,
        "effective_budgets_reported": '"effective_comfort_budgets"' in source_text,
        "effective_budget_helper": "def _effective_comfort_budgets" in source_text,
        "admissible_uses_effective_budgets": (
            "_effective_comfort_budgets(config)" in comfort_admissible_body
            and 'budgets["command_jerk_worse_budget_mps3"]'
            in comfort_admissible_body
            and 'budgets["rollout_lateral_worse_budget_mps2"]'
            in comfort_admissible_body
        ),
        "failure_classes_use_effective_budgets": (
            "_effective_comfort_budgets(config)" in comfort_failure_body
            and "route_topology_comfort_blocked_rollout_lateral"
            in comfort_failure_body
        ),
        "invalid_profile_fails_closed": (
            "default_off_remediation_profile" in validate_body
            and "REMEDIATION_PROFILE_SUPPORT_V1" in validate_body
            and "ValueError" in validate_body
        ),
        "descriptor_keeps_legacy_family": (
            '"payload_role": "report_only_current_tick_descriptor"' in descriptor_body
            and '"descriptor_family": "command_jerk_hinge"' in descriptor_body
        ),
        "descriptor_adds_followup_family": (
            '"followup_payload_role": "report_only"' in descriptor_body
            and '"followup_descriptor_family": '
            '"command_jerk_rollout_lateral_zero_comfort_gap"' in descriptor_body
        ),
        "descriptor_uses_current_tick_candidate_local": (
            '"current_tick_features_only": True' in descriptor_body
            and '"candidate_local": True' in descriptor_body
            and '"uses_outcome_labels": False' in descriptor_body
            and '"future_outcome_leakage": False' in descriptor_body
        ),
        "descriptor_terms_nonnegative_legal": (
            "command_jerk_hinge_mps3" in descriptor_body
            and "command_jerk_signed_pos_mps3" in descriptor_body
            and "command_jerk_signed_neg_mps3" in descriptor_body
            and "rollout_lateral_hinge_mps2" in descriptor_body
            and "rollout_lateral_signed_pos_mps2" in descriptor_body
            and "rollout_lateral_signed_neg_mps2" in descriptor_body
            and '"nonnegative_or_hinge_signed_split_legal": True' in descriptor_body
        ),
        "descriptor_preserves_math_contract": (
            '"score_contract": "score_k(w)=a_k^T w"' in descriptor_body
            and '"convex_master_contract": "simplex/CVaR/L2 unchanged"'
            in descriptor_body
        ),
        "descriptor_preserves_online_surface": all(
            token in descriptor_body
            for token in (
                '"candidate_mutation": False',
                '"score_mutation": False',
                '"selected_index_mutation": False',
                '"fallback_mutation": False',
                '"online_selector_feature": False',
                '"deployed_atom_schema_change": False',
            )
        ),
        "descriptor_does_not_call_reward_or_tracker": (
            "_score_trajectories" not in descriptor_body
            and "_tracker_delta" not in descriptor_body
        ),
    }
    route_test_contract = {
        "negative_support_policy_tests_present": (
            "test_route_topology_generator_builds_negative_support_followup_policy"
            in route_test_text
        ),
        "comfort_first_policy_tests_present": (
            "test_route_topology_generator_builds_comfort_first_remediation_policy"
            in route_test_text
        ),
        "candidate_budget_cap_pinned": "candidate_budget_cap" in route_test_text,
        "invalid_cap_rejected": (
            "test_route_topology_report_rejects_invalid_remediation_candidate_cap"
            in route_test_text
            and "max_remediation_candidates must be positive" in route_test_text
        ),
    }
    contract_test_contract = {
        "followup_family_pinned": (
            "command_jerk_rollout_lateral_zero_comfort_gap" in contract_test_text
        ),
        "no_surface_mutation_pinned": (
            "_assert_no_surface_mutation" in contract_test_text
            and "score_mutation" in contract_test_text
        ),
        "current_tick_candidate_local_pinned": (
            "current_tick_features_only" in contract_test_text
            and "candidate_local" in contract_test_text
            and "future_outcome_leakage" in contract_test_text
        ),
        "hinge_signed_split_pinned": (
            "command_jerk_signed_pos_mps3" in contract_test_text
            and "rollout_lateral_signed_neg_mps2" in contract_test_text
        ),
        "affine_convex_contract_pinned": (
            "score_k(w)=a_k^T w" in contract_test_text
            and "simplex/CVaR/L2 master unchanged" in contract_test_text
        ),
        "blocked_actions_pinned": (
            "training_execution_authorized" in contract_test_text
            and "dp_modification_authorized" in contract_test_text
            and "formal_seeds_authorized" in contract_test_text
        ),
    }
    return {
        "selection_type": "residual_comfort_remediation_followup_post_implementation_static_review_only",
        "source_contract": source_contract,
        "route_test_contract": route_test_contract,
        "contract_test_contract": contract_test_contract,
        "findings": [
            {
                "name": "default_off_profile_contract",
                "finding": "default path is off and support profile is explicit opt-in",
            },
            {
                "name": "effective_budget_contract",
                "finding": "admissibility, failure labels, and reports use effective budgets",
            },
            {
                "name": "descriptor_payload_contract",
                "finding": "legacy command-jerk fields are preserved and follow-up command-jerk/rollout-lateral fields are report-only",
            },
            {
                "name": "math_boundary_contract",
                "finding": "descriptor terms preserve affine scoring and convex master assumptions",
            },
            {
                "name": "execution_boundary_contract",
                "finding": "review remains static and blocks rerun, replay, formal seeds, training, promotion, claims, and DP modification",
            },
        ],
    }


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_tail: str) -> list[dict[str, Any]]:
    return [
        _check("audit_tail_records_implementation_complete", IMPLEMENTATION_READY_STATUS in audit_tail),
        _check("audit_tail_authorizes_current_gate", CURRENT_GATE in audit_tail),
        _check("audit_tail_blocks_screen_rerun", "fixed_snapshot_screen_rerun_authorized=False" in audit_tail),
        _check("audit_tail_blocks_training", "training_execution_authorized=False" in audit_tail),
        _check("audit_tail_blocks_dp_modification", "dp_modification_authorized=False" in audit_tail),
    ]


def _source_checks(contract: dict[str, bool]) -> list[dict[str, Any]]:
    return [
        _check(f"source_contract_{name}", passed)
        for name, passed in contract.items()
    ]


def _route_test_checks(contract: dict[str, bool]) -> list[dict[str, Any]]:
    return [
        _check(f"route_test_contract_{name}", passed)
        for name, passed in contract.items()
    ]


def _contract_test_checks(contract: dict[str, bool]) -> list[dict[str, Any]]:
    return [
        _check(f"contract_test_contract_{name}", passed)
        for name, passed in contract.items()
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_plan_only", decision["fixed_snapshot_screen_rerun_plan_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_full36", decision["full36_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_blocks_claims", decision["safety_benefit_claim_authorized"] is False and decision["camp_over_dp_top1_claim_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_implementation_static_contract_review_complete": passed,
        "fixed_snapshot_screen_rerun_plan_authorized": passed,
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


def _function_body(text: str, name: str) -> str:
    marker = f"def {name}"
    start = text.find(marker)
    if start < 0:
        return ""
    next_def = text.find("\ndef ", start + len(marker))
    next_class = text.find("\nclass ", start + len(marker))
    ends = [idx for idx in (next_def, next_class) if idx >= 0]
    end = min(ends) if ends else len(text)
    return text[start:end]


def _file_summary(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
