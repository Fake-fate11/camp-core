#!/usr/bin/env python3
"""Static contract review for the v13 fresh split implementation plan.

This is a read-only review gate. It consumes the fresh evaluation split
implementation-plan artifact and verifies that the future implementation is
limited to a manifest builder for a fresh fixed-DP evaluation split. It does not
implement the builder, run replay, generate candidates, train CAMP, modify
Diffusion Planner, promote artifacts, deploy, or make safety/CAMP-over-DP
claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_plan_v1"
)
SOURCE_PLAN_READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_"
    "artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_"
    "fresh_evaluation_split_implementation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_implementation_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_FUTURE_BUILDER_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_manifest.py"
)
EXPECTED_FUTURE_BUILDER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_manifest_builder.py"
)

REQUIRED_BEHAVIOR = (
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
)

BLOCKED_SOURCE_FLAGS = (
    "implementation_authorized_next",
    "data_preparation_authorized_next",
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only static review for the v13 fresh split implementation plan."
    )
    parser.add_argument("--implementation_plan_json", type=Path, required=True)
    parser.add_argument("--implementation_plan_script_py", type=Path, required=True)
    parser.add_argument("--implementation_plan_test_py", type=Path, required=True)
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
        implementation_plan_json=args.implementation_plan_json,
        implementation_plan_script_py=args.implementation_plan_script_py,
        implementation_plan_test_py=args.implementation_plan_test_py,
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
    implementation_plan_json: Path,
    implementation_plan_script_py: Path,
    implementation_plan_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    implementation_plan_json = implementation_plan_json.resolve()
    implementation_plan_script_py = implementation_plan_script_py.resolve()
    implementation_plan_test_py = implementation_plan_test_py.resolve()
    v13_audit_md = v13_audit_md.resolve()

    source_plan = _load_json_dict(implementation_plan_json)
    implementation_plan_script_text = _read_text(implementation_plan_script_py)
    implementation_plan_test_text = _read_text(implementation_plan_test_py)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(source_plan)
    review = _static_review(source_plan)
    checks = _checks(
        implementation_plan_json=implementation_plan_json,
        implementation_plan_script_py=implementation_plan_script_py,
        implementation_plan_test_py=implementation_plan_test_py,
        v13_audit_md=v13_audit_md,
        source_plan=source_plan,
        source_summary=source_summary,
        review=review,
        implementation_plan_script_text=implementation_plan_script_text,
        implementation_plan_test_text=implementation_plan_test_text,
        audit_text=audit_text,
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
            "read_only": True,
            "static_contract_review_only": True,
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
            "implementation_plan_json": str(implementation_plan_json),
            "implementation_plan_script_py": str(implementation_plan_script_py),
            "implementation_plan_test_py": str(implementation_plan_test_py),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "implementation_plan_json_sha256": _sha256(implementation_plan_json),
            "implementation_plan_script_py_sha256": _sha256(implementation_plan_script_py),
            "implementation_plan_test_py_sha256": _sha256(implementation_plan_test_py),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "static_contract_review": review,
        "review_checks": checks,
        "final_decision": {
            "status": PASS_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "fresh_evaluation_split_implementation_authorized_next": passed,
            "implementation_authorized_next": passed,
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
    review = _dict(report["static_contract_review"])
    lines = [
        "# V13 Fresh Evaluation Split Implementation Static Contract Review",
        "",
        f"- schema_version: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failed_checks: `{decision['failed_checks']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- implementation_authorized_next: `{decision['implementation_authorized_next']}`",
        f"- replay_execution_authorized_next: `{decision['replay_execution_authorized_next']}`",
        f"- fixed_dp_candidate_generation_authorized_next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- future_builder_script: `{review['future_builder_script']}`",
        f"- future_builder_test: `{review['future_builder_test']}`",
        "",
        "## Required Behavior",
        "",
    ]
    for item in review["required_behavior"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Checks", ""])
    for check in report["review_checks"]:
        suffix = f" ({check['detail']})" if check.get("detail") is not None else ""
        lines.append(f"- {check['name']}: {check['passed']}{suffix}")
    lines.append("")
    return "\n".join(lines)


def _source_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("implementation_plan"))
    future_scope = _dict(plan.get("future_scope_contract"))
    math = _dict(plan.get("math_boundary"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_ready": decision.get(
            "fresh_evaluation_split_implementation_plan_ready"
        ),
        "implementation_static_contract_review_authorized_next": decision.get(
            "fresh_evaluation_split_implementation_static_contract_review_authorized_next"
        ),
        **{flag: decision.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
        "implementation_performed_by_this_gate": plan.get(
            "implementation_performed_by_this_gate"
        ),
        "future_builder_script": plan.get("future_builder_script"),
        "future_builder_test": plan.get("future_builder_test"),
        "required_future_builder_behavior": plan.get("required_future_builder_behavior"),
        "future_selection_log_count": future_scope.get("selection_log_count"),
        "future_record_count": future_scope.get("record_count"),
        "future_candidate_count": future_scope.get("candidate_count"),
        "future_atom_count": future_scope.get("atom_count"),
        "score_expression": math.get("score_expression"),
        "candidate_operation": math.get("candidate_operation"),
        "nonnegative_simplex_weights_only": math.get("nonnegative_simplex_weights_only"),
    }


def _static_review(source_plan: dict[str, Any]) -> dict[str, Any]:
    source = _source_summary(source_plan)
    return {
        "future_builder_script": source["future_builder_script"],
        "future_builder_test": source["future_builder_test"],
        "required_behavior": _list(source["required_future_builder_behavior"]),
        "future_scope_contract": {
            "selection_log_count": source["future_selection_log_count"],
            "record_count": source["future_record_count"],
            "candidate_count": source["future_candidate_count"],
            "atom_count": source["future_atom_count"],
        },
        "math_boundary": {
            "candidate_operation": source["candidate_operation"],
            "score_expression": source["score_expression"],
            "nonnegative_simplex_weights_only": source["nonnegative_simplex_weights_only"],
        },
    }


def _checks(
    *,
    implementation_plan_json: Path,
    implementation_plan_script_py: Path,
    implementation_plan_test_py: Path,
    v13_audit_md: Path,
    source_plan: dict[str, Any],
    source_summary: dict[str, Any],
    review: dict[str, Any],
    implementation_plan_script_text: str,
    implementation_plan_test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    latest_status = _latest_value(audit_text, "current_v13_status")
    latest_target = _latest_value(audit_text, "next_work_target")
    behavior = set(review["required_behavior"])
    return [
        _check("implementation_plan_json_exists", implementation_plan_json.is_file()),
        _check("implementation_plan_script_exists", implementation_plan_script_py.is_file()),
        _check("implementation_plan_test_exists", implementation_plan_test_py.is_file()),
        _check("v13_audit_md_exists", v13_audit_md.is_file()),
        _check("source_schema_version_expected", source_plan.get("schema_version") == SOURCE_PLAN_SCHEMA_VERSION),
        _check("source_status_expected", source_summary["status"] == SOURCE_PLAN_READY_STATUS),
        _check("source_passed", source_summary["passed"] is True),
        _check("source_failed_checks_empty", source_summary["failed_checks"] == []),
        _check(
            "source_authorizes_this_static_review",
            source_summary["authorized_next_work"] == authorized_current_work,
        ),
        _check("source_plan_ready", source_summary["implementation_plan_ready"] is True),
        _check(
            "source_static_review_authorized_next",
            source_summary["implementation_static_contract_review_authorized_next"] is True,
        ),
        _check(
            "source_blocked_action_flags_false",
            all(source_summary.get(flag) is False for flag in BLOCKED_SOURCE_FLAGS),
            {flag: source_summary.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
        ),
        _check(
            "latest_audit_status_authorizes_static_review",
            latest_status == LATEST_AUDIT_STATUS,
            latest_status,
        ),
        _check(
            "latest_audit_target_authorizes_static_review",
            latest_target == authorized_current_work,
            latest_target,
        ),
        _check("camp_head_matches_origin", current_camp_head == current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD),
        _check("source_plan_did_not_implement", source_summary["implementation_performed_by_this_gate"] is False),
        _check("future_builder_script_expected", review["future_builder_script"] == EXPECTED_FUTURE_BUILDER_SCRIPT),
        _check("future_builder_test_expected", review["future_builder_test"] == EXPECTED_FUTURE_BUILDER_TEST),
        _check("all_required_behavior_present", set(REQUIRED_BEHAVIOR) <= behavior, sorted(behavior)),
        _check(
            "future_scope_counts_expected",
            review["future_scope_contract"]["selection_log_count"] == 32
            and review["future_scope_contract"]["record_count"] == 3200
            and review["future_scope_contract"]["candidate_count"] == 8
            and review["future_scope_contract"]["atom_count"] == 14,
        ),
        _check(
            "math_boundary_affine_simplex",
            review["math_boundary"]["candidate_operation"] == "fixed DP candidate reranking only"
            and review["math_boundary"]["score_expression"] == SCORE_EXPRESSION
            and review["math_boundary"]["nonnegative_simplex_weights_only"] is True,
        ),
        _check(
            "implementation_plan_script_contains_gate_names",
            "fresh_evaluation_split_implementation_plan_only" in implementation_plan_script_text
            and "fresh_evaluation_split_implementation_static_contract_review_only"
            in implementation_plan_script_text,
        ),
        _check(
            "implementation_plan_test_covers_rejections",
            "rejects_wrong_audit_target" in implementation_plan_test_text
            and "rejects_source_action_leak" in implementation_plan_test_text
            and "rejects_scope_drift" in implementation_plan_test_text
            and "rejects_dp_head_drift" in implementation_plan_test_text,
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
