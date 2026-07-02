#!/usr/bin/env python3
"""Static contract review for runner-contract remediation planning.

This read-only gate reviews the runner-contract remediation plan artifact and
the plan tool/test that produced it. It can authorize only an implementation
plan. It does not run Diffusion Planner, generate candidates, modify DP, train
CAMP, promote, deploy, or make safety/CAMP-over-DP claims.
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
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_plan_v1"
)
SOURCE_READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_preflight_runner_contract_remediation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "runner_contract_remediation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "runner_contract_remediation_implementation_plan_only"
)
PLAN_SCRIPT = (
    "scripts/integrations/plan_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution_preflight_runner_contract_remediation.py"
)
PLAN_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "execution_preflight_runner_contract_remediation_plan.py"
)
FUTURE_IMPLEMENTATION_TARGETS = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py",
    "scripts/integrations/preflight_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution.py",
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
SOURCE_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_execution_preflight_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fixed_dp_candidate_generation_executed",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "data_preparation_authorized_next",
    "replay_execution_authorized_next",
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
    "fixed_dp_candidate_generation_execution_preflight_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fixed_dp_candidate_generation_executed",
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
REQUIRED_PLAN_SCRIPT_SNIPPETS = (
    "replace_runner_implementation_only_execute_rejection_with_execution_gate_check",
    "replace_planner_generate_placeholder_with_validated_fixed_dp_candidate_export_command",
    "CAMP-owned runner contract and command validation only",
    "runner_contract_remediation_static_contract_review_only",
)
REQUIRED_PLAN_TEST_SNIPPETS = (
    "test_runner_contract_remediation_plan_authorizes_static_review_only",
    "test_runner_contract_remediation_plan_rejects_execution_auth_leak",
    "replace_planner_generate_placeholder_with_validated_fixed_dp_candidate_export_command",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--plan_script", type=Path, required=True)
    parser.add_argument("--plan_test", type=Path, required=True)
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
        plan_json=args.plan_json,
        plan_artifact_dir=args.plan_artifact_dir,
        plan_script=args.plan_script,
        plan_test=args.plan_test,
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
    plan_json: Path,
    plan_artifact_dir: Path,
    plan_script: Path,
    plan_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_payload = _load_json_dict(plan_json)
    source_decision = _dict(source_payload.get("final_decision"))
    plan = _dict(source_payload.get("runner_contract_remediation_plan"))
    plan_script_text = _read_text(plan_script)
    plan_test_text = _read_text(plan_test)
    audit_text = _read_text(v13_audit_md)
    checks = _checks(
        plan_json=plan_json,
        plan_artifact_dir=plan_artifact_dir,
        plan_script=plan_script,
        plan_test=plan_test,
        v13_audit_md=v13_audit_md,
        source_payload=source_payload,
        source_decision=source_decision,
        plan=plan,
        plan_script_text=plan_script_text,
        plan_test_text=plan_test_text,
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
            "static_contract_review_only": True,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "training_execution": False,
            "dp_modification": False,
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
        "source_plan": {
            "path": str(plan_json.resolve()),
            "artifact_dir": str(plan_artifact_dir.resolve()),
            "schema_version": source_payload.get("schema_version"),
            "status": source_decision.get("status"),
            "passed": source_decision.get("passed"),
            "json_sha256": _sha256(plan_json),
        },
        "plan_static_contract": {
            "future_implementation_targets": plan.get("future_implementation_targets"),
            "required_contract_changes": plan.get("required_contract_changes"),
            "future_static_review_script": plan.get("future_static_review_script"),
            "execution_authorized_by_source_plan": plan.get("execution_authorized_by_this_gate"),
            "dp_modification_allowed_by_source_plan": plan.get("dp_repo_modification_allowed"),
        },
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _checks(
    *,
    plan_json: Path,
    plan_artifact_dir: Path,
    plan_script: Path,
    plan_test: Path,
    v13_audit_md: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    plan: dict[str, Any],
    plan_script_text: str,
    plan_test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    targets = set(_list(plan.get("future_implementation_targets")))
    changes = set(_list(plan.get("required_contract_changes")))
    zero_keys = set(_list(plan.get("required_zero_overlap_keys")))

    add(_expect("plan_json_exists", plan_json.exists(), True))
    add(_expect("plan_artifact_dir_exists", plan_artifact_dir.exists(), True))
    add(_expect("plan_script_exists", plan_script.exists(), True))
    add(_expect("plan_test_exists", plan_test.exists(), True))
    add(_expect("v13_audit_exists", v13_audit_md.exists(), True))
    add(_expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION))
    add(_expect("source_status", source_decision.get("status"), SOURCE_READY_STATUS))
    add(_expect("source_passed", source_decision.get("passed"), True))
    add(_expect("source_failed_checks_empty", source_decision.get("failed_checks"), []))
    add(_expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work))
    add(_expect("source_plan_ready", source_decision.get("runner_contract_remediation_plan_ready"), True))
    add(
        _expect(
            "source_authorizes_static_review",
            source_decision.get("runner_contract_remediation_static_contract_review_authorized_next"),
            True,
        )
    )
    for flag in SOURCE_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))

    add(_expect("plan_scope", plan.get("remediation_scope"), "CAMP-owned runner contract and command validation only"))
    add(_expect("plan_execution_false", plan.get("execution_authorized_by_this_gate"), False))
    add(_expect("plan_fixed_dp_generation_false", plan.get("fixed_dp_candidate_generation_authorized_by_this_gate"), False))
    add(_expect("plan_training_false", plan.get("training_authorized_by_this_gate"), False))
    add(_expect("plan_dp_modification_false", plan.get("dp_repo_modification_allowed"), False))
    add(_expect("plan_dp_config_weight_checkpoint_false", plan.get("dp_config_weight_checkpoint_change_allowed"), False))
    add(_expect("plan_future_static_review_script", plan.get("future_static_review_script"), plan_script_to_review_script()))
    for target in FUTURE_IMPLEMENTATION_TARGETS:
        add(_expect(f"plan_targets_{_slug(target)}", target in targets, True))
    for change in (
        "replace_runner_implementation_only_execute_rejection_with_execution_gate_check",
        "replace_planner_generate_placeholder_with_validated_fixed_dp_candidate_export_command",
        "preserve_zero_overlap_registry_requirements",
        "require_guard_env_var_for_any_future_execution",
        "keep_affine_score_contract",
        "keep_nonexecution_gates_default_off",
    ):
        add(_expect(f"plan_requires_{_slug(change)}", change in changes, True))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"plan_requires_zero_overlap_{key}", key in zero_keys, True))

    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(_expect("audit_records_plan_ready", _latest_value(audit_text, "runner_contract_remediation_plan_ready"), "True"))
    add(
        _expect(
            "audit_authorizes_static_review",
            _latest_value(audit_text, "runner_contract_remediation_static_contract_review_authorized_next"),
            "True",
        )
    )
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
    for snippet in REQUIRED_PLAN_SCRIPT_SNIPPETS:
        add(_expect(f"plan_script_contains_{_slug(snippet)}", snippet in plan_script_text, True))
    for snippet in REQUIRED_PLAN_TEST_SNIPPETS:
        add(_expect(f"plan_test_contains_{_slug(snippet)}", snippet in plan_test_text, True))
    return checks


def plan_script_to_review_script() -> str:
    return (
        "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
        "generation_execution_preflight_runner_contract_remediation_static_contract.py"
    )


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
        "runner_contract_remediation_static_contract_review_passed": passed,
        "runner_contract_remediation_implementation_plan_authorized_next": passed,
        "fixed_dp_candidate_generation_execution_preflight_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "replay_execution_authorized_next": False,
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


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    source = _dict(report.get("source_plan"))
    return "\n".join(
        [
            "# Runner Contract Remediation Static Contract Review",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{decision.get('failed_checks')}`",
            f"- Source plan: `{source.get('path')}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Implementation plan authorized next: `{decision.get('runner_contract_remediation_implementation_plan_authorized_next')}`",
            f"- Fixed-DP generation execution authorized: `{decision.get('fixed_dp_candidate_generation_execution_authorized_next')}`",
            f"- Training preflight authorized: `{decision.get('training_preflight_authorized_next')}`",
            f"- DP modification authorized: `{decision.get('dp_modification_authorized')}`",
            f"- Candidate operation: `{decision.get('candidate_operation')}`",
            f"- Score expression: `{decision.get('score_expression')}`",
            "",
        ]
    )


def _load_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0].strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")[:80]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
