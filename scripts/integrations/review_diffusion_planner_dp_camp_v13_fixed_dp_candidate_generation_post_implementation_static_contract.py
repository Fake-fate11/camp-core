#!/usr/bin/env python3
"""Post-implementation static review for fixed-DP candidate generation builder.

This read-only gate reviews the builder artifact, generated manifest, and
guarded runbook. It does not run Diffusion Planner, generate candidates,
prepare data, replay, train CAMP, modify DP, promote, deploy, or make
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
SOURCE_SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_builder_v1"
SOURCE_READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_builder_complete"
MANIFEST_SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_manifest_v1"
SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_post_implementation_static_contract_review_v1"
READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_post_implementation_static_contract_review_passed"
REJECT_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_post_implementation_static_contract_review_rejected"
GUARD_ENV_VAR = "DP_CAMP_V13_FIXED_DP_CANDIDATE_GENERATION_EXECUTE"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_implementation_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_only"
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
    "training_executed",
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
    "fixed_dp_candidate_generation_execution_authorized_next",
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
    "DP_CAMP_V13_FIXED_DP_CANDIDATE_GENERATION_EXECUTE",
    "DP HEAD mismatch",
    "--forbid_formal_seeds 11 12 13",
    "--write_zero_overlap_registries",
    "fixed_dp_candidate_generation_executed\": False",
)
REQUIRED_SOURCE_TEST_SNIPPETS = (
    "fixed_dp_candidate_generation_executed",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "candidate_generation_by_camp_authorized",
    "DP HEAD mismatch",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builder_json", type=Path, required=True)
    parser.add_argument("--builder_artifact_dir", type=Path, required=True)
    parser.add_argument("--builder_script", type=Path, required=True)
    parser.add_argument("--builder_test", type=Path, required=True)
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
        builder_json=args.builder_json,
        builder_artifact_dir=args.builder_artifact_dir,
        builder_script=args.builder_script,
        builder_test=args.builder_test,
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
    builder_json: Path,
    builder_artifact_dir: Path,
    builder_script: Path,
    builder_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_payload = _load_json_dict(builder_json)
    source_decision = _dict(source_payload.get("final_decision"))
    generation_builder = _dict(source_payload.get("generation_builder"))
    output_paths = _dict(source_payload.get("output_paths"))
    manifest_path = Path(str(output_paths.get("manifest", "")))
    runbook_path = Path(str(output_paths.get("runbook", "")))
    manifest = _load_json_dict(manifest_path) if manifest_path.exists() else {}
    runbook_text = _read_text(runbook_path) if runbook_path.exists() else ""
    source_script_text = _read_text(builder_script)
    source_test_text = _read_text(builder_test)
    audit_text = _read_text(v13_audit_md)
    checks = _checks(
        builder_json=builder_json,
        builder_artifact_dir=builder_artifact_dir,
        builder_script=builder_script,
        builder_test=builder_test,
        v13_audit_md=v13_audit_md,
        source_payload=source_payload,
        source_decision=source_decision,
        generation_builder=generation_builder,
        manifest_path=manifest_path,
        runbook_path=runbook_path,
        manifest=manifest,
        runbook_text=runbook_text,
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
            "post_implementation_static_review_only": True,
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
        "artifact_summary": {
            "builder_json": str(builder_json.resolve()),
            "builder_artifact_dir": str(builder_artifact_dir.resolve()),
            "manifest_path": str(manifest_path),
            "runbook_path": str(runbook_path),
            "manifest_sha256": _sha256(manifest_path) if manifest_path.exists() else None,
            "runbook_sha256": _sha256(runbook_path) if runbook_path.exists() else None,
            "fixed_dp_candidate_generation_executed": source_decision.get("fixed_dp_candidate_generation_executed"),
            "manifest_written": generation_builder.get("manifest_written"),
            "runbook_guard_env_var": generation_builder.get("runbook_guard_env_var"),
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
    builder_json: Path,
    builder_artifact_dir: Path,
    builder_script: Path,
    builder_test: Path,
    v13_audit_md: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    generation_builder: dict[str, Any],
    manifest_path: Path,
    runbook_path: Path,
    manifest: dict[str, Any],
    runbook_text: str,
    source_script_text: str,
    source_test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    add(_expect("builder_json_exists", builder_json.exists(), True))
    add(_expect("builder_artifact_dir_exists", builder_artifact_dir.exists(), True))
    add(_expect("builder_script_exists", builder_script.exists(), True))
    add(_expect("builder_test_exists", builder_test.exists(), True))
    add(_expect("v13_audit_exists", v13_audit_md.exists(), True))
    add(_expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION))
    add(_expect("source_status", source_decision.get("status"), SOURCE_READY_STATUS))
    add(_expect("source_passed", source_decision.get("passed"), True))
    add(_expect("source_failed_checks_empty", source_decision.get("failed_checks"), []))
    add(_expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work))
    add(_expect("source_implementation_complete", source_decision.get("fixed_dp_candidate_generation_implementation_complete"), True))
    add(_expect("source_post_review_authorized", source_decision.get("post_implementation_static_contract_review_authorized_next"), True))
    for flag in SOURCE_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))
    add(_expect("builder_manifest_written", generation_builder.get("manifest_written"), True))
    add(_expect("builder_guard_env_var", generation_builder.get("runbook_guard_env_var"), GUARD_ENV_VAR))
    zero_keys = set(_list(generation_builder.get("required_zero_overlap_keys")))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"builder_requires_zero_overlap_{key}", key in zero_keys, True))
    add(_expect("manifest_exists", manifest_path.exists(), True))
    add(_expect("runbook_exists", runbook_path.exists(), True))
    add(_expect("manifest_schema_version", manifest.get("schema_version"), MANIFEST_SCHEMA_VERSION))
    add(_expect("manifest_fixed_dp_generation_not_executed", manifest.get("fixed_dp_candidate_generation_executed"), False))
    add(_expect("manifest_candidate_generation_by_camp_false", manifest.get("candidate_generation_by_camp"), False))
    add(_expect("manifest_dp_modification_false", manifest.get("dp_modification"), False))
    add(_expect("runbook_guard_env_present", GUARD_ENV_VAR in runbook_text, True))
    add(_expect("runbook_checks_dp_head", "DP HEAD mismatch" in runbook_text, True))
    add(_expect("runbook_forbids_formal_seeds", "--forbid_formal_seeds 11 12 13" in runbook_text, True))
    add(_expect("runbook_writes_zero_overlap_registries", "--write_zero_overlap_registries" in runbook_text, True))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    for snippet in REQUIRED_SOURCE_SCRIPT_SNIPPETS:
        add(_expect(f"source_script_contains_{_slug(snippet)}", snippet in source_script_text, True))
    for snippet in REQUIRED_SOURCE_TEST_SNIPPETS:
        add(_expect(f"source_test_contains_{_slug(snippet)}", snippet in source_test_text, True))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(_expect("audit_authorizes_post_review", _latest_value(audit_text, "fixed_dp_candidate_generation_post_implementation_static_contract_review_authorized_next"), "True"))
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
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
        "fixed_dp_candidate_generation_post_implementation_static_contract_review_passed": passed,
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
    summary = _dict(report.get("artifact_summary"))
    failed = decision.get("failed_checks") or []
    return "\n".join(
        [
            "# Fixed-DP Candidate Generation Post-Implementation Static Contract Review",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{failed}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Execution preflight authorized next: `{decision.get('fixed_dp_candidate_generation_execution_preflight_authorized_next')}`",
            f"- Fixed-DP generation execution authorized next: `{decision.get('fixed_dp_candidate_generation_execution_authorized_next')}`",
            f"- Fixed-DP generation executed: `{decision.get('fixed_dp_candidate_generation_executed')}`",
            f"- CAMP candidate generation authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- Training preflight authorized next: `{decision.get('training_preflight_authorized_next')}`",
            f"- Training execution authorized next: `{decision.get('training_execution_authorized_next')}`",
            f"- DP modification authorized: `{decision.get('dp_modification_authorized')}`",
            f"- Manifest SHA256: `{summary.get('manifest_sha256')}`",
            f"- Runbook SHA256: `{summary.get('runbook_sha256')}`",
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
