#!/usr/bin/env python3
"""Plan remediation for the fixed-DP execution-preflight runner contract.

This plan-only gate consumes the rejected execution-preflight artifact where
the CAMP-owned runner still hard-rejects execution and the source DP command is
a missing placeholder. The remediation remains CAMP-side and read-only with
respect to Diffusion Planner. This tool does not run Diffusion Planner,
generate candidates, train CAMP, modify DP, promote, deploy, or make
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
SOURCE_SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_v1"
SOURCE_REJECT_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_rejected"
SOURCE_FAILURE_CLASS = "runner_execution_contract_not_authorized"
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_preflight_rejected_runner_contract_remediation_required"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "runner_contract_remediation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "runner_contract_remediation_static_contract_review_only"
)
FUTURE_STATIC_REVIEW_SCRIPT = (
    "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution_preflight_runner_contract_remediation_static_contract.py"
)
FUTURE_STATIC_REVIEW_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "execution_preflight_runner_contract_remediation_static_contract.py"
)
RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
PREFLIGHT_SCRIPT = (
    "scripts/integrations/preflight_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
SOURCE_REQUIRED_FAILED_CHECKS = (
    "runner_script_does_not_hard_reject_execute",
    "base_dp_command_entrypoint_exists",
)
SOURCE_FALSE_FLAGS = (
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
REQUIRED_SOURCE_SCRIPT_SNIPPETS = (
    "runner_script_does_not_hard_reject_execute",
    "base_dp_command_entrypoint_exists",
    "runner_execution_contract_not_authorized",
)
REQUIRED_SOURCE_TEST_SNIPPETS = (
    "test_execution_preflight_rejects_runner_that_still_hard_rejects_execute",
    "test_execution_preflight_rejects_missing_dp_command_entrypoint",
    "runner_execution_contract_not_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--preflight_script", type=Path, required=True)
    parser.add_argument("--preflight_test", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--dp_repo", type=Path, default=Path("/root/autodl-tmp/Diffusion-Planner"))
    parser.add_argument("--camp_repo", type=Path, default=Path("/root/autodl-tmp/camp_core"))
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        preflight_json=args.preflight_json,
        preflight_artifact_dir=args.preflight_artifact_dir,
        preflight_script=args.preflight_script,
        preflight_test=args.preflight_test,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        dp_repo=args.dp_repo,
        camp_repo=args.camp_repo,
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
    preflight_json: Path,
    preflight_artifact_dir: Path,
    preflight_script: Path,
    preflight_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    dp_repo: Path = Path("/root/autodl-tmp/Diffusion-Planner"),
    camp_repo: Path = Path("/root/autodl-tmp/camp_core"),
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_payload = _load_json_dict(preflight_json)
    source_decision = _dict(source_payload.get("final_decision"))
    source_preflight = _dict(source_payload.get("execution_preflight"))
    source_script_text = _read_text(preflight_script)
    source_test_text = _read_text(preflight_test)
    audit_text = _read_text(v13_audit_md)
    remediation = _remediation_plan(source_preflight=source_preflight, dp_repo=dp_repo, camp_repo=camp_repo)
    checks = _checks(
        preflight_json=preflight_json,
        preflight_artifact_dir=preflight_artifact_dir,
        preflight_script=preflight_script,
        preflight_test=preflight_test,
        v13_audit_md=v13_audit_md,
        source_payload=source_payload,
        source_decision=source_decision,
        source_preflight=source_preflight,
        source_script_text=source_script_text,
        source_test_text=source_test_text,
        audit_text=audit_text,
        remediation=remediation,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "data_preparation_execution": False,
            "training_preflight": False,
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
        "source_preflight": {
            "path": str(preflight_json.resolve()),
            "artifact_dir": str(preflight_artifact_dir.resolve()),
            "schema_version": source_payload.get("schema_version"),
            "status": source_decision.get("status"),
            "passed": source_decision.get("passed"),
            "failure_class": source_decision.get("failure_class"),
            "failed_checks": source_decision.get("failed_checks"),
            "json_sha256": _sha256(preflight_json),
        },
        "runner_contract_remediation_plan": remediation,
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
    preflight_json: Path,
    preflight_artifact_dir: Path,
    preflight_script: Path,
    preflight_test: Path,
    v13_audit_md: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    source_preflight: dict[str, Any],
    source_script_text: str,
    source_test_text: str,
    audit_text: str,
    remediation: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    dp_repo: Path,
    camp_repo: Path,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    failed_checks = set(_list(source_decision.get("failed_checks")))
    source_zero_keys = set(_list(source_preflight.get("required_zero_overlap_keys")))
    base_entrypoint = _optional_path(source_preflight.get("base_dp_command_entrypoint_path"))

    add(_expect("preflight_json_exists", preflight_json.exists(), True))
    add(_expect("preflight_artifact_dir_exists", preflight_artifact_dir.exists(), True))
    add(_expect("preflight_script_exists", preflight_script.exists(), True))
    add(_expect("preflight_test_exists", preflight_test.exists(), True))
    add(_expect("v13_audit_exists", v13_audit_md.exists(), True))
    add(_expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION))
    add(_expect("source_status", source_decision.get("status"), SOURCE_REJECT_STATUS))
    add(_expect("source_passed", source_decision.get("passed"), False))
    add(_expect("source_failure_class", source_decision.get("failure_class"), SOURCE_FAILURE_CLASS))
    add(_expect("source_recommended_next_work", source_decision.get("recommended_next_work"), authorized_current_work))
    for failed in SOURCE_REQUIRED_FAILED_CHECKS:
        add(_expect(f"source_failed_check_{failed}", failed in failed_checks, True))
    add(_expect("source_preflight_passed_false", source_decision.get("fixed_dp_candidate_generation_execution_preflight_passed"), False))
    for flag in SOURCE_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))
    add(_expect("source_runner_script_exists", source_preflight.get("runner_script_exists"), True))
    add(_expect("source_base_dp_entrypoint_exists_false", source_preflight.get("base_dp_command_entrypoint_exists"), False))
    add(_expect("source_base_dp_entrypoint_still_missing", base_entrypoint is not None and not base_entrypoint.exists(), True))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"source_requires_zero_overlap_{key}", key in source_zero_keys, True))

    add(_expect("camp_repo_exists", camp_repo.is_dir(), True))
    add(_expect("dp_repo_exists", dp_repo.is_dir(), True))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(_expect("audit_records_preflight_failed", _latest_value(audit_text, "fixed_dp_candidate_generation_execution_preflight_passed"), "False"))
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))

    for snippet in REQUIRED_SOURCE_SCRIPT_SNIPPETS:
        add(_expect(f"source_script_contains_{_slug(snippet)}", snippet in source_script_text, True))
    for snippet in REQUIRED_SOURCE_TEST_SNIPPETS:
        add(_expect(f"source_test_contains_{_slug(snippet)}", snippet in source_test_text, True))

    add(_expect("plan_scope", remediation.get("remediation_scope"), "CAMP-owned runner contract and command validation only"))
    add(_expect("plan_authorizes_execution", remediation.get("execution_authorized_by_this_gate"), False))
    add(_expect("plan_forbids_dp_modification", remediation.get("dp_repo_modification_allowed"), False))
    add(_expect("plan_forbids_training", remediation.get("training_authorized_by_this_gate"), False))
    add(_expect("plan_future_static_review_script", remediation.get("future_static_review_script"), FUTURE_STATIC_REVIEW_SCRIPT))
    targets = set(_list(remediation.get("future_implementation_targets")))
    add(_expect("plan_targets_runner_script", RUNNER_SCRIPT in targets, True))
    add(_expect("plan_targets_preflight_script", PREFLIGHT_SCRIPT in targets, True))
    required_changes = set(_list(remediation.get("required_contract_changes")))
    add(_expect("plan_requires_execute_gate_support", "replace_runner_implementation_only_execute_rejection_with_execution_gate_check" in required_changes, True))
    add(_expect("plan_requires_command_discovery", "replace_planner_generate_placeholder_with_validated_fixed_dp_candidate_export_command" in required_changes, True))
    add(_expect("plan_requires_zero_overlap", "preserve_zero_overlap_registry_requirements" in required_changes, True))
    return checks


def _remediation_plan(*, source_preflight: dict[str, Any], dp_repo: Path, camp_repo: Path) -> dict[str, Any]:
    return {
        "remediation_scope": "CAMP-owned runner contract and command validation only",
        "execution_authorized_by_this_gate": False,
        "fixed_dp_candidate_generation_authorized_by_this_gate": False,
        "training_authorized_by_this_gate": False,
        "dp_repo_modification_allowed": False,
        "dp_config_weight_checkpoint_change_allowed": False,
        "candidate_generation_by_camp_allowed": False,
        "trajectory_generation_by_camp_allowed": False,
        "trajectory_modification_by_camp_allowed": False,
        "reference_blend_allowed": False,
        "guidance_allowed": False,
        "postprocess_or_postselection_allowed": False,
        "closed_loop_outcome_allowed": False,
        "future_static_review_script": FUTURE_STATIC_REVIEW_SCRIPT,
        "future_static_review_test": FUTURE_STATIC_REVIEW_TEST,
        "future_implementation_targets": [RUNNER_SCRIPT, PREFLIGHT_SCRIPT],
        "required_contract_changes": [
            "replace_runner_implementation_only_execute_rejection_with_execution_gate_check",
            "replace_planner_generate_placeholder_with_validated_fixed_dp_candidate_export_command",
            "preserve_zero_overlap_registry_requirements",
            "require_guard_env_var_for_any_future_execution",
            "keep_affine_score_contract",
            "keep_nonexecution_gates_default_off",
        ],
        "source_base_dp_command": _list(source_preflight.get("base_dp_command")),
        "source_base_dp_entrypoint": source_preflight.get("base_dp_command_entrypoint_path"),
        "source_base_dp_entrypoint_exists": source_preflight.get("base_dp_command_entrypoint_exists"),
        "source_runner_script": source_preflight.get("runner_script_path"),
        "dp_repo": str(dp_repo),
        "camp_repo": str(camp_repo),
        "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
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
        "runner_contract_remediation_plan_ready": passed,
        "runner_contract_remediation_static_contract_review_authorized_next": passed,
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
    source = _dict(report.get("source_preflight"))
    plan = _dict(report.get("runner_contract_remediation_plan"))
    return "\n".join(
        [
            "# Runner Contract Remediation Plan",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{decision.get('failed_checks')}`",
            f"- Source preflight: `{source.get('path')}`",
            f"- Source failure class: `{source.get('failure_class')}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Future static review script: `{plan.get('future_static_review_script')}`",
            f"- Execution authorized by this gate: `{plan.get('execution_authorized_by_this_gate')}`",
            f"- DP modification allowed: `{plan.get('dp_repo_modification_allowed')}`",
            f"- Training authorized by this gate: `{plan.get('training_authorized_by_this_gate')}`",
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


def _optional_path(value: Any) -> Path | None:
    if isinstance(value, str) and value:
        return Path(value)
    return None


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
