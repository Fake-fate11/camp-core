#!/usr/bin/env python3
"""Post-implementation static review for the v13 member-source materializer.

This gate is read-only. It verifies that the implemented fresh member-source
materializer is default-off, fail-closed, and bounded to already materialized
candidate member-source plus registry inputs before authorizing only a future
materialization-only gate. It does not execute the materializer, run Diffusion
Planner, generate candidates, replay, train CAMP, modify DP, promote, deploy,
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
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "post_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "post_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "post_implementation_static_contract_review_rejected"
)
IMPLEMENTATION_VERIFICATION_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "implementation_verification_v1"
)
IMPLEMENTATION_VERIFICATION_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "implementation_verified"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_implementation_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_only"
)
REQUIRED_SCRIPT_TERMS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materializer_v1",
    "dp_camp_v13_fresh_evaluation_split_member_source_materializer_default_off_disabled",
    "--enable_v13_fresh_evaluation_split_member_source_materializer",
    "if not enabled:",
    "return report",
    "load_candidate_member_source_manifest_before_selection",
    "load_training_candidate_tensor_hash_registry_before_selection",
    "load_training_path_signature_registry_before_selection",
    "load_training_record_identity_registry_before_selection",
    "load_training_split_manifest_root_registry_before_selection",
    "load_recovered_prior_registry_before_selection",
    "load_rejected_overlap_source_registry_before_selection",
    "fail_closed_when_any_required_input_is_missing_empty_or_unreadable",
    "exclude_rejected_overlap_source_members",
    "exclude_formal_seeds_11_12_13_and_full36",
    "prove_zero_candidate_tensor_hash_intersection",
    "prove_zero_path_signature_intersection",
    "prove_zero_record_identity_intersection",
    "prove_zero_split_manifest_root_intersection",
    "reject_split_root_only_acceptance",
    "write_fresh_member_source_manifest_nonoverlap_report_preflight_inputs_and_sha256sums",
    "preserve_default_off_shadow_selector_and_executed_dp_top1",
    "forbid_camp_candidate_generation_or_trajectory_modification",
    "forbid_dp_code_config_or_weight_changes",
    "base._write_sha256sums",
    "member_source_manifest_written",
    "fixed DP candidate reranking only",
    "SCORE_EXPRESSION = base.SCORE_EXPRESSION",
    "\"nonnegative_simplex_weights_only\": True",
    "\"master_problem_remains_convex\": True",
    "\"fixed_dp_candidate_generation_execution\": False",
    "\"candidate_generation_by_camp\": False",
    "\"trajectory_generation_by_camp\": False",
    "\"trajectory_modification_by_camp\": False",
    "\"replay_execution\": False",
    "\"training_execution\": False",
    "\"dp_modification\": False",
)
REQUIRED_TEST_TERMS = (
    "test_member_source_materializer_is_default_off_and_has_no_side_effects",
    "test_member_source_materializer_writes_only_fresh_nonoverlap_outputs",
    "test_member_source_materializer_main_writes_report_and_sha256sums",
    "test_member_source_materializer_rejects_wrong_audit_target",
    "test_member_source_materializer_rejects_source_action_leak",
    "test_member_source_materializer_rejects_missing_registry",
    "test_member_source_materializer_rejects_split_root_only_acceptance",
    "test_member_source_materializer_excludes_formal_seeds_and_full36",
)
AUDIT_FALSE_FLAGS = (
    "implementation_execution_authorized_next",
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
    "fresh_member_selection_execution_authorized_next",
    "fresh_evaluation_split_evaluation_authorized_next",
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
        description=(
            "Read-only post-implementation static review for the v13 fresh "
            "evaluation split member-source materializer."
        )
    )
    parser.add_argument("--materializer_script_py", type=Path, required=True)
    parser.add_argument("--materializer_test_py", type=Path, required=True)
    parser.add_argument("--implementation_artifact_dir", type=Path, required=True)
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
        materializer_script_py=args.materializer_script_py,
        materializer_test_py=args.materializer_test_py,
        implementation_artifact_dir=args.implementation_artifact_dir,
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
    materializer_script_py: Path,
    materializer_test_py: Path,
    implementation_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "materializer_script_py": materializer_script_py.resolve(),
        "materializer_test_py": materializer_test_py.resolve(),
        "implementation_artifact_dir": implementation_artifact_dir.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    artifact_paths = _artifact_paths(paths["implementation_artifact_dir"])
    script_text = _read_text(paths["materializer_script_py"])
    test_text = _read_text(paths["materializer_test_py"])
    audit_text = _read_text(paths["v13_audit_md"])
    artifact_texts = {
        name: _read_text(path) for name, path in artifact_paths.items() if path.is_file()
    }
    verification_payload = _load_json_dict(artifact_paths["materialization_implementation_verification.json"])
    checks = _checks(
        paths=paths,
        artifact_paths=artifact_paths,
        script_text=script_text,
        test_text=test_text,
        audit_text=audit_text,
        artifact_texts=artifact_texts,
        verification_payload=verification_payload,
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
            "materializer_execution": False,
            "materialization_execution": False,
            "member_source_builder_execution": False,
            "fresh_evaluation_split_evaluation_execution": False,
            "data_preparation_execution": False,
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
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {name: str(path) for name, path in paths.items()},
        "artifact_inputs": {name: str(path) for name, path in artifact_paths.items()},
        "source_hashes": {
            "materializer_script_py_sha256": _sha256(paths["materializer_script_py"]),
            "materializer_test_py_sha256": _sha256(paths["materializer_test_py"]),
            "v13_audit_md_sha256": _sha256(paths["v13_audit_md"]),
        },
        "artifact_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in artifact_paths.items()
        },
        "implementation_artifact_summary": _artifact_summary(
            artifact_texts,
            verification_payload,
        ),
        "review_checks": checks,
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
            "# V13 Fresh Evaluation Split Member-Source Materializer Post-Implementation Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Materialization authorized next: `{decision['materialization_execution_authorized_next']}`",
            f"- Materializer executed by this gate: `{decision['materializer_executed']}`",
            f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
            f"- Replay authorized next: `{decision['replay_execution_authorized_next']}`",
            f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "The review is read-only and authorizes only a future materialization-only "
            "gate. It does not execute the materializer, run DP, generate "
            "candidates, replay, train CAMP, modify DP, promote, deploy, or "
            "authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _checks(
    *,
    paths: dict[str, Path],
    artifact_paths: dict[str, Path],
    script_text: str,
    test_text: str,
    audit_text: str,
    artifact_texts: dict[str, str],
    verification_payload: dict[str, Any],
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
        _check("implementation_artifact_dir_exists", paths["implementation_artifact_dir"].is_dir(), str(paths["implementation_artifact_dir"]), "directory exists"),
    ]
    for name in ("materializer_script_py", "materializer_test_py", "v13_audit_md"):
        checks.append(_check(f"{name}_exists", paths[name].is_file(), str(paths[name]), "file exists"))
    for name, path in artifact_paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    checks.extend(_artifact_checks(artifact_texts, verification_payload, authorized_current_work))
    checks.extend(_materializer_script_checks(script_text))
    checks.extend(_materializer_test_checks(test_text))
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _artifact_checks(
    texts: dict[str, str],
    payload: dict[str, Any],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    heads = _key_values(texts.get("HEADS", ""))
    command = texts.get("COMMAND", "")
    stdout = texts.get("stdout.log", "")
    stderr = texts.get("stderr.log", "")
    exit_text = texts.get("run.exit", "").strip()
    sha_check_exit = texts.get("SHA256SUMS.check.exit", "").strip()
    return [
        _expect("implementation_artifact_exit_zero", exit_text, "0"),
        _expect("implementation_artifact_sha256sums_check_zero", sha_check_exit, "0"),
        _expect("implementation_artifact_dp_head_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("implementation_artifact_payload_schema", payload.get("schema_version"), IMPLEMENTATION_VERIFICATION_SCHEMA_VERSION),
        _expect("implementation_artifact_payload_status", payload.get("status"), IMPLEMENTATION_VERIFICATION_STATUS),
        _expect("implementation_artifact_payload_passed", payload.get("passed"), True),
        _expect("implementation_artifact_payload_authorizes_this_review", payload.get("authorized_next_work"), authorized_current_work),
        _expect("implementation_artifact_materializer_execution_false", payload.get("materializer_execution"), False),
        _expect("implementation_artifact_materialization_executed_false", payload.get("materialization_executed"), False),
        _expect("implementation_artifact_fixed_dp_candidate_generation_false", payload.get("fixed_dp_candidate_generation_executed"), False),
        _expect("implementation_artifact_replay_false", payload.get("replay_executed"), False),
        _expect("implementation_artifact_training_false", payload.get("training_executed"), False),
        _expect("implementation_artifact_dp_modification_false", payload.get("dp_modification_executed"), False),
        _check("implementation_artifact_camp_head_is_sha", _is_git_sha(heads.get("camp_head", "")), heads.get("camp_head"), "git sha"),
        _contains("implementation_artifact_command_py_compile", command, "-m py_compile"),
        _contains("implementation_artifact_command_pytest", command, "-m pytest"),
        _contains("implementation_artifact_command_materializer_test", command, "test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materializer.py"),
        _contains("implementation_artifact_command_v13_audit_test", command, "test_diffusion_planner_v13_iteration_audit.py"),
        _contains("implementation_artifact_command_diff_check", command, "git diff --check"),
        _contains("implementation_artifact_stdout_tests_passed", stdout, "281 passed"),
        _expect("implementation_artifact_stderr_empty", stderr, ""),
    ]


def _materializer_script_checks(text: str) -> list[dict[str, Any]]:
    checks = [_contains(f"materializer_contains_{_slug(term)}", text, term) for term in REQUIRED_SCRIPT_TERMS]
    for forbidden in (
        "reference_blend\": True",
        "guidance\": True",
        "postprocess_or_postselection\": True",
        "closed_loop_outcome_authorized\": True",
        "dp_modification_authorized\": True",
        "safety_benefit_claim_authorized\": True",
        "camp_over_dp_top1_claim_authorized\": True",
    ):
        checks.append(
            _check(
                f"materializer_does_not_authorize_{_slug(forbidden)}",
                forbidden not in text,
                "absent" if forbidden not in text else "present",
                "absent",
            )
        )
    return checks


def _materializer_test_checks(text: str) -> list[dict[str, Any]]:
    return [_contains(f"test_contains_{_slug(term)}", text, term) for term in REQUIRED_TEST_TERMS]


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    checks = [
        _expect("audit_latest_status", _latest_value(text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_authorizes_post_review",
            _latest_value(
                text,
                "materialization_post_implementation_static_contract_review_authorized_next",
            ),
            "True",
        ),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(text, flag), "False"))
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
        "post_implementation_static_contract_review_complete": passed,
        "materialization_only_authorized_next": passed,
        "materialization_execution_authorized_next": passed,
        "materializer_execution_authorized_next": passed,
        "member_source_builder_execution_authorized_next": False,
        "fresh_evaluation_split_evaluation_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "materializer_executed": False,
        "materialization_executed": False,
        "member_source_builder_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "HEADS": root / "HEADS",
        "COMMAND": root / "COMMAND",
        "run.exit": root / "run.exit",
        "stdout.log": root / "stdout.log",
        "stderr.log": root / "stderr.log",
        "materialization_implementation_verification.json": (
            root / "materialization_implementation_verification.json"
        ),
        "materialization_implementation_verification.md": (
            root / "materialization_implementation_verification.md"
        ),
        "SHA256SUMS": root / "SHA256SUMS",
        "SHA256SUMS.check.exit": root / "SHA256SUMS.check.exit",
        "SHA256SUMS.check.stdout": root / "SHA256SUMS.check.stdout",
        "SHA256SUMS.check.stderr": root / "SHA256SUMS.check.stderr",
    }


def _artifact_summary(
    texts: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    heads = _key_values(texts.get("HEADS", ""))
    return {
        "camp_head": heads.get("camp_head"),
        "camp_origin_main": heads.get("camp_origin_main"),
        "dp_head": heads.get("dp_head"),
        "exit": texts.get("run.exit", "").strip(),
        "sha256sums_check_exit": texts.get("SHA256SUMS.check.exit", "").strip(),
        "status": payload.get("status"),
        "authorized_next_work": payload.get("authorized_next_work"),
        "stdout_contains_281_passed": "281 passed" in texts.get("stdout.log", ""),
        "stderr_empty": texts.get("stderr.log", "") == "",
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _key_values(text: str) -> dict[str, str]:
    values = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", maxsplit=1)
            values[key.strip()] = value.strip()
    return values


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


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
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")[:80]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
