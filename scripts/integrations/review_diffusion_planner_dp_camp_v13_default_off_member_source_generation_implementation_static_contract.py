#!/usr/bin/env python3
"""Static contract review for v13 default-off source-generation implementation plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_SCHEMA_VERSION = "dp_camp_v13_default_off_member_source_generation_implementation_plan_v1"
SOURCE_READY_STATUS = "dp_camp_v13_default_off_member_source_generation_implementation_plan_ready"
SCHEMA_VERSION = (
    "dp_camp_v13_default_off_member_source_generation_implementation_"
    "static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_default_off_member_source_generation_implementation_"
    "static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_member_source_generation_implementation_"
    "static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_default_off_"
    "member_source_generation_implementation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_implementation_only"
)
EXPECTED_FUTURE_GENERATOR_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "default_off_member_source_generation.py"
)
EXPECTED_FUTURE_GENERATOR_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "default_off_member_source_generation_builder.py"
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
SOURCE_FALSE_FLAGS = (
    "implementation_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "replay_execution_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
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
    "default_off_member_source_generation_implementation_authorized_next",
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
    "implementation_static_contract_review_authorized_next",
    "implementation_authorized_next\": False",
    "fixed_dp_candidate_generation_authorized_next\": False",
    "training_execution_authorized_next\": False",
    "future_generator_script",
)
REQUIRED_SOURCE_TEST_SNIPPETS = (
    "implementation_static_contract_review_authorized_next",
    "implementation_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "future_generator_script",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--implementation_plan_script", type=Path, required=True)
    parser.add_argument("--implementation_plan_test", type=Path, required=True)
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
        implementation_plan_artifact_dir=args.implementation_plan_artifact_dir,
        implementation_plan_script=args.implementation_plan_script,
        implementation_plan_test=args.implementation_plan_test,
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
    implementation_plan_artifact_dir: Path,
    implementation_plan_script: Path,
    implementation_plan_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    artifact_dir = implementation_plan_artifact_dir.resolve()
    plan_json = artifact_dir / "default_off_member_source_generation_implementation_plan.json"
    plan_payload = _load_json_dict(plan_json)
    plan = _dict(plan_payload.get("implementation_plan"))
    source_script_text = _read_text(implementation_plan_script)
    source_test_text = _read_text(implementation_plan_test)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(plan_payload)
    checks = _checks(
        artifact_dir=artifact_dir,
        plan_json=plan_json,
        implementation_plan_script=implementation_plan_script,
        implementation_plan_test=implementation_plan_test,
        v13_audit_md=v13_audit_md,
        plan_payload=plan_payload,
        plan=plan,
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
            "static_review_only": True,
            "implementation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "replay_execution": False,
            "data_preparation": False,
            "training_preflight": False,
            "training_execution": False,
            "dp_modification": False,
            "promotion": False,
            "deployment": False,
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
            "implementation_plan_artifact_dir": str(artifact_dir),
            "implementation_plan_json": str(plan_json),
            "implementation_plan_script": str(implementation_plan_script.resolve()),
            "implementation_plan_test": str(implementation_plan_test.resolve()),
            "v13_audit_md": str(v13_audit_md.resolve()),
        },
        "source_hashes": {
            "implementation_plan_json_sha256": _sha256(plan_json),
            "implementation_plan_script_sha256": _sha256(implementation_plan_script),
            "implementation_plan_test_sha256": _sha256(implementation_plan_test),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "contract_summary": _contract_summary(plan),
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V13 Default-Off Source-Generation Implementation Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Implementation authorized next: `{decision['implementation_authorized_next']}`",
            f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
            f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
        ]
    )


def _checks(
    *,
    artifact_dir: Path,
    plan_json: Path,
    implementation_plan_script: Path,
    implementation_plan_test: Path,
    v13_audit_md: Path,
    plan_payload: dict[str, Any],
    plan: dict[str, Any],
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
    acceptance = _dict(plan.get("acceptance_summary"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory exists"),
        _check("implementation_plan_json_exists", plan_json.is_file(), str(plan_json), "file exists"),
        _check("implementation_plan_script_exists", implementation_plan_script.is_file(), str(implementation_plan_script), "file exists"),
        _check("implementation_plan_test_exists", implementation_plan_test.is_file(), str(implementation_plan_test), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("source_schema", plan_payload.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status", source_summary["status"], SOURCE_READY_STATUS),
        _expect("source_passed", source_summary["passed"], True),
        _expect("source_authorizes_this_gate", source_summary["authorized_next_work"], authorized_current_work),
        _expect("source_static_review_authorized", source_summary["implementation_static_contract_review_authorized_next"], True),
        _expect("plan_not_executed_by_source_gate", plan.get("implementation_performed_by_this_gate"), False),
        _expect("future_generator_script", plan.get("future_generator_script"), EXPECTED_FUTURE_GENERATOR_SCRIPT),
        _expect("future_generator_test", plan.get("future_generator_test"), EXPECTED_FUTURE_GENERATOR_TEST),
        _expect("required_future_behavior", sorted(_list(plan.get("required_future_behavior"))), sorted(REQUIRED_FUTURE_BEHAVIOR)),
        _expect("default_off_execution_contract", acceptance.get("default_off_execution"), "selected_index=0 and executed_index=0 for every record"),
        _expect("shadow_only_field_contract", acceptance.get("shadow_only_field"), "shadow_selected_index may be recorded without execution effect"),
        _expect("acceptance_score_affine", acceptance.get("score_expression"), SCORE_EXPRESSION),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_static_review", _latest_value(audit_text, "default_off_member_source_generation_implementation_static_contract_review_authorized_next"), "True"),
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
        "implementation_static_contract_review_authorized_next": decision.get("implementation_static_contract_review_authorized_next"),
        "implementation_authorized_next": decision.get("implementation_authorized_next"),
        "fixed_dp_candidate_generation_authorized_next": decision.get("fixed_dp_candidate_generation_authorized_next"),
        "candidate_generation_by_camp_authorized": decision.get("candidate_generation_by_camp_authorized"),
        "trajectory_generation_by_camp_authorized": decision.get("trajectory_generation_by_camp_authorized"),
        "trajectory_modification_by_camp_authorized": decision.get("trajectory_modification_by_camp_authorized"),
        "reference_blend_authorized": decision.get("reference_blend_authorized"),
        "guidance_authorized": decision.get("guidance_authorized"),
        "postprocess_or_postselection_authorized": decision.get("postprocess_or_postselection_authorized"),
        "closed_loop_outcome_authorized": decision.get("closed_loop_outcome_authorized"),
        "replay_execution_authorized_next": decision.get("replay_execution_authorized_next"),
        "data_preparation_authorized_next": decision.get("data_preparation_authorized_next"),
        "training_preflight_authorized_next": decision.get("training_preflight_authorized_next"),
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


def _contract_summary(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "future_generator_script": plan.get("future_generator_script"),
        "future_generator_test": plan.get("future_generator_test"),
        "required_future_behavior": plan.get("required_future_behavior"),
        "future_outputs": plan.get("future_outputs"),
        "acceptance_summary": plan.get("acceptance_summary"),
    }


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": PASS_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "implementation_authorized_next": passed,
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


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
