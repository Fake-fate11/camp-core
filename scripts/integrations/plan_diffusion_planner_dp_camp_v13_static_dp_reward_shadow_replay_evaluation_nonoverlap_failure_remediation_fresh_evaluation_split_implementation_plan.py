#!/usr/bin/env python3
"""Plan implementation for the v13 fresh evaluation split.

This gate is plan-only. It consumes the completed fresh evaluation split static
contract review and defines a future implementation plan for a fresh split
manifest builder. It does not implement the builder, run replay, generate fixed
DP candidates, train CAMP, modify Diffusion Planner, promote artifacts, deploy,
or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_static_contract_review_v1"
)
SOURCE_REVIEW_PASS_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_static_contract_review_passed"
)
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_"
    "artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_"
    "fresh_evaluation_split_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_implementation_static_contract_review_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
FUTURE_BUILDER_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_manifest.py"
)
FUTURE_BUILDER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_manifest_builder.py"
)

BLOCKED_SOURCE_FLAGS = (
    "implementation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)

REQUIRED_CONTRACT_GROUPS = (
    "future_scope_contract",
    "full_registry_nonoverlap_contract",
    "forbidden_source_exclusion_contract",
    "fixed_dp_default_off_runtime_boundary_contract",
    "affine_simplex_math_boundary_contract",
    "no_action_authorization_beyond_next_implementation_plan_gate",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan-only implementation plan for a fresh v13 evaluation split."
    )
    parser.add_argument("--static_contract_review_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        static_contract_review_json=args.static_contract_review_json,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    static_contract_review_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    static_contract_review_json = static_contract_review_json.resolve()
    v13_audit_md = v13_audit_md.resolve()
    source_review = _load_json_dict(static_contract_review_json)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(source_review)
    implementation_plan = _implementation_plan(source_review)
    checks = _checks(
        static_contract_review_json=static_contract_review_json,
        v13_audit_md=v13_audit_md,
        source_review=source_review,
        audit_text=audit_text,
        source_summary=source_summary,
        implementation_plan=implementation_plan,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "implementation_execution": False,
            "data_preparation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "deployable_checkpoint_claim": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "static_contract_review_json": str(static_contract_review_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "static_contract_review_json_sha256": _sha256(static_contract_review_json),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "implementation_plan": implementation_plan,
        "future_static_contract_review_requirements": _future_static_review_requirements(),
        "forbidden_paths": _forbidden_paths(),
        "plan_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "fresh_evaluation_split_implementation_plan_ready": passed,
            "fresh_evaluation_split_implementation_static_contract_review_authorized_next": passed,
            "implementation_authorized_next": False,
            "data_preparation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report["final_decision"])
    plan = _dict(report["implementation_plan"])
    lines = [
        "# V13 Fresh Evaluation Split Implementation Plan",
        "",
        f"- schema_version: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failed_checks: `{decision['failed_checks']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- implementation_authorized_next: `{decision['implementation_authorized_next']}`",
        f"- replay_execution_authorized_next: `{decision['replay_execution_authorized_next']}`",
        f"- fixed_dp_candidate_generation_authorized_next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- source_status: `{report['source_summary']['status']}`",
        f"- future_builder_script: `{plan['future_builder_script']}`",
        f"- future_builder_test: `{plan['future_builder_test']}`",
        "",
        "## Required Future Builder Behavior",
        "",
    ]
    for item in plan["required_future_builder_behavior"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Future Static Review Requirements", ""])
    for item in report["future_static_contract_review_requirements"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report["forbidden_paths"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It does not implement the builder, run replay, generate fixed-DP candidates, train CAMP, modify DP, promote, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    analysis = _dict(source_review.get("analysis"))
    contract = _dict(source_review.get("static_contract_review"))
    plan_summary = _dict(source_review.get("plan_summary"))
    future_scope = _dict(contract.get("future_scope_contract"))
    math_boundary = _dict(contract.get("math_boundary"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "fresh_evaluation_split_implementation_plan_authorized_next": decision.get(
            "fresh_evaluation_split_implementation_plan_authorized_next"
        ),
        "implementation_authorized_next": decision.get("implementation_authorized_next"),
        "training_preflight_authorized_next": decision.get("training_preflight_authorized_next"),
        "training_execution_authorized_next": decision.get("training_execution_authorized_next"),
        "replay_execution_authorized_next": decision.get("replay_execution_authorized_next"),
        "fixed_dp_candidate_generation_authorized_next": decision.get(
            "fixed_dp_candidate_generation_authorized_next"
        ),
        "candidate_generation_by_camp_authorized": decision.get(
            "candidate_generation_by_camp_authorized"
        ),
        "trajectory_generation_by_camp_authorized": decision.get(
            "trajectory_generation_by_camp_authorized"
        ),
        "trajectory_modification_by_camp_authorized": decision.get(
            "trajectory_modification_by_camp_authorized"
        ),
        "dp_modification_authorized": decision.get("dp_modification_authorized"),
        "selector_promotion_authorized": decision.get("selector_promotion_authorized"),
        "atom_promotion_authorized": decision.get("atom_promotion_authorized"),
        "deployment_authorized": decision.get("deployment_authorized"),
        "deployable_checkpoint_claim_authorized": decision.get(
            "deployable_checkpoint_claim_authorized"
        ),
        "safety_benefit_claim_authorized": decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": decision.get(
            "camp_over_dp_top1_claim_authorized"
        ),
        "future_selection_log_count": future_scope.get("selection_log_count"),
        "future_record_count": future_scope.get("record_count"),
        "future_candidate_count": future_scope.get("candidate_count"),
        "future_atom_count": future_scope.get("atom_count"),
        "future_routes_minimum": future_scope.get("routes_minimum"),
        "future_seeds_minimum": future_scope.get("seeds_minimum"),
        "future_route_traffic_light_buckets_minimum": future_scope.get(
            "route_traffic_light_buckets_minimum"
        ),
        "future_formal_seeds_excluded": future_scope.get("formal_seeds_11_12_13_excluded"),
        "future_full36_excluded": future_scope.get("full36_excluded"),
        "required_contract_groups": contract.get("required_contract_groups"),
        "source_plan_status": plan_summary.get("status"),
        "source_record_identity_intersection_count": plan_summary.get(
            "source_record_identity_intersection_count"
        ),
        "source_candidate_tensor_eval_hashes_in_previous_rate": plan_summary.get(
            "source_candidate_tensor_eval_hashes_in_previous_rate"
        ),
        "candidate_operation": analysis.get("candidate_operation"),
        "score_expression": analysis.get("score_expression"),
        "math_score_expression": math_boundary.get("score_expression"),
        "nonnegative_simplex_weights_only": math_boundary.get(
            "nonnegative_simplex_weights_only"
        ),
    }


def _implementation_plan(source_review: dict[str, Any]) -> dict[str, Any]:
    source_summary = _source_summary(source_review)
    return {
        "implementation_performed_by_this_gate": False,
        "future_builder_script": FUTURE_BUILDER_SCRIPT,
        "future_builder_test": FUTURE_BUILDER_TEST,
        "future_artifacts": [
            "fresh_evaluation_split_scope_manifest.json",
            "fresh_evaluation_split_nonoverlap_registry_report.json",
            "run_fresh_evaluation_split_preflight.sh",
            "SHA256SUMS.txt",
        ],
        "required_future_builder_behavior": [
            "load_full_76c2_training_manifest_before_selecting_any_split_member",
            "load_recovered_missing_prior_registry_before_selecting_any_split_member",
            "load_rejected_evaluation_source_registry_before_selecting_any_split_member",
            "fail_closed_when_any_required_registry_is_missing_or_empty",
            "prove_zero_candidate_tensor_hash_intersection",
            "prove_zero_path_signature_intersection",
            "prove_zero_record_identity_intersection",
            "prove_zero_split_manifest_root_intersection",
            "exclude_formal_seeds_11_12_13_and_full36",
            "require_default_off_shadow_selector_and_executed_dp_top1",
            "forbid_camp_candidate_generation_or_trajectory_modification",
            "forbid_reference_blend_guidance_postprocess_postselection",
            "forbid_closed_loop_outcomes_as_training_or_online_input",
            "write_immutable_sha256_manifest_for_all_outputs",
        ],
        "future_scope_contract": {
            "selection_log_count": source_summary["future_selection_log_count"],
            "record_count": source_summary["future_record_count"],
            "candidate_count": source_summary["future_candidate_count"],
            "atom_count": source_summary["future_atom_count"],
            "routes_minimum": source_summary["future_routes_minimum"],
            "seeds_minimum": source_summary["future_seeds_minimum"],
            "route_traffic_light_buckets_minimum": source_summary[
                "future_route_traffic_light_buckets_minimum"
            ],
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
        },
        "next_gate": "fresh_evaluation_split_implementation_static_contract_review_only",
    }


def _future_static_review_requirements() -> list[str]:
    return [
        "reject_if_builder_implementation_is_included_in_plan_gate",
        "reject_if_any_required_registry_check_is_missing",
        "reject_if_zero_intersection_checks_do_not_cover_candidate_path_record_and_split_root",
        "reject_if_formal_seed_or_full36_scope_is_authorized",
        "reject_if_replay_or_fixed_dp_candidate_generation_is_authorized",
        "reject_if_camp_candidate_generation_or_trajectory_modification_is_possible",
        "reject_if_dp_code_config_or_weight_changes_are_authorized",
        "reject_if_reference_blend_guidance_postprocess_or_postselection_is_allowed",
        "reject_if_closed_loop_outcomes_are_used_as_training_or_online_inputs",
        "reject_if_score_is_not_affine_or_weights_are_not_nonnegative_simplex",
        "reject_if_promotion_deployment_or_safety_claims_are_authorized",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "implementation_code_edit_by_this_gate",
        "fresh_split_preflight_execution_by_this_gate",
        "replay_execution_by_this_gate",
        "fixed_dp_candidate_generation_execution_by_this_gate",
        "camp_candidate_generation_or_trajectory_modification",
        "diffusion_planner_code_config_or_weight_change",
        "selector_or_atom_promotion",
        "deployment_or_deployable_checkpoint_claim",
        "safety_benefit_or_camp_over_dp_top1_claim",
    ]


def _checks(
    *,
    static_contract_review_json: Path,
    v13_audit_md: Path,
    source_review: dict[str, Any],
    audit_text: str,
    source_summary: dict[str, Any],
    implementation_plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    latest_status = _latest_value(audit_text, "current_v13_status")
    latest_target = _latest_value(audit_text, "next_work_target")
    return [
        _check("static_contract_review_json_exists", static_contract_review_json.is_file()),
        _check("v13_audit_md_exists", v13_audit_md.is_file()),
        _check("source_schema_version_expected", source_review.get("schema_version") == SOURCE_REVIEW_SCHEMA_VERSION),
        _check("source_status_expected", source_summary["status"] == SOURCE_REVIEW_PASS_STATUS),
        _check("source_passed", source_summary["passed"] is True),
        _check("source_failed_checks_empty", source_summary["failed_checks"] == []),
        _check(
            "source_authorizes_this_plan",
            source_summary["authorized_next_work"] == authorized_current_work,
        ),
        _check(
            "source_authorizes_implementation_plan_only",
            source_summary["fresh_evaluation_split_implementation_plan_authorized_next"]
            is True,
        ),
        _check(
            "source_blocked_action_flags_false",
            all(source_summary.get(flag) is False for flag in BLOCKED_SOURCE_FLAGS),
            {flag: source_summary.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
        ),
        _check("latest_audit_status_authorizes_plan", latest_status == LATEST_AUDIT_STATUS, latest_status),
        _check("latest_audit_target_authorizes_plan", latest_target == authorized_current_work, latest_target),
        _check("camp_head_matches_origin", current_camp_head == current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD),
        _check(
            "source_contract_groups_complete",
            set(REQUIRED_CONTRACT_GROUPS)
            <= set(_list(source_summary["required_contract_groups"])),
            source_summary["required_contract_groups"],
        ),
        _check(
            "future_scope_counts_expected",
            source_summary["future_selection_log_count"] == 32
            and source_summary["future_record_count"] == 3200
            and source_summary["future_candidate_count"] == 8
            and source_summary["future_atom_count"] == 14,
        ),
        _check(
            "future_scope_coverage_expected",
            source_summary["future_routes_minimum"] >= 4
            and source_summary["future_seeds_minimum"] >= 2
            and source_summary["future_route_traffic_light_buckets_minimum"] >= 8,
        ),
        _check(
            "future_scope_excludes_formal_and_full36",
            source_summary["future_formal_seeds_excluded"] is True
            and source_summary["future_full36_excluded"] is True,
        ),
        _check("source_plan_status_ready", source_summary["source_plan_status"] is not None),
        _check(
            "source_overlap_evidence_preserved",
            source_summary["source_record_identity_intersection_count"] == 3200
            and source_summary["source_candidate_tensor_eval_hashes_in_previous_rate"] == 1.0,
        ),
        _check(
            "source_math_boundary_affine_simplex",
            source_summary["candidate_operation"] == "fixed DP candidate reranking only"
            and source_summary["score_expression"] == SCORE_EXPRESSION
            and source_summary["math_score_expression"] == SCORE_EXPRESSION
            and source_summary["nonnegative_simplex_weights_only"] is True,
        ),
        _check(
            "implementation_plan_is_plan_only",
            implementation_plan["implementation_performed_by_this_gate"] is False
            and implementation_plan["next_gate"]
            == "fresh_evaluation_split_implementation_static_contract_review_only",
        ),
    ]


def _check(name: str, passed: bool, detail: Any | None = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
