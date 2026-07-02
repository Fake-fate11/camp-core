#!/usr/bin/env python3
"""Plan remediation for the fixed-DP candidate-generation entrypoint contract.

This plan-only gate consumes the rejected execution-preflight artifact where
the generated runbook pointed at a missing DP-repo entrypoint. The remediation
keeps Diffusion Planner fixed and read-only: the next implementation must be a
CAMP-owned adapter/contract update, not a DP code/config/weight change. This
tool does not run Diffusion Planner, generate candidates, train CAMP, modify
DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
SOURCE_FAILURE_CLASS = "missing_fixed_dp_candidate_generation_entrypoint"
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_preflight_rejected_missing_fixed_dp_entrypoint"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_static_contract_review_only"
)
FUTURE_STATIC_REVIEW_SCRIPT = (
    "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "entrypoint_contract_remediation_static_contract.py"
)
FUTURE_STATIC_REVIEW_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "entrypoint_contract_remediation_static_contract.py"
)
FUTURE_IMPLEMENTATION_TARGET = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
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
    "dp_entrypoint_exists",
    "missing_fixed_dp_candidate_generation_entrypoint",
    "fixed_dp_candidate_generation_execution_authorized_next",
)
REQUIRED_SOURCE_TEST_SNIPPETS = (
    "test_execution_preflight_rejects_missing_dp_entrypoint",
    "dp_entrypoint_exists",
    "missing_fixed_dp_candidate_generation_entrypoint",
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
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "data_preparation_execution": False,
            "replay_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
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
            "failed_checks": source_decision.get("failed_checks"),
            "failure_class": source_decision.get("failure_class"),
            "dp_entrypoint_path": source_preflight.get("dp_entrypoint_path"),
            "dp_entrypoint_exists": source_preflight.get("dp_entrypoint_exists"),
            "json_sha256": _sha256(preflight_json),
        },
        "entrypoint_contract_remediation_plan": remediation,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _remediation_plan(
    *,
    source_preflight: dict[str, Any],
    dp_repo: Path,
    camp_repo: Path,
) -> dict[str, Any]:
    missing_entrypoint = str(source_preflight.get("dp_entrypoint_path") or "")
    return {
        "failure_class": SOURCE_FAILURE_CLASS,
        "missing_entrypoint_path": missing_entrypoint,
        "dp_repo": str(dp_repo),
        "camp_repo": str(camp_repo),
        "remediation_scope": "CAMP-owned entrypoint contract only",
        "dp_repo_modification_allowed": False,
        "dp_config_weight_checkpoint_change_allowed": False,
        "future_static_review_script": FUTURE_STATIC_REVIEW_SCRIPT,
        "future_static_review_test": FUTURE_STATIC_REVIEW_TEST,
        "future_implementation_target": FUTURE_IMPLEMENTATION_TARGET,
        "required_contract_changes": [
            "replace_dp_repo_tools_entrypoint_with_camp_owned_adapter",
            "keep_diffusion_planner_checkout_read_only_at_required_commit",
            "fail_if_required_dp_head_or_candidate_count_drifts",
            "emit_fixed_dp_candidate_tensor_registries_for_zero_overlap",
            "preserve_guard_env_before_any_future_execution",
            "forbid_camp_trajectory_generation_repair_rewrite_or_blend",
            "forbid_reference_blend_guidance_postprocess_and_postselection",
            "forbid_closed_loop_outcomes_full36_and_formal_seeds",
            "keep_score_affine_and_simplex_contracts_unchanged",
        ],
        "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        "next_gate_is_static_review_only": True,
        "execution_authorized_by_this_gate": False,
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
    add(_expect("preflight_json_exists", preflight_json.exists(), True))
    add(_expect("preflight_artifact_dir_exists", preflight_artifact_dir.exists(), True))
    add(_expect("preflight_script_exists", preflight_script.exists(), True))
    add(_expect("preflight_test_exists", preflight_test.exists(), True))
    add(_expect("v13_audit_exists", v13_audit_md.exists(), True))
    add(_expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION))
    add(_expect("source_status", source_decision.get("status"), SOURCE_REJECT_STATUS))
    add(_expect("source_passed_false", source_decision.get("passed"), False))
    add(_expect("source_failed_checks", source_decision.get("failed_checks"), ["dp_entrypoint_exists"]))
    add(_expect("source_failure_class", source_decision.get("failure_class"), SOURCE_FAILURE_CLASS))
    add(_expect("source_recommended_next_work", source_decision.get("recommended_next_work"), authorized_current_work))
    add(_expect("source_preflight_passed_false", source_decision.get("fixed_dp_candidate_generation_execution_preflight_passed"), False))
    for flag in SOURCE_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))
    add(_expect("source_dp_entrypoint_exists_false", source_preflight.get("dp_entrypoint_exists"), False))
    missing_path = str(source_preflight.get("dp_entrypoint_path") or "")
    add(_expect("source_dp_entrypoint_path_nonempty", bool(missing_path), True))
    add(_expect("source_dp_entrypoint_path_in_dp_repo", missing_path.startswith(str(dp_repo)), True))
    add(_expect("actual_dp_entrypoint_still_missing", Path(missing_path).exists(), False))
    for snippet in REQUIRED_SOURCE_SCRIPT_SNIPPETS:
        add(_expect(f"source_script_contains_{_slug(snippet)}", snippet in source_script_text, True))
    for snippet in REQUIRED_SOURCE_TEST_SNIPPETS:
        add(_expect(f"source_test_contains_{_slug(snippet)}", snippet in source_test_text, True))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("dp_repo_exists", dp_repo.is_dir(), True))
    add(_expect("camp_repo_exists", camp_repo.is_dir(), True))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(_expect("audit_records_rejected_preflight", _latest_value(audit_text, "fixed_dp_candidate_generation_execution_preflight_rejected"), "True"))
    add(_expect("audit_records_failure_class", _latest_value(audit_text, "fixed_dp_candidate_generation_execution_preflight_failure_class"), SOURCE_FAILURE_CLASS))
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
    add(_expect("plan_is_camp_owned_scope", remediation.get("remediation_scope"), "CAMP-owned entrypoint contract only"))
    add(_expect("plan_forbids_dp_modification", remediation.get("dp_repo_modification_allowed"), False))
    add(_expect("plan_forbids_dp_config_weight_checkpoint_change", remediation.get("dp_config_weight_checkpoint_change_allowed"), False))
    add(_expect("plan_future_static_review_script", remediation.get("future_static_review_script"), FUTURE_STATIC_REVIEW_SCRIPT))
    add(_expect("plan_future_implementation_target", remediation.get("future_implementation_target"), FUTURE_IMPLEMENTATION_TARGET))
    add(_expect("plan_next_gate_static_review_only", remediation.get("next_gate_is_static_review_only"), True))
    add(_expect("plan_execution_not_authorized", remediation.get("execution_authorized_by_this_gate"), False))
    zero_keys = set(_list(remediation.get("required_zero_overlap_keys")))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"plan_requires_zero_overlap_{key}", key in zero_keys, True))
    return checks


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
        "entrypoint_contract_remediation_plan_ready": passed,
        "entrypoint_contract_remediation_static_contract_review_authorized_next": passed,
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
    plan = _dict(report.get("entrypoint_contract_remediation_plan"))
    failed = decision.get("failed_checks") or []
    return "\n".join(
        [
            "# Fixed-DP Candidate Generation Entrypoint Contract Remediation Plan",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{failed}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Remediation scope: `{plan.get('remediation_scope')}`",
            f"- Missing entrypoint: `{plan.get('missing_entrypoint_path')}`",
            f"- Future implementation target: `{plan.get('future_implementation_target')}`",
            f"- DP modification allowed: `{plan.get('dp_repo_modification_allowed')}`",
            f"- Fixed-DP generation executed: `{decision.get('fixed_dp_candidate_generation_executed')}`",
            f"- Fixed-DP generation execution authorized: `{decision.get('fixed_dp_candidate_generation_execution_authorized_next')}`",
            f"- CAMP candidate generation authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- Training preflight authorized next: `{decision.get('training_preflight_authorized_next')}`",
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
