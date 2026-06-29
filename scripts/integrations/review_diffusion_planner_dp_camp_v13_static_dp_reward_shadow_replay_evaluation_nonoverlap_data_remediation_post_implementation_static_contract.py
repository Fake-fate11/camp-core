#!/usr/bin/env python3
"""Post-implementation static review for v13 non-overlap remediation.

This gate is read-only. It verifies that the implemented result-readiness
hardening matches the non-overlap contract before returning control to the
read-only result-review gate. It does not run replay, generate candidates,
train CAMP, modify Diffusion Planner, promote artifacts, deploy, or make
safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_post_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_post_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_post_implementation_static_contract_review_rejected"
)
SOURCE_IMPLEMENTATION_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_v1"
)
SOURCE_IMPLEMENTATION_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "result_review_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CLI_ARGS = (
    "--split_manifest_json",
    "--candidate_tensor_hash_registry_json",
    "--path_signature_registry_json",
    "--record_identity_hash_registry_json",
)
EXPECTED_SOURCE_CHECKS = (
    "split_manifest_training_holdout_root_intersection_zero",
    "split_manifest_formal_seed_records_zero",
    "candidate_tensor_hash_registry_intersection_zero",
    "path_signature_registry_intersection_zero",
    "record_identity_hash_registry_intersection_zero",
    "candidate_tensor_hash_registry_eval_values_complete",
    "record_identity_hash_registry_eval_values_complete",
    "previous_training_summary_json",
    "_compare_candidate_tensor_hashes",
    "max_previous_overlap_rate",
    "FORMAL_SEEDS = {11, 12, 13}",
)
EXPECTED_TESTS = (
    "test_result_readiness_rejects_split_manifest_overlap",
    "test_result_readiness_rejects_formal_seed_in_split_manifest",
    "test_result_readiness_rejects_candidate_tensor_registry_overlap",
    "test_result_readiness_rejects_path_signature_registry_overlap",
    "test_result_readiness_rejects_record_identity_registry_overlap",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only post-implementation static contract review for v13 "
            "static DP-reward non-overlap data remediation."
        )
    )
    parser.add_argument("--implementation_json", type=Path, required=True)
    parser.add_argument("--result_readiness_py", type=Path, required=True)
    parser.add_argument("--result_readiness_test_py", type=Path, required=True)
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
        implementation_json=args.implementation_json,
        result_readiness_py=args.result_readiness_py,
        result_readiness_test_py=args.result_readiness_test_py,
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
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    implementation_json: Path,
    result_readiness_py: Path,
    result_readiness_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    implementation_json = implementation_json.resolve()
    result_readiness_py = result_readiness_py.resolve()
    result_readiness_test_py = result_readiness_test_py.resolve()
    v13_audit_md = v13_audit_md.resolve()

    implementation = _load_json_dict(implementation_json)
    result_readiness_text = _read_text(result_readiness_py)
    result_readiness_test_text = _read_text(result_readiness_test_py)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(implementation)

    checks = _checks(
        implementation_json=implementation_json,
        result_readiness_py=result_readiness_py,
        result_readiness_test_py=result_readiness_test_py,
        v13_audit_md=v13_audit_md,
        result_readiness_text=result_readiness_text,
        result_readiness_test_text=result_readiness_test_text,
        audit_text=audit_text,
        source_summary=source_summary,
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
            "result_readiness_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
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
        "inputs": {
            "implementation_json": str(implementation_json),
            "result_readiness_py": str(result_readiness_py),
            "result_readiness_test_py": str(result_readiness_test_py),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "implementation_json_sha256": _sha256(implementation_json)
            if implementation_json.is_file()
            else None,
            "result_readiness_py_sha256": _sha256(result_readiness_py)
            if result_readiness_py.is_file()
            else None,
            "result_readiness_test_py_sha256": _sha256(result_readiness_test_py)
            if result_readiness_test_py.is_file()
            else None,
            "v13_audit_md_sha256": _sha256(v13_audit_md)
            if v13_audit_md.is_file()
            else None,
        },
        "source_summary": source_summary,
        "review_checks": checks,
        "final_decision": _decision(
            passed,
            failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_summary"]
    lines = [
        "# V13 Static DP-Reward Non-Overlap Post-Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Result review authorized next: `{decision['result_review_authorized_next']}`",
        f"- Training preflight authorized next: `{decision['training_preflight_authorized_next']}`",
        f"- Replay authorized next: `{decision['replay_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Implementation Source",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Candidate operation: `{summary.get('candidate_operation')}`",
        f"- Score expression: `{summary.get('score_expression')}`",
        f"- Split manifest required: `{summary.get('split_manifest_json_required_by_result_readiness')}`",
        f"- Candidate registry required: `{summary.get('candidate_tensor_hash_registry_json_required_by_result_readiness')}`",
        f"- Path signature registry required: `{summary.get('path_signature_registry_json_required_by_result_readiness')}`",
        f"- Record identity registry required: `{summary.get('record_identity_hash_registry_json_required_by_result_readiness')}`",
        "",
        "This review is read-only. It does not run result review, replay, "
        "generate candidates, train CAMP, modify DP, promote, deploy, or "
        "authorize safety/CAMP-over-DP claims.",
        "",
    ]
    return "\n".join(lines)


def _source_summary(implementation: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(implementation.get("final_decision"))
    contracts = _dict(implementation.get("implemented_contracts"))
    math_boundary = _dict(implementation.get("math_boundary"))
    verification = _dict(implementation.get("verification"))
    source_hashes = _dict(implementation.get("source_hashes"))
    return {
        "schema_version": implementation.get("schema_version"),
        "status": implementation.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "training_executed": decision.get("training_executed"),
        "replay_executed": decision.get("replay_executed"),
        "candidate_generation_executed": decision.get("candidate_generation_executed"),
        "candidate_generation_by_camp_authorized": decision.get(
            "candidate_generation_by_camp_authorized"
        ),
        "trajectory_generation_by_camp_authorized": decision.get(
            "trajectory_generation_by_camp_authorized"
        ),
        "trajectory_modification_by_camp_authorized": decision.get(
            "trajectory_modification_by_camp_authorized"
        ),
        "dp_modification_authorized": decision.get("dp_modification_authorized"),
        "selector_promotion_authorized": decision.get("selector_promotion_authorized"),
        "atom_promotion_authorized": decision.get("atom_promotion_authorized"),
        "deployment_authorized": decision.get("deployment_authorized"),
        "deployable_checkpoint_claim_authorized": decision.get(
            "deployable_checkpoint_claim_authorized"
        ),
        "safety_benefit_claim_authorized": decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": decision.get("camp_over_dp_top1_claim_authorized"),
        "target_pytest_passed": verification.get("target_pytest_passed"),
        "target_pytest_count": verification.get("target_pytest_count"),
        "result_readiness_script_sha256": source_hashes.get("result_readiness_script_sha256"),
        "result_readiness_test_sha256": source_hashes.get("result_readiness_test_sha256"),
        "split_manifest_json_required_by_result_readiness": contracts.get(
            "split_manifest_json_required_by_result_readiness"
        ),
        "candidate_tensor_hash_registry_json_required_by_result_readiness": contracts.get(
            "candidate_tensor_hash_registry_json_required_by_result_readiness"
        ),
        "path_signature_registry_json_required_by_result_readiness": contracts.get(
            "path_signature_registry_json_required_by_result_readiness"
        ),
        "record_identity_hash_registry_json_required_by_result_readiness": contracts.get(
            "record_identity_hash_registry_json_required_by_result_readiness"
        ),
        "train_holdout_split_intersection_must_be_zero": contracts.get(
            "train_holdout_split_intersection_must_be_zero"
        ),
        "candidate_tensor_train_eval_intersection_must_be_zero": contracts.get(
            "candidate_tensor_train_eval_intersection_must_be_zero"
        ),
        "path_signature_train_eval_intersection_must_be_zero": contracts.get(
            "path_signature_train_eval_intersection_must_be_zero"
        ),
        "record_identity_train_eval_intersection_must_be_zero": contracts.get(
            "record_identity_train_eval_intersection_must_be_zero"
        ),
        "formal_seeds_11_12_13_rejected": contracts.get("formal_seeds_11_12_13_rejected"),
        "candidate_operation": math_boundary.get("candidate_operation"),
        "score_expression": math_boundary.get("score_expression"),
        "approved_atoms_nonnegative_simplex_only": math_boundary.get(
            "approved_atoms_nonnegative_simplex_only"
        ),
        "simplex_cvar_l2_master_convexity_preserved": math_boundary.get(
            "simplex_cvar_l2_master_convexity_preserved"
        ),
    }


def _checks(
    *,
    implementation_json: Path,
    result_readiness_py: Path,
    result_readiness_test_py: Path,
    v13_audit_md: Path,
    result_readiness_text: str,
    result_readiness_test_text: str,
    audit_text: str,
    source_summary: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    current_boundary = _current_v13_boundary(audit_text)
    checks = [
        _check("implementation_json_exists", implementation_json.is_file(), str(implementation_json), "file exists"),
        _check("result_readiness_py_exists", result_readiness_py.is_file(), str(result_readiness_py), "file exists"),
        _check("result_readiness_test_py_exists", result_readiness_test_py.is_file(), str(result_readiness_test_py), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_next_work_target", _latest_audit_value(audit_text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_latest_status_implementation_complete",
            _latest_audit_value(audit_text, "current_v13_status"),
            "static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_data_remediation_implementation_complete",
        ),
        _contains(
            "audit_current_boundary_authorizes_post_review",
            current_boundary,
            "static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_data_remediation_post_implementation_static_contract_review_authorized=True",
        ),
        _contains(
            "audit_current_boundary_blocks_training_preflight",
            current_boundary,
            "static_dp_reward_training_preflight_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_current_boundary_blocks_training_execution",
            current_boundary,
            "training_execution_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_current_boundary_blocks_replay",
            current_boundary,
            "replay_execution_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_current_boundary_blocks_candidate_generation",
            current_boundary,
            "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_current_boundary_blocks_dp_modification",
            current_boundary,
            "dp_modification_authorized_by_current_boundary=False",
        ),
        _expect_summary(source_summary, "schema_version", SOURCE_IMPLEMENTATION_SCHEMA_VERSION),
        _expect_summary(source_summary, "status", SOURCE_IMPLEMENTATION_STATUS),
        _expect_summary(source_summary, "passed", True),
        _expect_summary(source_summary, "failed_checks", []),
        _expect_summary(source_summary, "authorized_next_work", authorized_current_work),
        _expect_summary(source_summary, "target_pytest_passed", True),
        _expect_summary(source_summary, "target_pytest_count", 35),
        _expect_summary(source_summary, "split_manifest_json_required_by_result_readiness", True),
        _expect_summary(
            source_summary,
            "candidate_tensor_hash_registry_json_required_by_result_readiness",
            True,
        ),
        _expect_summary(
            source_summary,
            "path_signature_registry_json_required_by_result_readiness",
            True,
        ),
        _expect_summary(
            source_summary,
            "record_identity_hash_registry_json_required_by_result_readiness",
            True,
        ),
        _expect_summary(source_summary, "train_holdout_split_intersection_must_be_zero", True),
        _expect_summary(source_summary, "candidate_tensor_train_eval_intersection_must_be_zero", True),
        _expect_summary(source_summary, "path_signature_train_eval_intersection_must_be_zero", True),
        _expect_summary(source_summary, "record_identity_train_eval_intersection_must_be_zero", True),
        _expect_summary(source_summary, "formal_seeds_11_12_13_rejected", True),
        _expect_summary(source_summary, "candidate_operation", "fixed DP candidate reranking only"),
        _expect_summary(source_summary, "score_expression", SCORE_EXPRESSION),
        _expect_summary(source_summary, "approved_atoms_nonnegative_simplex_only", True),
        _expect_summary(source_summary, "simplex_cvar_l2_master_convexity_preserved", True),
        _expect_summary(source_summary, "training_executed", False),
        _expect_summary(source_summary, "replay_executed", False),
        _expect_summary(source_summary, "candidate_generation_executed", False),
        _expect_summary(source_summary, "candidate_generation_by_camp_authorized", False),
        _expect_summary(source_summary, "trajectory_generation_by_camp_authorized", False),
        _expect_summary(source_summary, "trajectory_modification_by_camp_authorized", False),
        _expect_summary(source_summary, "dp_modification_authorized", False),
        _expect_summary(source_summary, "selector_promotion_authorized", False),
        _expect_summary(source_summary, "atom_promotion_authorized", False),
        _expect_summary(source_summary, "deployment_authorized", False),
        _expect_summary(source_summary, "deployable_checkpoint_claim_authorized", False),
        _expect_summary(source_summary, "safety_benefit_claim_authorized", False),
        _expect_summary(source_summary, "camp_over_dp_top1_claim_authorized", False),
    ]
    if result_readiness_py.is_file():
        checks.extend(
            [
                _expect(
                    "result_readiness_source_hash_matches_implementation",
                    _sha256(result_readiness_py),
                    source_summary["result_readiness_script_sha256"],
                ),
            ]
        )
    if result_readiness_test_py.is_file():
        checks.extend(
            [
                _expect(
                    "result_readiness_test_hash_matches_implementation",
                    _sha256(result_readiness_test_py),
                    source_summary["result_readiness_test_sha256"],
                ),
            ]
        )
    for arg in EXPECTED_CLI_ARGS:
        checks.append(
            _contains(
                f"result_readiness_has_{_slug(arg)}",
                result_readiness_text,
                arg,
            )
        )
    for phrase in EXPECTED_SOURCE_CHECKS:
        checks.append(
            _contains(
                f"result_readiness_has_{_slug(phrase)}",
                result_readiness_text,
                phrase,
            )
        )
    for test_name in EXPECTED_TESTS:
        checks.append(
            _contains(
                f"result_readiness_test_has_{test_name}",
                result_readiness_test_text,
                test_name,
            )
        )
    return checks


def _decision(
    passed: bool,
    failed_checks: list[str],
    *,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed_checks,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "post_implementation_static_contract_review_complete": bool(passed),
        "result_review_authorized_next": bool(passed),
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
    }


def _expect_summary(summary: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _expect(key, summary.get(key), expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else None, needle)


def _current_v13_boundary(audit: str) -> str:
    marker = "\n## Current V13 "
    index = audit.rfind(marker)
    return audit[index + 1 :] if index >= 0 else audit


def _latest_audit_value(text: str, key: str) -> str | None:
    marker = f"{key}="
    if marker not in text:
        return None
    return text.rsplit(marker, maxsplit=1)[1].splitlines()[0].strip()


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _slug(value: str) -> str:
    return (
        value.replace("--", "")
        .replace("=", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("{", "")
        .replace("}", "")
        .replace(",", "")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .lower()
    )


if __name__ == "__main__":
    raise SystemExit(main())
