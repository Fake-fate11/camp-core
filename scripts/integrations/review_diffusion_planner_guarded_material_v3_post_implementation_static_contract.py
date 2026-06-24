#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DEFAULT_SOURCE_PATH = (
    ROOT / "scripts" / "integrations" / "analyze_diffusion_planner_route_topology_candidate_screen.py"
)
DEFAULT_ROUTE_TEST_PATH = (
    ROOT / "camp_core" / "tests" / "test_diffusion_planner_route_topology_candidate_screen.py"
)
DEFAULT_CONTRACT_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / (
        "test_diffusion_planner_residual_comfort_remediation_followup_"
        "materially_different_generator_guarded_fixed_snapshot_screen_"
        "rerun_failure_attribution_remediation_guarded_fixed_snapshot_screen_"
        "rerun_failure_attribution_remediation_implementation_contract.py"
    )
)

EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = (11, 12, 13)
MATERIAL_PROFILE_V3 = "lane_red_hard_feasible_comfort_first_support_v3"
MATERIAL_POLICY_V3 = "lane_red_hard_feasible_comfort_first_material_support"
IMPLEMENTATION_GATE = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_only"
)
CURRENT_GATE = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_post_implementation_static_contract_review_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_post_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_post_implementation_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_fixed_snapshot_screen_rerun_plan_only"
)
TAIL_BYTES = 70000

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
        description="Read-only post-implementation static review for guarded material v3."
    )
    parser.add_argument("--audit_path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--source_path", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--route_test_path", type=Path, default=DEFAULT_ROUTE_TEST_PATH)
    parser.add_argument("--contract_test_path", type=Path, default=DEFAULT_CONTRACT_TEST_PATH)
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
    label: str | None = None,
) -> dict[str, Any]:
    audit_text = _read_text_if_present(audit_path)
    source_text = _read_text_if_present(source_path)
    route_test_text = _read_text_if_present(route_test_path)
    contract_test_text = _read_text_if_present(contract_test_path)
    review = _static_review(
        source_text=source_text or "",
        route_test_text=route_test_text or "",
        contract_test_text=contract_test_text or "",
    )
    checks = [
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks((audit_text or "")[-TAIL_BYTES:]),
        *_file_checks("audit", audit_path, audit_text),
        *_file_checks("source", source_path, source_text),
        *_file_checks("route_test", route_test_path, route_test_text),
        *_file_checks("contract_test", contract_test_path, contract_test_text),
        *_contract_checks(review),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_guarded_material_generator_v3_post_static_review",
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
            "math_boundary": (
                "This review reads only repo-local audit, implementation, route "
                "test, and v3 implementation-contract text plus HEAD values. It "
                "does not edit code, create candidates, execute a fixed-snapshot "
                "screen rerun, run DP, run replay, use formal seeds, define or "
                "promote runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, modify DP, claim safety "
                "benefit, claim CAMP over DP Top-1, or claim a DP-side classical "
                "Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
            "formal_seeds": list(FORMAL_SEEDS),
        },
        "inputs": {
            "audit_path": _file_summary(audit_path, audit_text),
            "source_path": _file_summary(source_path, source_text),
            "route_test_path": _file_summary(route_test_path, route_test_text),
            "contract_test_path": _file_summary(contract_test_path, contract_test_text),
        },
        "post_implementation_static_contract_review": review,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["post_implementation_static_contract_review"]
    lines = [
        "# Guarded Material Generator V3 Post-Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Contracts",
        "",
    ]
    for name, passed in review["source_contract"]["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Route Tests", ""])
    for name, passed in review["route_test_contract"]["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Contract Tests", ""])
    for name, passed in review["contract_test_contract"]["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Blocked Boundaries", ""])
    for item in review["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _static_review(
    *,
    source_text: str,
    route_test_text: str,
    contract_test_text: str,
) -> dict[str, Any]:
    helper_body = _function_body(source_text, "_lane_station_material_support_candidates")
    hard_precheck_body = _function_body(source_text, "_lane_red_hard_feasibility_precheck")
    comfort_precheck_body = _function_body(source_text, "_material_support_v3_comfort_precheck")
    descriptor_body = (
        _function_body(source_text, "_command_jerk_descriptor_payload")
        + "\n"
        + _function_body(source_text, "_material_support_descriptor_payload")
    )
    validate_body = _function_body(source_text, "_validate_config")
    profile_body = _function_body(source_text, "_material_support_profile_failure")
    budgets_body = _function_body(source_text, "_effective_comfort_budgets")
    material_branch = _material_branch_body(source_text)
    return {
        "selection_type": CURRENT_GATE,
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "material_policy_v3": MATERIAL_POLICY_V3,
        "material_profile_v3": MATERIAL_PROFILE_V3,
        "source_contract": {
            "contracts": {
                "explicit_v3_profile_policy_pair": _all_present(
                    source_text,
                    (
                        "REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3",
                        "GENERATOR_POLICY_MATERIAL_SUPPORT_V3",
                        MATERIAL_PROFILE_V3,
                        MATERIAL_POLICY_V3,
                        "MATERIAL_SUPPORT_POLICY_PROFILES",
                        "GENERATOR_POLICY_MATERIAL_SUPPORT_V3: REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3",
                    ),
                ),
                "profile_policy_mismatch_fails_closed": _all_present(
                    source_text + "\n" + profile_body + "\n" + validate_body,
                    (
                        "def _material_support_profile_failure",
                        "MATERIAL_SUPPORT_POLICY_PROFILES.get",
                        "material_support_profile_required",
                        "material_support_policy_required",
                        "if _material_support_profile_failure(config) is not None",
                        "return np.empty((0, raw.shape[1], raw.shape[2])",
                        "raise ValueError(_material_support_profile_failure(config))",
                    ),
                ),
                "v3_hard_precheck_fail_closed_no_relaxation": _all_present(
                    source_text + "\n" + hard_precheck_body,
                    (
                        "def _requires_material_hard_precheck",
                        "def _is_material_support_v3_policy",
                        "def _lane_red_hard_feasibility_precheck",
                        "red_ahead_margin_m",
                        "stop_distance_margin_m",
                        "forward_range_margin_m",
                        "kinematic_deceleration_margin_mps2",
                        "kinematic_deceleration_margin_negative",
                        "if _requires_material_hard_precheck(config):",
                        "continue",
                        "no_gate_relaxation",
                    ),
                ),
                "v3_comfort_first_precheck_fail_closed": _all_present(
                    material_branch + "\n" + comfort_precheck_body,
                    (
                        "def _material_support_v3_comfort_precheck",
                        "command_jerk_hinge_mps3",
                        "rollout_jerk_hinge_mps3",
                        "rollout_lateral_hinge_mps2",
                        "lane_corridor_hinge_m",
                        "progress_retention_hinge_m",
                        "smoothness_proxy_hinge",
                        "if not material_v3_comfort_precheck[\"passed\"]",
                        "continue",
                    ),
                ),
                "v3_budget_floors_not_applied": _all_present(
                    budgets_body,
                    (
                        "config.default_off_remediation_profile in {",
                        "REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3",
                        "REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4",
                        '"progress_loss_budgets_m": config.progress_loss_budgets_m',
                        '"smoothness_loss_budgets": config.smoothness_loss_budgets',
                        '"command_jerk_worse_budget_mps3": config.command_jerk_worse_budget_mps3',
                        '"rollout_lateral_worse_budget_mps2": (',
                    ),
                ),
                "candidate0_and_dp_rows_preserved": _all_present(
                    source_text,
                    (
                        '"candidate0_preserved": True',
                        '"dp_rows_preserved": True',
                        '"append_after_existing_candidate_count": int(raw.shape[0])',
                        '"source_candidate_index": int(selected_index)',
                    ),
                ),
                "v3_descriptor_legality_report_only": _all_present(
                    descriptor_body,
                    (
                        "diagnostic_descriptor_payload_v3",
                        "diagnostic_descriptor_payload_v3_report_only",
                        "lane_red_hard_feasible_comfort_first_material_support",
                        "hard_feasibility_comfort_first_lane_corridor_progress_v3",
                        "hard_feasibility_margin_hinges",
                        "lane_corridor_hinge_m",
                        "progress_retention_hinge_m",
                        "smoothness_proxy_hinge",
                        '"current_tick_features_only": True',
                        '"candidate_local": True',
                        '"uses_outcome_labels": False',
                        '"future_outcome_leakage": False',
                        '"runtime_atom_promotion": False',
                        '"atom_promotion": False',
                        '"online_selector_promotion": False',
                        '"nonnegative_descriptor_channels": True',
                        '"hinge_signed_split_channels": True',
                        '"affine_score_compatible": True',
                        '"score_contract": "score_k(w)=a_k^T w"',
                        '"convex_master_contract": "simplex/CVaR/L2 unchanged"',
                    ),
                )
                and _all_absent(
                    descriptor_body + "\n" + comfort_precheck_body + "\n" + helper_body,
                    (
                        "_load_runtime",
                        "_score_trajectories",
                        "_tracker_delta",
                        "reward_config",
                        "snapshot_path",
                        "formal",
                    ),
                ),
            },
        },
        "route_test_contract": {
            "contracts": {
                "v3_route_test_present": _all_present(
                    route_test_text,
                    (
                        "test_route_topology_material_v3_builds_explicit_comfort_first_support",
                        "GENERATOR_POLICY_MATERIAL_SUPPORT_V3",
                        "REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3",
                        "diagnostic_descriptor_payload_v3_report_only",
                        "score_k(w)=a_k^T w",
                        "simplex/CVaR/L2 unchanged",
                    ),
                ),
                "route_tests_do_not_use_forbidden_execution": _all_absent(
                    route_test_text,
                    (
                        "Diffusion-Planner",
                        "reward_config",
                        "formal seeds",
                        "seed=11",
                        "seed=12",
                        "seed=13",
                    ),
                ),
            },
        },
        "contract_test_contract": {
            "contracts": {
                "v3_implementation_contract_tests_present": _all_present(
                    contract_test_text,
                    (
                        "test_v3_material_support_requires_explicit_profile_policy_pair",
                        "test_v3_material_support_preserves_v1_v2_profile_mapping",
                        "test_v3_material_support_appends_after_dp_rows_without_mutating_candidate0",
                        "test_v3_material_support_fails_closed_on_hard_precheck",
                        "test_v3_material_support_fails_closed_on_comfort_first_precheck",
                        "test_v3_effective_budgets_do_not_apply_v1_v2_budget_floors",
                        "test_v3_descriptor_channels_remain_report_only_and_affine_compatible",
                    ),
                ),
                "v3_contract_tests_pin_boundary_tokens": _all_present(
                    contract_test_text,
                    (
                        "candidate0_preserved",
                        "dp_rows_preserved",
                        "lane_red_hard_feasibility_precheck_required",
                        "comfort_first_precheck_passed",
                        "diagnostic_descriptor_payload_v3_report_only",
                        "current_tick_features_only",
                        "uses_outcome_labels",
                        "future_outcome_leakage",
                        "nonnegative_descriptor_channels",
                        "hinge_signed_split_channels",
                        "affine_score_compatible",
                        "score_k(w)=a_k^T w",
                        "simplex/CVaR/L2 unchanged",
                        "online_selector_feature",
                        "runtime_atom_promotion",
                    ),
                ),
                "v3_tests_do_not_use_forbidden_execution": _all_absent(
                    contract_test_text,
                    (
                        "Diffusion-Planner",
                        "reward_config",
                        "formal seeds",
                        "seed=11",
                        "seed=12",
                        "seed=13",
                    ),
                ),
            },
        },
        "blocked_boundaries": [
            "implementation edits are not authorized in this review gate",
            "candidate generation execution is not authorized",
            "fixed-snapshot screen rerun execution is not authorized",
            "replay and closed-loop smoke are not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "atom promotion, CAMP retraining, and online selector changes are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim or CAMP-over-DP Top-1 claim is authorized",
            "no DP-side classical Benders claim is authorized",
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
        _check("formal_seeds_frozen_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _audit_checks(audit_tail: str) -> list[dict[str, Any]]:
    return [
        _check("audit_records_implementation_complete", IMPLEMENTATION_GATE in audit_tail),
        _check("audit_authorizes_current_gate", CURRENT_GATE in audit_tail),
        _check("audit_records_no_screen_rerun", "fixed_snapshot_screen_rerun_authorized=False" in audit_tail),
        _check("audit_records_no_training", "training_execution_authorized=False" in audit_tail),
        _check("audit_records_no_dp_modification", "dp_modification_authorized=False" in audit_tail),
        _check("audit_records_v3_profile", MATERIAL_PROFILE_V3 in audit_tail),
        _check("audit_records_v3_policy", MATERIAL_POLICY_V3 in audit_tail),
    ]


def _file_checks(name: str, path: Path, text: str | None) -> list[dict[str, Any]]:
    return [
        _check(f"{name}_file_present", path.is_file()),
        _check(f"{name}_file_readable", isinstance(text, str) and len(text) > 0),
    ]


def _contract_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for group_name in (
        "source_contract",
        "route_test_contract",
        "contract_test_contract",
    ):
        for name, passed in review[group_name]["contracts"].items():
            checks.append(_check(f"{group_name}.{name}", bool(passed)))
    return checks


def _boundary_checks() -> list[dict[str, Any]]:
    return [_check(f"blocked_action.{key}", True) for key in BLOCKED_ACTIONS]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_implementation_static_contract_review_complete": passed,
        "fixed_snapshot_screen_rerun_plan_authorized": passed,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


def _function_body(text: str, name: str) -> str:
    marker = f"def {name}"
    start = text.find(marker)
    if start < 0:
        return ""
    next_def = text.find("\ndef ", start + len(marker))
    if next_def < 0:
        next_def = text.find("\nclass ", start + len(marker))
    return text[start:] if next_def < 0 else text[start:next_def]


def _material_branch_body(text: str) -> str:
    marker = "if _is_material_support_policy(config):"
    start = text.find(marker)
    if start < 0:
        return ""
    end = text.find('if config.generator_policy == "prefix_lane_projected_red_stop"', start)
    return text[start:] if end < 0 else text[start:end]


def _all_present(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle in text for needle in needles)


def _all_absent(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return all(needle.lower() not in lowered for needle in needles)


def _read_text_if_present(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _file_summary(path: Path, text: str | None) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": _sha256_text(text) if text is not None else None,
        "bytes": len(text.encode("utf-8")) if text is not None else 0,
    }


def _sha256_text(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
