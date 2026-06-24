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
    / (
        "test_diffusion_planner_residual_comfort_remediation_followup_"
        "materially_different_generator_guarded_fixed_snapshot_screen_rerun_"
        "failure_attribution_remediation_implementation_contract.py"
    )
)

EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = (11, 12, 13)
MATERIAL_PROFILE_V2 = "lane_red_hard_feasible_jerk_lateral_support_v2"
MATERIAL_POLICY_V2 = "lane_red_hard_feasible_jerk_lateral_material_support"
IMPLEMENTATION_GATE = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_only"
)
CURRENT_GATE = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_post_implementation_static_contract_review_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_post_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_post_implementation_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_fixed_snapshot_screen_rerun_plan_only"
)
TAIL_BYTES = 60000

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
            "Read-only post-implementation static contract review for the "
            "material generator failure-attribution remediation v2."
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
            "name": (
                "dp_camp_material_generator_failure_attribution_remediation_"
                "post_implementation_static_contract_review_v1"
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
            "math_boundary": (
                "This review reads only repo-local audit, implementation, route "
                "test, and v2 implementation-contract text plus HEAD values. It "
                "does not edit production code, create candidates, execute a "
                "fixed-snapshot screen rerun, run DP, run replay, use formal "
                "seeds, define or promote runtime atoms, choose lambda online, "
                "alter score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 "
                "master, train CAMP, change online selection, modify DP "
                "weights/code/config, claim safety benefit, claim CAMP over DP "
                "Top-1, or claim a DP-side classical Benders decomposition."
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
        "# Material Generator Remediation Post-Implementation Static Contract Review",
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
    lines.extend(["", "## Route Test Baseline", ""])
    for name, passed in review["route_test_contract"]["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## V2 Contract Tests", ""])
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
    precheck_body = _function_body(source_text, "_lane_red_hard_feasibility_precheck")
    base_descriptor_body = _function_body(source_text, "_command_jerk_descriptor_payload")
    descriptor_body = _function_body(source_text, "_material_support_descriptor_payload")
    combined_descriptor_body = base_descriptor_body + "\n" + descriptor_body
    validate_body = _function_body(source_text, "_validate_config")
    profile_body = _function_body(source_text, "_material_support_profile_failure")
    budgets_body = _function_body(source_text, "_effective_comfort_budgets")
    return {
        "selection_type": CURRENT_GATE,
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "material_policy_v2": MATERIAL_POLICY_V2,
        "material_profile_v2": MATERIAL_PROFILE_V2,
        "source_contract": {
            "contracts": {
                "default_off_explicit_v2_pairing": _all_present(
                    source_text,
                    (
                        'REMEDIATION_PROFILE_OFF = "off"',
                        "default_off_remediation_profile: str = REMEDIATION_PROFILE_OFF",
                        "REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2",
                        "GENERATOR_POLICY_MATERIAL_SUPPORT_V2",
                        "MATERIAL_SUPPORT_POLICY_PROFILES",
                        MATERIAL_POLICY_V2,
                        MATERIAL_PROFILE_V2,
                    ),
                ),
                "profile_policy_mismatch_fails_closed": _all_present(
                    profile_body + "\n" + validate_body + "\n" + source_text,
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
                "v2_hard_precheck_fail_closed_without_gate_relaxation": _all_present(
                    source_text + "\n" + precheck_body,
                    (
                        "def _lane_red_hard_feasibility_precheck",
                        "red_ahead_margin_m",
                        "stop_distance_margin_m",
                        "forward_range_margin_m",
                        "kinematic_deceleration_margin_mps2",
                        "kinematic_deceleration_margin_negative",
                        "if _is_material_support_v2_policy(config):",
                        "continue",
                        "no_gate_relaxation",
                    ),
                ),
                "current_tick_finite_inputs_only": _all_present(
                    helper_body + "\n" + precheck_body,
                    (
                        "selected_arr",
                        "_project_points_to_lane",
                        "selected_forward",
                        "target_forward",
                        "np.maximum.accumulate",
                        "np.nan_to_num",
                        "current_speed_mps",
                        "uses_outcome_labels",
                    ),
                )
                and _all_absent(
                    helper_body + "\n" + precheck_body,
                    (
                        "_load_runtime",
                        "_score_trajectories",
                        "_tracker_delta",
                        "reward_config",
                        "snapshot",
                        "formal",
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
                "lateral_heading_continuity_projection": _all_present(
                    helper_body,
                    (
                        "_smoothstep",
                        "envelope[: int(prefix)] = 1.0",
                        "xy[: int(prefix)] = selected_arr[: int(prefix), :2]",
                        "heading_features_from_xy",
                        "fallback=selected_arr[:, 2:4]",
                    ),
                ),
                "descriptor_v2_legality_report_only": _all_present(
                    combined_descriptor_body,
                    (
                        "diagnostic_descriptor_payload_v2",
                        "lane_red_hard_feasible_jerk_lateral_material_support",
                        "hard_feasibility_margin_hinges",
                        "hard_feasibility_red_ahead_margin_m",
                        "hard_feasibility_stop_distance_margin_m",
                        "hard_feasibility_forward_range_margin_m",
                        "hard_feasibility_kinematic_deceleration_margin_mps2",
                        '"current_tick_features_only": True',
                        '"candidate_local": True',
                        '"uses_outcome_labels": False',
                        '"future_outcome_leakage": False',
                        '"runtime_atom_promotion": False',
                        '"nonnegative_descriptor_channels": True',
                        '"hinge_signed_split_channels": True',
                        '"affine_score_compatible": True',
                        '"score_contract": "score_k(w)=a_k^T w"',
                        '"convex_master_contract": "simplex/CVaR/L2 unchanged"',
                    ),
                )
                and _all_absent(
                    combined_descriptor_body,
                    (
                        "_load_runtime",
                        "_score_trajectories",
                        "_tracker_delta",
                        "reward_config",
                        "snapshot",
                    ),
                ),
                "support_floor_budget_contract_keeps_v1_and_v2": _all_present(
                    budgets_body,
                    (
                        "REMEDIATION_PROFILE_SUPPORT_V1",
                        "REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1",
                        "REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2",
                        "_budgets_with_floor",
                        "command_jerk_worse_budget_mps3",
                        "rollout_lateral_worse_budget_mps2",
                    ),
                ),
            },
        },
        "route_test_contract": {
            "contracts": {
                "baseline_route_topology_tests_present": _all_present(
                    route_test_text,
                    (
                        "test_route_topology_generator_builds_default_off_jerk_progress_policy",
                        "test_route_topology_generator_builds_negative_support_followup_policy",
                        "test_route_topology_report_rejects_invalid_remediation_candidate_cap",
                        "max_remediation_candidates must be positive",
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
                "v2_implementation_tests_present": _all_present(
                    contract_test_text,
                    (
                        "test_v2_default_off_and_v1_behavior_unchanged",
                        "test_v2_requires_explicit_policy_profile_pair",
                        "test_v2_preserves_candidate0_and_dp_rows_while_appending_support",
                        "test_v2_hard_precheck_fails_closed_on_kinematic_margin",
                        "test_v2_rejects_nonfinite_current_tick_inputs",
                        "test_v2_descriptor_legality_and_affine_contract",
                    ),
                ),
                "v2_tests_pin_boundary_tokens": _all_present(
                    contract_test_text,
                    (
                        "candidate0_preserved",
                        "dp_rows_preserved",
                        "lane_red_hard_feasibility_precheck",
                        "hard_feasibility_precheck_passed",
                        "no_gate_relaxation",
                        "diagnostic_descriptor_payload_v2",
                        "current_tick_features_only",
                        "uses_outcome_labels",
                        "future_outcome_leakage",
                        "hard_feasibility_margin_hinges",
                        "nonnegative_descriptor_channels",
                        "hinge_signed_split_channels",
                        "affine_score_compatible",
                        "score_k(w)=a_k^T w",
                        "simplex/CVaR/L2 unchanged",
                        "online_selector_feature",
                        "deployed_atom_schema_change",
                    ),
                ),
                "v2_tests_do_not_use_forbidden_execution": _all_absent(
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
        _check("audit_tail_present", bool(audit_tail)),
        _check("audit_records_implementation_gate", IMPLEMENTATION_GATE in audit_tail),
        _check("audit_authorizes_current_gate", CURRENT_GATE in audit_tail),
        _check(
            "audit_blocks_candidate_generation",
            "candidate_generation_execution_authorized=False" in audit_tail,
        ),
        _check(
            "audit_blocks_screen_rerun",
            "fixed_snapshot_screen_rerun_authorized=False" in audit_tail,
        ),
        _check(
            "audit_blocks_replay_training_promotion",
            "new_replay_authorized=False" in audit_tail
            and "training_execution_authorized=False" in audit_tail
            and "atom_promotion_authorized=False" in audit_tail,
        ),
        _check(
            "audit_blocks_dp_modification",
            "dp_modification_authorized=False" in audit_tail,
        ),
    ]


def _file_checks(
    name: str,
    path: Path,
    text: str | None,
) -> list[dict[str, Any]]:
    return [
        _check(f"{name}_exists", path.is_file()),
        _check(f"{name}_nonempty", bool(text)),
    ]


def _contract_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for group_name in (
        "source_contract",
        "route_test_contract",
        "contract_test_contract",
    ):
        for name, passed in review[group_name]["contracts"].items():
            checks.append(_check(f"{group_name}.{name}", bool(passed)))
    return checks


def _boundary_checks() -> list[dict[str, Any]]:
    return [
        _check("blocked_action_count", len(BLOCKED_ACTIONS) >= 18),
        _check("authorized_next_is_plan_only", AUTHORIZED_NEXT_WORK.endswith("_plan_only")),
        _check("formal_seeds_remain_11_12_13", FORMAL_SEEDS == (11, 12, 13)),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_post_implementation_static_contract_review_complete": passed,
        "remediation_fixed_snapshot_screen_rerun_plan_authorized": passed,
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


def _read_text_if_present(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _file_summary(path: Path, text: str | None) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text is not None
        else None,
        "bytes": len(text.encode("utf-8")) if text is not None else 0,
    }


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _all_present(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle in text for needle in needles)


def _all_absent(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle not in text for needle in needles)


def _function_body(source_text: str, function_name: str) -> str:
    marker = f"def {function_name}"
    start = source_text.find(marker)
    if start < 0:
        return ""
    next_def = source_text.find("\ndef ", start + len(marker))
    if next_def < 0:
        return source_text[start:]
    return source_text[start:next_def]


if __name__ == "__main__":
    main()
