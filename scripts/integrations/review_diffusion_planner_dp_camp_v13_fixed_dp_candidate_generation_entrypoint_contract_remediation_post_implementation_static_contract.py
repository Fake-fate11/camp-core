#!/usr/bin/env python3
"""Post-implementation static review for the fixed-DP runner remediation.

This read-only gate reviews the landed CAMP-owned runner and its implementation
artifact. It can authorize only the fixed-DP candidate generation execution
preflight. It does not run Diffusion Planner, generate candidates, prepare
data, replay, train CAMP, modify DP, promote, deploy, or make claims.
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
GUARD_ENV_VAR = "DP_CAMP_V13_FIXED_DP_CANDIDATE_GENERATION_EXECUTE"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "runner_implementation_v1"
)
SOURCE_READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "runner_implementation_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "post_implementation_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "post_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "post_implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_runner_implementation_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_only"
)
RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
SOURCE_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_preflight_authorized_next",
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
REQUIRED_RUNNER_SCRIPT_SNIPPETS = (
    GUARD_ENV_VAR,
    "execute_fixed_dp_command",
    "runner_is_default_off_for_this_gate",
    "--forbid_full36",
    "--forbid_formal_seeds",
    "--write_zero_overlap_registries",
    "fixed DP candidate reranking only",
    SCORE_EXPRESSION,
    "FORBIDDEN_COMMAND_SNIPPETS",
)
REQUIRED_RUNNER_TEST_SNIPPETS = (
    "test_runner_rejects_execute_in_implementation_gate",
    "test_runner_rejects_forbidden_command_snippet",
    "fixed_dp_candidate_generation_executed",
    "candidate_generation_by_camp_authorized",
    "training_preflight_authorized_next",
    "GUARD_ENV_VAR",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner_implementation_json", type=Path, required=True)
    parser.add_argument("--runner_implementation_artifact_dir", type=Path, required=True)
    parser.add_argument("--runner_script", type=Path, required=True)
    parser.add_argument("--runner_test", type=Path, required=True)
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
        runner_implementation_json=args.runner_implementation_json,
        runner_implementation_artifact_dir=args.runner_implementation_artifact_dir,
        runner_script=args.runner_script,
        runner_test=args.runner_test,
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
    runner_implementation_json: Path,
    runner_implementation_artifact_dir: Path,
    runner_script: Path,
    runner_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_payload = _load_json_dict(runner_implementation_json)
    source_decision = _dict(source_payload.get("final_decision"))
    runner_contract = _dict(source_payload.get("runner_contract"))
    runner_script_text = _read_text(runner_script)
    runner_test_text = _read_text(runner_test)
    audit_text = _read_text(v13_audit_md)
    checks = _checks(
        runner_implementation_json=runner_implementation_json,
        runner_implementation_artifact_dir=runner_implementation_artifact_dir,
        runner_script=runner_script,
        runner_test=runner_test,
        v13_audit_md=v13_audit_md,
        source_payload=source_payload,
        source_decision=source_decision,
        runner_contract=runner_contract,
        runner_script_text=runner_script_text,
        runner_test_text=runner_test_text,
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
            "post_implementation_static_review_only": True,
            "fixed_dp_candidate_generation_execution_preflight_authorized_next": passed,
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
        "source_runner_implementation": {
            "path": str(runner_implementation_json.resolve()),
            "artifact_dir": str(runner_implementation_artifact_dir.resolve()),
            "schema_version": source_payload.get("schema_version"),
            "status": source_decision.get("status"),
            "passed": source_decision.get("passed"),
            "json_sha256": _sha256(runner_implementation_json),
        },
        "runner_contract_review": {
            "runner_script": runner_contract.get("runner_script"),
            "guard_env_var": runner_contract.get("guard_env_var"),
            "required_zero_overlap_keys": runner_contract.get("required_zero_overlap_keys"),
            "fixed_dp_candidate_generation_executed": runner_contract.get(
                "fixed_dp_candidate_generation_executed"
            ),
            "candidate_generation_by_camp": runner_contract.get("candidate_generation_by_camp"),
            "dp_modification": runner_contract.get("dp_modification"),
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
    runner_implementation_json: Path,
    runner_implementation_artifact_dir: Path,
    runner_script: Path,
    runner_test: Path,
    v13_audit_md: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    runner_contract: dict[str, Any],
    runner_script_text: str,
    runner_test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    planned_command = _list(runner_contract.get("planned_command"))
    zero_keys = set(_list(runner_contract.get("required_zero_overlap_keys")))
    checks: list[dict[str, Any]] = [
        _expect("runner_implementation_json_exists", runner_implementation_json.exists(), True),
        _expect("runner_implementation_artifact_dir_exists", runner_implementation_artifact_dir.exists(), True),
        _expect("runner_script_exists", runner_script.exists(), True),
        _expect("runner_test_exists", runner_test.exists(), True),
        _expect("v13_audit_exists", v13_audit_md.exists(), True),
        _expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status", source_decision.get("status"), SOURCE_READY_STATUS),
        _expect("source_passed", source_decision.get("passed"), True),
        _expect("source_failed_checks_empty", source_decision.get("failed_checks"), []),
        _expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work),
        _expect("source_implementation_complete", source_decision.get("entrypoint_contract_remediation_implementation_complete"), True),
        _expect(
            "source_post_review_authorized",
            source_decision.get(
                "entrypoint_contract_remediation_post_implementation_static_contract_review_authorized_next"
            ),
            True,
        ),
        _expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("runner_contract_script", runner_contract.get("runner_script"), RUNNER_SCRIPT),
        _expect("runner_contract_guard_env", runner_contract.get("guard_env_var"), GUARD_ENV_VAR),
        _expect("runner_contract_execution_false", runner_contract.get("fixed_dp_candidate_generation_executed"), False),
        _expect("runner_contract_candidate_generation_by_camp_false", runner_contract.get("candidate_generation_by_camp"), False),
        _expect("runner_contract_dp_modification_false", runner_contract.get("dp_modification"), False),
        _expect("planned_command_has_output_dir", "--output_dir" in planned_command, True),
        _expect("planned_command_has_fixed_dp_head", FIXED_DP_HEAD in planned_command, True),
        _expect("planned_command_forbids_full36", "--forbid_full36" in planned_command, True),
        _expect("planned_command_forbids_formal_seeds", all(seed in planned_command for seed in ("11", "12", "13")), True),
        _expect("planned_command_writes_zero_overlap_registries", "--write_zero_overlap_registries" in planned_command, True),
        _expect("planned_command_candidate_operation_fixed", "fixed DP candidate reranking only" in planned_command, True),
        _expect("planned_command_score_affine", SCORE_EXPRESSION in planned_command, True),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_authorizes_post_review",
            _latest_value(
                audit_text,
                "entrypoint_contract_remediation_post_implementation_static_contract_review_authorized_next",
            ),
            "True",
        ),
    ]
    for key in ZERO_OVERLAP_KEYS:
        checks.append(_expect(f"runner_contract_requires_zero_overlap_{key}", key in zero_keys, True))
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
    for snippet in REQUIRED_RUNNER_SCRIPT_SNIPPETS:
        checks.append(_expect(f"runner_script_contains_{_slug(snippet)}", snippet in runner_script_text, True))
    for snippet in REQUIRED_RUNNER_TEST_SNIPPETS:
        checks.append(_expect(f"runner_test_contains_{_slug(snippet)}", snippet in runner_test_text, True))
    return checks


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
        "entrypoint_contract_remediation_post_implementation_static_contract_review_passed": passed,
        "fixed_dp_candidate_generation_execution_preflight_authorized_next": passed,
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
    source = _dict(report.get("source_runner_implementation"))
    return "\n".join(
        [
            "# Entrypoint Remediation Runner Post-Implementation Static Contract Review",
            "",
            f"- status: `{decision.get('status')}`",
            f"- passed: `{decision.get('passed')}`",
            f"- failed_checks: `{decision.get('failed_checks')}`",
            f"- source_runner_json_sha256: `{source.get('json_sha256')}`",
            f"- authorized_next_work: `{decision.get('authorized_next_work')}`",
            f"- execution_preflight_authorized_next: `{decision.get('fixed_dp_candidate_generation_execution_preflight_authorized_next')}`",
            f"- fixed_dp_generation_execution_authorized: `{decision.get('fixed_dp_candidate_generation_execution_authorized_next')}`",
            f"- fixed_dp_generation_executed: `{decision.get('fixed_dp_candidate_generation_executed')}`",
            f"- camp_candidate_generation_authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- training_preflight_authorized: `{decision.get('training_preflight_authorized_next')}`",
            f"- dp_modification_authorized: `{decision.get('dp_modification_authorized')}`",
            f"- candidate_operation: `{decision.get('candidate_operation')}`",
            f"- score_expression: `{decision.get('score_expression')}`",
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
