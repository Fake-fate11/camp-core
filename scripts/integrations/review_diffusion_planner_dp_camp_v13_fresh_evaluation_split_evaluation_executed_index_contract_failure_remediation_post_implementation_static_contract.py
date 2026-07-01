#!/usr/bin/env python3
"""Post-implementation static review for executed-index remediation.

This gate is read-only over source, focused tests, the implementation
verification artifact, and the v13 audit EOF. It verifies that the implemented
member-source filter rejects legacy non-default-off selection logs before any
new member-source rematerialization is planned. It does not materialize member
sources, run evaluation, replay, generate candidates, train CAMP, modify DP,
promote, deploy, or make safety/CAMP-over-DP claims.
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
RUNTIME_SCHEMA = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_post_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_post_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_post_implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_"
    "implementation_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fresh_member_source_rematerialization_plan_only"
)
REQUIRED_BUILDER_TERMS = (
    "DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION",
    RUNTIME_SCHEMA,
    "_member_default_off_contract_errors",
    "_load_selection_records",
    "source_path.is_file()",
    "default_off_contract_source_path_not_file",
    "default_off_contract_selected_index_not_dp_top1",
    "default_off_contract_executed_index_not_dp_top1",
    "default_off_contract_shadow_selected_index_missing",
    "default_off_contract_shadow_selected_index_out_of_range",
    "default_off_contract_default_off_shadow_selector_missing",
    "selected_default_off_contract_failures_zero",
    "rejected_default_off_contract_failed_count",
    "\"candidate_operation\": \"fixed DP candidate reranking only\"",
    "\"score_expression\": SCORE_EXPRESSION",
)
REQUIRED_BUILDER_TEST_TERMS = (
    "test_member_source_builder_rejects_legacy_non_default_off_selection_log",
    "rejected_default_off_contract_failed_count",
    "selected_index=3",
    "executed_index=3",
    "include_selector=False",
    "_selection_log",
)
REQUIRED_MATERIALIZER_TEST_TERMS = (
    "test_member_source_materializer_rejects_legacy_non_default_off_selection_log",
    "rejected_default_off_contract_failed_count",
    "selected_index=3",
    "executed_index=3",
    "include_selector=False",
    "_selection_log",
)
AUDIT_FALSE_FLAGS = (
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only post-implementation static review for executed-index remediation."
    )
    parser.add_argument("--member_source_builder_script_py", type=Path, required=True)
    parser.add_argument("--member_source_builder_test_py", type=Path, required=True)
    parser.add_argument("--member_source_materializer_test_py", type=Path, required=True)
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
        member_source_builder_script_py=args.member_source_builder_script_py,
        member_source_builder_test_py=args.member_source_builder_test_py,
        member_source_materializer_test_py=args.member_source_materializer_test_py,
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
    member_source_builder_script_py: Path,
    member_source_builder_test_py: Path,
    member_source_materializer_test_py: Path,
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
        "member_source_builder_script_py": member_source_builder_script_py.resolve(),
        "member_source_builder_test_py": member_source_builder_test_py.resolve(),
        "member_source_materializer_test_py": member_source_materializer_test_py.resolve(),
        "implementation_artifact_dir": implementation_artifact_dir.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    artifact_paths = _artifact_paths(paths["implementation_artifact_dir"])
    source_texts = {name: _read_text(path) for name, path in paths.items()}
    artifact_texts = {
        name: _read_text(path) for name, path in artifact_paths.items() if path.is_file()
    }
    checks = _checks(
        paths=paths,
        artifact_paths=artifact_paths,
        source_texts=source_texts,
        artifact_texts=artifact_texts,
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
            "fresh_member_source_materialization_execution": False,
            "fresh_evaluation_split_evaluation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "replay_execution": False,
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
        "inputs": {name: str(path) for name, path in paths.items()},
        "artifact_inputs": {name: str(path) for name, path in artifact_paths.items()},
        "source_hashes": {
            name: _sha256(path) for name, path in paths.items() if path.is_file()
        },
        "artifact_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in artifact_paths.items()
        },
        "implementation_artifact_summary": _artifact_summary(artifact_texts),
        "static_contract_review": {
            "required_builder_terms_missing": _missing_terms(
                source_texts["member_source_builder_script_py"], REQUIRED_BUILDER_TERMS
            ),
            "required_builder_test_terms_missing": _missing_terms(
                source_texts["member_source_builder_test_py"],
                REQUIRED_BUILDER_TEST_TERMS,
            ),
            "required_materializer_test_terms_missing": _missing_terms(
                source_texts["member_source_materializer_test_py"],
                REQUIRED_MATERIALIZER_TEST_TERMS,
            ),
            "source_path_file_required": True,
            "default_off_shadow_selector_schema_required": RUNTIME_SCHEMA,
            "selected_index_must_remain_dp_top1_zero": True,
            "executed_index_must_remain_dp_top1_zero": True,
            "shadow_selected_index_required_for_camp_choice": True,
            "legacy_non_default_off_selection_logs_rejected": True,
            "score_expression": SCORE_EXPRESSION,
            "next_gate_reason": (
                "the old evaluation member source cannot be reused; a fresh "
                "member-source rematerialization plan is required first"
            ),
        },
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
            "# V13 Executed-Index Contract Remediation Post-Implementation Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Rematerialization plan authorized next: `{decision['fresh_member_source_rematerialization_plan_authorized_next']}`",
            f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "The review is read-only. It authorizes only a future plan for "
            "fresh member-source rematerialization, because the rejected legacy "
            "evaluation member source cannot be reused as a holdout. It does "
            "not run DP, generate candidates, replay, train CAMP, modify DP, "
            "promote, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _checks(
    *,
    paths: dict[str, Path],
    artifact_paths: dict[str, Path],
    source_texts: dict[str, str],
    artifact_texts: dict[str, str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    audit_text = source_texts["v13_audit_md"]
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("implementation_artifact_dir_exists", paths["implementation_artifact_dir"].is_dir(), str(paths["implementation_artifact_dir"]), "directory exists"),
    ]
    for name in (
        "member_source_builder_script_py",
        "member_source_builder_test_py",
        "member_source_materializer_test_py",
        "v13_audit_md",
    ):
        checks.append(_check(f"{name}_exists", paths[name].is_file(), str(paths[name]), "file exists"))
    for name, path in artifact_paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    checks.extend(_artifact_checks(artifact_texts))
    checks.extend(
        _term_checks(
            "builder",
            source_texts["member_source_builder_script_py"],
            REQUIRED_BUILDER_TERMS,
        )
    )
    checks.extend(
        _term_checks(
            "builder_test",
            source_texts["member_source_builder_test_py"],
            REQUIRED_BUILDER_TEST_TERMS,
        )
    )
    checks.extend(
        _term_checks(
            "materializer_test",
            source_texts["member_source_materializer_test_py"],
            REQUIRED_MATERIALIZER_TEST_TERMS,
        )
    )
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _artifact_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    heads = _key_values(texts.get("HEADS.txt", ""))
    command = texts.get("COMMAND.sh", "")
    stdout = texts.get("stdout.txt", "")
    stderr = texts.get("stderr.txt", "")
    return [
        _expect("implementation_artifact_exit_zero", texts.get("run.exit", "").strip(), "0"),
        _expect(
            "implementation_artifact_sha256sums_check_zero",
            texts.get("sha256sums.check.exit", "").strip(),
            "0",
        ),
        _expect("implementation_artifact_dp_head_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _check("implementation_artifact_camp_head_is_sha", _is_git_sha(heads.get("camp_head", "")), heads.get("camp_head"), "git sha"),
        _contains("implementation_artifact_command_py_compile", command, "-m py_compile"),
        _contains("implementation_artifact_command_pytest", command, "-m pytest"),
        _contains("implementation_artifact_command_builder_test", command, "test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_builder.py"),
        _contains("implementation_artifact_command_materializer_test", command, "test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materializer.py"),
        _contains("implementation_artifact_stdout_tests_passed", stdout, "317 passed"),
        _expect("implementation_artifact_stderr_empty", stderr, ""),
    ]


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    checks = [
        _expect("audit_latest_status", _latest_value(text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_authorizes_post_review",
            _latest_value(
                text,
                "fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_post_implementation_static_contract_review_authorized_next",
            ),
            "True",
        ),
        _expect(
            "audit_implementation_complete",
            _latest_value(
                text,
                "fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_implementation_complete",
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
        "fresh_member_source_rematerialization_plan_authorized_next": passed,
        "fresh_member_source_materialization_executed": False,
        "fresh_evaluation_split_evaluation_executed": False,
        "fresh_evaluation_split_evaluation_execution_authorized_next": False,
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
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "HEADS.txt": root / "HEADS.txt",
        "COMMAND.sh": root / "COMMAND.sh",
        "run.exit": root / "run.exit",
        "stdout.txt": root / "stdout.txt",
        "stderr.txt": root / "stderr.txt",
        "SHA256SUMS": root / "SHA256SUMS",
        "sha256sums.check.exit": root / "sha256sums.check.exit",
        "sha256sums.check.stdout": root / "sha256sums.check.stdout",
        "sha256sums.check.stderr": root / "sha256sums.check.stderr",
    }


def _artifact_summary(texts: dict[str, str]) -> dict[str, Any]:
    heads = _key_values(texts.get("HEADS.txt", ""))
    return {
        "camp_head": heads.get("camp_head"),
        "camp_origin_main": heads.get("camp_origin_main"),
        "dp_head": heads.get("dp_head"),
        "exit": texts.get("run.exit", "").strip(),
        "sha256sums_check_exit": texts.get("sha256sums.check.exit", "").strip(),
        "stdout_contains_317_passed": "317 passed" in texts.get("stdout.txt", ""),
        "stderr_empty": texts.get("stderr.txt", "") == "",
    }


def _term_checks(prefix: str, text: str, terms: tuple[str, ...]) -> list[dict[str, Any]]:
    return [_contains(f"{prefix}_contains_{_slug(term)}", text, term) for term in terms]


def _missing_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term not in text]


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
