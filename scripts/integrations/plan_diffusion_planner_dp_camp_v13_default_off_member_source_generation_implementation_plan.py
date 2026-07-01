#!/usr/bin/env python3
"""Plan implementation for v13 default-off member-source generation.

This gate consumes the passed default-off member-source generation static
contract review and defines the next implementation-static-review contract.
It does not implement the generator, run DP, generate fixed-DP candidates,
run replay, prepare data, train CAMP, modify DP, promote, deploy, or make
safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_default_off_member_source_generation_static_contract_review_v1"
)
SOURCE_PASS_STATUS = (
    "dp_camp_v13_default_off_member_source_generation_static_contract_review_passed"
)
SCHEMA_VERSION = "dp_camp_v13_default_off_member_source_generation_implementation_plan_v1"
READY_STATUS = "dp_camp_v13_default_off_member_source_generation_implementation_plan_ready"
REJECT_STATUS = "dp_camp_v13_default_off_member_source_generation_implementation_plan_rejected"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_default_off_"
    "member_source_generation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_implementation_static_contract_review_only"
)
FUTURE_GENERATOR_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "default_off_member_source_generation.py"
)
FUTURE_GENERATOR_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "default_off_member_source_generation_builder.py"
)
FUTURE_STATIC_REVIEW_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "default_off_member_source_generation_implementation_static_contract.py"
)
REQUIRED_FUTURE_BEHAVIOR = (
    "generate_or_collect_only_fixed_dp_candidate_tensors",
    "keep_diffusion_planner_head_config_and_weights_fixed",
    "record_default_off_shadow_selector_contract_for_every_record",
    "force_executed_index_zero_and_selected_index_zero_for_every_record",
    "record_shadow_selected_index_without_execution_effect",
    "derive_atoms_only_from_current_tick_candidate_features",
    "preserve_affine_score_k_w_equals_a_k_transpose_w",
    "preserve_nonnegative_simplex_weight_contract",
    "exclude_full36_and_formal_seeds_11_12_13",
    "write_candidate_tensor_hash_path_signature_record_identity_and_split_root_registries",
    "fail_closed_before_training_or_evaluation_until_zero_overlap_preflight_passes",
    "forbid_camp_candidate_generation_trajectory_rewrite_blend_or_postprocess",
)
FUTURE_STATIC_REVIEW_REQUIREMENTS = (
    "reject_if_dp_head_config_or_weights_can_change",
    "reject_if_camp_can_generate_modify_repair_or_blend_trajectories",
    "reject_if_default_off_selected_or_executed_index_can_be_nonzero",
    "reject_if_shadow_selected_index_can_affect_execution",
    "reject_if_formal_seeds_or_full36_can_enter_source",
    "reject_if_candidate_hash_path_record_or_split_root_registry_is_missing",
    "reject_if_zero_overlap_preflight_is_optional",
    "reject_if_training_replay_data_preparation_promotion_or_deployment_is_authorized",
    "reject_if_score_is_not_affine_or_weights_are_not_nonnegative_simplex",
)
SOURCE_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "replay_execution_authorized_next",
    "training_execution_authorized_next",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fresh_member_source_materialization_execution_authorized_next",
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "fresh_evaluation_split_evaluation_result_review_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_by_current_boundary",
    "runtime_shadow_selector_execution_authorized",
    "replay_execution_authorized_by_current_boundary",
    "fixed_dp_candidate_generation_authorized_by_current_boundary",
    "candidate_generation_by_camp_authorized_by_current_boundary",
    "trajectory_generation_by_camp_authorized_by_current_boundary",
    "trajectory_modification_by_camp_authorized_by_current_boundary",
    "dp_modification_authorized_by_current_boundary",
    "formal_seed_11_12_13_execution_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
REQUIRED_SOURCE_SCRIPT_SNIPPETS = (
    "fixed_dp_candidate_generation_authorized_next\": False",
    "candidate_generation_by_camp_authorized\": False",
    "training_execution_authorized_next\": False",
    "dp_modification_authorized\": False",
    "score_expression\": SCORE_EXPRESSION",
)
REQUIRED_SOURCE_TEST_SNIPPETS = (
    "implementation_plan_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "training_execution_authorized_next",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static_contract_review_json", type=Path, required=True)
    parser.add_argument("--static_contract_review_script", type=Path, required=True)
    parser.add_argument("--static_contract_review_test", type=Path, required=True)
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
        static_contract_review_script=args.static_contract_review_script,
        static_contract_review_test=args.static_contract_review_test,
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
    static_contract_review_script: Path,
    static_contract_review_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    static_contract_review_json = static_contract_review_json.resolve()
    static_contract_review_script = static_contract_review_script.resolve()
    static_contract_review_test = static_contract_review_test.resolve()
    v13_audit_md = v13_audit_md.resolve()
    source_payload = _load_json_dict(static_contract_review_json)
    source_script_text = _read_text(static_contract_review_script)
    source_test_text = _read_text(static_contract_review_test)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(source_payload)
    checks = _checks(
        static_contract_review_json=static_contract_review_json,
        static_contract_review_script=static_contract_review_script,
        static_contract_review_test=static_contract_review_test,
        v13_audit_md=v13_audit_md,
        source_payload=source_payload,
        source_summary=source_summary,
        source_script_text=source_script_text,
        source_test_text=source_test_text,
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
            "plan_only": True,
            "implementation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "replay_execution": False,
            "data_preparation": False,
            "training_preflight": False,
            "training_execution": False,
            "dp_modification": False,
            "promotion": False,
            "deployment": False,
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
            "static_contract_review_script": str(static_contract_review_script),
            "static_contract_review_test": str(static_contract_review_test),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "static_contract_review_json_sha256": _sha256(static_contract_review_json),
            "static_contract_review_script_sha256": _sha256(static_contract_review_script),
            "static_contract_review_test_sha256": _sha256(static_contract_review_test),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "implementation_plan": _implementation_plan(),
        "future_static_contract_review_requirements": list(FUTURE_STATIC_REVIEW_REQUIREMENTS),
        "plan_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    lines = [
        "# V13 Default-Off Member-Source Generation Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation execution authorized: `{decision['implementation_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Training authorized: `{decision['training_execution_authorized_next']}`",
        "",
        "## Future Implementation Scope",
        "",
        f"- Target script: `{plan['future_generator_script']}`",
        f"- Target test: `{plan['future_generator_test']}`",
        f"- Implementation performed by this gate: `{plan['implementation_performed_by_this_gate']}`",
        "",
        "## Required Future Behavior",
        "",
    ]
    for item in plan["required_future_behavior"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Future Static Review Requirements", ""])
    for item in report["future_static_contract_review_requirements"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It does not implement the generator, run DP, generate candidates, replay, prepare data, train CAMP, modify DP, promote, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _checks(
    *,
    static_contract_review_json: Path,
    static_contract_review_script: Path,
    static_contract_review_test: Path,
    v13_audit_md: Path,
    source_payload: dict[str, Any],
    source_summary: dict[str, Any],
    source_script_text: str,
    source_test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("static_contract_review_json_exists", static_contract_review_json.is_file(), str(static_contract_review_json), "file exists"),
        _check("static_contract_review_script_exists", static_contract_review_script.is_file(), str(static_contract_review_script), "file exists"),
        _check("static_contract_review_test_exists", static_contract_review_test.is_file(), str(static_contract_review_test), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("source_schema", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status", source_summary["status"], SOURCE_PASS_STATUS),
        _expect("source_passed", source_summary["passed"], True),
        _expect("source_authorizes_this_gate", source_summary["authorized_next_work"], authorized_current_work),
        _expect("source_implementation_plan_authorized", source_summary["implementation_plan_authorized_next"], True),
        _expect("source_score_affine", source_summary["score_expression"], SCORE_EXPRESSION),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_implementation_plan", _latest_value(audit_text, "default_off_member_source_generation_implementation_plan_authorized_next"), "True"),
    ]
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", source_summary.get(flag), False))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    for snippet in REQUIRED_SOURCE_SCRIPT_SNIPPETS:
        checks.append(
            _check(
                f"source_script_contains_{_slug(snippet)}",
                snippet in source_script_text,
                "present" if snippet in source_script_text else "missing",
                snippet,
            )
        )
    for snippet in REQUIRED_SOURCE_TEST_SNIPPETS:
        checks.append(
            _check(
                f"source_test_contains_{_slug(snippet)}",
                snippet in source_test_text,
                "present" if snippet in source_test_text else "missing",
                snippet,
            )
        )
    return checks


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "schema_version": payload.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_authorized_next": decision.get("implementation_plan_authorized_next"),
        "fixed_dp_candidate_generation_authorized_next": decision.get("fixed_dp_candidate_generation_authorized_next"),
        "candidate_generation_by_camp_authorized": decision.get("candidate_generation_by_camp_authorized"),
        "trajectory_generation_by_camp_authorized": decision.get("trajectory_generation_by_camp_authorized"),
        "trajectory_modification_by_camp_authorized": decision.get("trajectory_modification_by_camp_authorized"),
        "reference_blend_authorized": decision.get("reference_blend_authorized"),
        "guidance_authorized": decision.get("guidance_authorized"),
        "postprocess_or_postselection_authorized": decision.get("postprocess_or_postselection_authorized"),
        "closed_loop_outcome_authorized": decision.get("closed_loop_outcome_authorized"),
        "replay_execution_authorized_next": decision.get("replay_execution_authorized_next"),
        "training_execution_authorized_next": decision.get("training_execution_authorized_next"),
        "dp_modification_authorized": decision.get("dp_modification_authorized"),
        "selector_promotion_authorized": decision.get("selector_promotion_authorized"),
        "atom_promotion_authorized": decision.get("atom_promotion_authorized"),
        "deployment_authorized": decision.get("deployment_authorized"),
        "deployable_checkpoint_claim_authorized": decision.get("deployable_checkpoint_claim_authorized"),
        "safety_benefit_claim_authorized": decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": decision.get("camp_over_dp_top1_claim_authorized"),
        "candidate_operation": decision.get("candidate_operation"),
        "score_expression": decision.get("score_expression"),
    }


def _implementation_plan() -> dict[str, Any]:
    return {
        "implementation_performed_by_this_gate": False,
        "future_generator_script": FUTURE_GENERATOR_SCRIPT,
        "future_generator_test": FUTURE_GENERATOR_TEST,
        "future_implementation_static_review_test": FUTURE_STATIC_REVIEW_TEST,
        "required_future_behavior": list(REQUIRED_FUTURE_BEHAVIOR),
        "future_outputs": [
            "default_off_member_source_generation_manifest.json",
            "candidate_tensor_hash_registry.json",
            "path_signature_registry.json",
            "record_identity_registry.json",
            "split_manifest_root_registry.json",
            "zero_overlap_preflight_inputs.json",
            "SHA256SUMS",
        ],
        "acceptance_summary": {
            "dp_role": "fixed black-box candidate tensor generator",
            "camp_role": "current-tick fixed DP candidate reranker only",
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "fixed_dp_head": FIXED_DP_HEAD,
            "default_off_execution": "selected_index=0 and executed_index=0 for every record",
            "shadow_only_field": "shadow_selected_index may be recorded without execution effect",
        },
    }


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "implementation_plan_ready": passed,
        "implementation_static_contract_review_authorized_next": passed,
        "implementation_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "replay_execution_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:64]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
