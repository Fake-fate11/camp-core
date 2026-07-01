#!/usr/bin/env python3
"""Post-implementation static review for the v13 missing-input materializer.

This gate is read-only. It verifies the implemented missing-input materializer
and its implementation artifact before authorizing only the next
input-materialization gate. It does not execute the materializer, run DP,
generate candidates, replay, train CAMP, modify DP, promote, deploy, or make
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
SOURCE_IMPLEMENTATION_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_artifact_v1"
)
SOURCE_IMPLEMENTATION_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_missing_input_"
    "materializer_implementation_complete"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_post_implementation_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_post_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_post_implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_failure_remediation_implementation_"
    "complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_input_materialization_only"
)
EXPECTED_MATERIALIZER_SCRIPT = (
    "scripts/integrations/materialize_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_missing_inputs.py"
)
EXPECTED_MATERIALIZER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_missing_input_materializer.py"
)
REQUIRED_ARTIFACT_FILES = (
    "HEADS",
    "COMMAND",
    "run.exit",
    "stdout.log",
    "stderr.log",
    "missing_input_materializer_implementation_report.json",
    "missing_input_materializer_implementation_report.md",
    "SHA256SUMS",
    "SHA256SUMS.check.exit",
    "SHA256SUMS.check.stdout",
    "SHA256SUMS.check.stderr",
)
REQUIRED_SCRIPT_TERMS = (
    "SCHEMA_VERSION",
    "DISABLED_STATUS",
    "READY_STATUS",
    "REJECT_STATUS",
    "AUTHORIZED_CURRENT_WORK",
    "AUTHORIZED_NEXT_WORK",
    "--enable_v13_fresh_evaluation_split_member_source_missing_input_materializer",
    "if not enabled:",
    "candidate_member_source_manifest.json",
    "training_split_manifest_roots.json",
    "candidate_member_source_manifest_provenance_report.json",
    "SHA256SUMS",
    "candidate_tensor_hashes",
    "path_signatures",
    "record_identity_hashes",
    "split_manifest_roots",
    "formal_seed",
    "full36",
    "rejected_overlap",
    "candidate_member_source_manifest_written",
    "training_split_manifest_roots_written",
    "input_materialization_execution_authorized_next",
    "fixed DP candidate reranking only",
    SCORE_EXPRESSION,
)
REQUIRED_TEST_TERMS = (
    "test_missing_input_materializer_default_off_has_no_outputs",
    "test_missing_input_materializer_writes_candidate_manifest_and_training_split_roots",
    "test_missing_input_materializer_rejects_formal_seed",
    "test_missing_input_materializer_rejects_full36",
    "test_missing_input_materializer_rejects_rejected_overlap_identity",
    "test_missing_input_materializer_rejects_empty_training_split_roots",
    "test_missing_input_materializer_rejects_static_review_sha_mismatch",
    "test_missing_input_materializer_main_writes_report",
)
SOURCE_FALSE_FLAGS = (
    "input_materialization_executed",
    "candidate_member_source_manifest_written",
    "training_split_manifest_roots_written",
    "validation_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "deployment_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "validation_preflight_authorized_next",
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only post-implementation static review for v13 missing inputs."
    )
    parser.add_argument("--implementation_artifact_dir", type=Path, required=True)
    parser.add_argument("--materializer_script_py", type=Path, required=True)
    parser.add_argument("--materializer_test_py", type=Path, required=True)
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
        implementation_artifact_dir=args.implementation_artifact_dir,
        materializer_script_py=args.materializer_script_py,
        materializer_test_py=args.materializer_test_py,
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
    implementation_artifact_dir: Path,
    materializer_script_py: Path,
    materializer_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "implementation_artifact_dir": implementation_artifact_dir.resolve(),
        "materializer_script_py": materializer_script_py.resolve(),
        "materializer_test_py": materializer_test_py.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    artifact_paths = {
        name: paths["implementation_artifact_dir"] / name
        for name in REQUIRED_ARTIFACT_FILES
    }
    source_report = _load_json_dict(
        artifact_paths["missing_input_materializer_implementation_report.json"]
    )
    script_text = _read_text(paths["materializer_script_py"])
    test_text = _read_text(paths["materializer_test_py"])
    audit_text = _read_text(paths["v13_audit_md"])
    checks = _checks(
        paths=paths,
        artifact_paths=artifact_paths,
        source_report=source_report,
        script_text=script_text,
        test_text=test_text,
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
            "post_implementation_static_contract_review_only": True,
            "input_materialization_execution": False,
            "materialization_execution": False,
            "validation_preflight_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
        },
        "paths": {key: str(value) for key, value in paths.items()},
        "artifact_summary": _artifact_summary(paths["implementation_artifact_dir"], source_report),
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
    paths: dict[str, Path],
    artifact_paths: dict[str, Path],
    source_report: dict[str, Any],
    script_text: str,
    test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    latest_status = _latest_value(audit_text, "current_v13_status")
    latest_target = _latest_value(audit_text, "next_work_target")
    checks = [
        _expect("current_camp_head_sha", _is_git_sha(current_camp_head), True),
        _expect("current_camp_origin_main_sha", _is_git_sha(current_camp_origin_main), True),
        _expect("current_camp_head_equals_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("materializer_script_path", _repo_path(paths["materializer_script_py"]), EXPECTED_MATERIALIZER_SCRIPT),
        _expect("materializer_test_path", _repo_path(paths["materializer_test_py"]), EXPECTED_MATERIALIZER_TEST),
        _expect("audit_latest_status", latest_status, LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", latest_target, authorized_current_work),
        _expect(
            "audit_missing_input_materializer_implemented",
            _contains(audit_text, "missing_input_materializer_implemented=True"),
            True,
        ),
        _expect(
            "audit_input_materialization_not_executed",
            _contains(audit_text, "input_materialization_executed=False"),
            True,
        ),
        _expect(
            "audit_candidate_manifest_not_written",
            _contains(audit_text, "candidate_member_source_manifest_written=False"),
            True,
        ),
        _expect(
            "audit_training_split_roots_not_written",
            _contains(audit_text, "training_split_manifest_roots_written=False"),
            True,
        ),
        _expect("source_schema", source_report.get("schema_version"), SOURCE_IMPLEMENTATION_SCHEMA_VERSION),
        _expect("source_status", source_report.get("status"), SOURCE_IMPLEMENTATION_STATUS),
        _expect("source_passed", source_report.get("passed"), True),
        _expect("source_py_compile_passed", source_report.get("py_compile_passed"), True),
        _expect("source_target_tests_passed", source_report.get("target_tests_passed"), True),
        _expect("source_dp_head", source_report.get("dp_head"), required_dp_head),
        _expect("source_required_dp_head", source_report.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("source_authorized_next_work", source_report.get("authorized_next_work"), authorized_current_work),
        _expect("source_script", source_report.get("script"), EXPECTED_MATERIALIZER_SCRIPT),
        _expect("source_test", source_report.get("test"), EXPECTED_MATERIALIZER_TEST),
        _expect("source_candidate_operation", source_report.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("source_score_expression", source_report.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_nonnegative_simplex", source_report.get("nonnegative_simplex_weights_only"), True),
        _expect("source_master_convex", source_report.get("master_problem_remains_convex"), True),
        _expect("artifact_run_exit_zero", _read_text(artifact_paths["run.exit"]).strip(), "0"),
        _expect("artifact_sha256sums_check_zero", _read_text(artifact_paths["SHA256SUMS.check.exit"]).strip(), "0"),
    ]
    for name, path in artifact_paths.items():
        checks.append(_expect(f"artifact_file_exists_{name}", path.is_file(), True))
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", source_report.get(flag), False))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _contains(audit_text, f"{flag}=False"), True))
    for term in REQUIRED_SCRIPT_TERMS:
        checks.append(_expect(f"materializer_contains_{_slug(term)}", term in script_text, True))
    for term in REQUIRED_TEST_TERMS:
        checks.append(_expect(f"test_contains_{term}", term in test_text, True))
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
        "post_implementation_static_contract_review_passed": passed,
        "input_materialization_execution_authorized_next": passed,
        "materialization_execution_authorized_next": passed,
        "materializer_execution_authorized_next": passed,
        "candidate_member_source_manifest_materialization_authorized_next": passed,
        "training_split_manifest_roots_materialization_authorized_next": passed,
        "validation_preflight_authorized_next": False,
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
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "nonnegative_simplex_weights_only": True,
        "master_problem_remains_convex": True,
    }


def _artifact_summary(root: Path, source_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_dir": str(root),
        "source_camp_head": source_report.get("camp_head"),
        "source_camp_origin_main": source_report.get("camp_origin_main"),
        "source_dp_head": source_report.get("dp_head"),
        "source_status": source_report.get("status"),
        "source_passed": source_report.get("passed"),
        "source_input_materialization_executed": source_report.get("input_materialization_executed"),
        "source_candidate_member_source_manifest_written": (
            source_report.get("candidate_member_source_manifest_written")
        ),
        "source_training_split_manifest_roots_written": (
            source_report.get("training_split_manifest_roots_written")
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    return "\n".join(
        [
            "# V13 Missing Input Materializer Post-Implementation Static Review",
            "",
            f"- status: {decision['status']}",
            f"- passed: {decision['passed']}",
            f"- authorized_next_work: {decision['authorized_next_work']}",
            f"- failed_checks: {', '.join(failed)}",
            f"- candidate_operation: {decision['candidate_operation']}",
            f"- score_expression: {decision['score_expression']}",
            f"- input_materialization_execution_authorized_next: {decision['input_materialization_execution_authorized_next']}",
            f"- training_execution_authorized_next: {decision['training_execution_authorized_next']}",
            f"- fixed_dp_candidate_generation_authorized_next: {decision['fixed_dp_candidate_generation_authorized_next']}",
            f"- candidate_generation_by_camp_authorized: {decision['candidate_generation_by_camp_authorized']}",
            f"- trajectory_modification_by_camp_authorized: {decision['trajectory_modification_by_camp_authorized']}",
            f"- dp_modification_authorized: {decision['dp_modification_authorized']}",
            f"- safety_benefit_claim_authorized: {decision['safety_benefit_claim_authorized']}",
            f"- camp_over_dp_top1_claim_authorized: {decision['camp_over_dp_top1_claim_authorized']}",
            "",
        ]
    )


def _repo_path(path: Path) -> str:
    normalized = path.as_posix()
    for marker in ("/scripts/", "/camp_core/tests/"):
        if marker in normalized:
            return normalized[normalized.index(marker) + 1 :]
    return normalized


def _latest_value(text: str, key: str) -> str | None:
    needle = f"{key}="
    if needle not in text:
        return None
    return text.rsplit(needle, maxsplit=1)[1].splitlines()[0].strip()


def _contains(text: str, needle: str) -> bool:
    return needle in text


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "actual": actual,
        "expected": expected,
    }


def _slug(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z_]+", "_", value).strip("_")[:96]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
