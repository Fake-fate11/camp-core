#!/usr/bin/env python3
"""Post-implementation static review for the v13 fresh split evaluator.

This gate is read-only over source, tests, and the v13 audit EOF. It verifies
that the implemented evaluator remains default-off, fail-closed, and limited to
existing fixed-DP candidate selection logs before authorizing only the fresh
evaluation execution gate. It does not evaluate logs, replay, generate
candidates, train CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP
claims.
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
    "dp_camp_v13_fresh_evaluation_split_evaluation_"
    "post_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_"
    "post_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_"
    "post_implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_implementation_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_post_implementation_"
    "static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_execution_only"
)
REQUIRED_SCRIPT_TERMS = (
    "DISABLED_STATUS",
    "READY_STATUS",
    "AUTHORIZED_CURRENT_WORK",
    "AUTHORIZED_NEXT_WORK",
    "--enable_v13_fresh_evaluation_split_evaluation",
    "validate_logs(selection_logs)",
    "selection_logs = sorted",
    "runtime_executed_output_dp_top1",
    "evaluation_executed_index_violations_zero",
    "evaluation_closed_loop_outcome_records_zero",
    "evaluation_affine_error_tiny",
    "\"replay_execution\": False",
    "\"fixed_dp_candidate_generation_execution\": False",
    "\"candidate_generation_by_camp\": False",
    "\"trajectory_generation_by_camp\": False",
    "\"trajectory_modification_by_camp\": False",
    "\"dp_modification\": False",
    "\"training_execution\": False",
    "\"executed_trajectory_change\": False",
    "\"candidate_operation\": \"fixed DP candidate reranking only\"",
    "\"score_expression\": SCORE_EXPRESSION",
    "\"fresh_evaluation_split_evaluation_executed\": bool(enabled and passed)",
    "\"training_preflight_authorized_next\": False",
    "\"training_execution_authorized_next\": False",
    "\"fixed_dp_candidate_generation_authorized_next\": False",
    "\"candidate_generation_by_camp_authorized\": False",
    "\"dp_modification_authorized\": False",
    "\"safety_benefit_claim_authorized\": False",
    "\"camp_over_dp_top1_claim_authorized\": False",
)
REQUIRED_TEST_TERMS = (
    "test_fresh_evaluation_split_evaluator_is_disabled_by_default",
    "test_fresh_evaluation_split_evaluator_accepts_default_off_shadow_logs",
    "test_fresh_evaluation_split_evaluator_rejects_wrong_audit_target",
    "test_fresh_evaluation_split_evaluator_rejects_selection_effect_or_executed_change",
    "test_fresh_evaluation_split_evaluator_main_writes_outputs",
)
CURRENT_AUDIT_FALSE_FLAGS = (
    "fresh_evaluation_split_evaluation_execution_authorized_next",
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
DECISION_FALSE_FLAGS = (
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "dp_modification_authorized",
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
    "fixed_dp_candidate_generation_executed",
    "replay_executed",
    "training_executed",
    "dp_modification_executed",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only post-implementation static review for v13 fresh split evaluation."
    )
    parser.add_argument("--evaluator_script_py", type=Path, required=True)
    parser.add_argument("--evaluator_test_py", type=Path, required=True)
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
        evaluator_script_py=args.evaluator_script_py,
        evaluator_test_py=args.evaluator_test_py,
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
    evaluator_script_py: Path,
    evaluator_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "evaluator_script_py": evaluator_script_py.resolve(),
        "evaluator_test_py": evaluator_test_py.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    script_text = _read_text(paths["evaluator_script_py"])
    test_text = _read_text(paths["evaluator_test_py"])
    audit_text = _read_text(paths["v13_audit_md"])
    review = {
        "read_only_static_review": True,
        "fresh_evaluation_execution_allowed_next": True,
        "training_preflight_allowed_next": False,
        "training_execution_allowed_next": False,
        "fixed_dp_candidate_generation_allowed_next": False,
        "candidate_generation_by_camp_allowed": False,
        "trajectory_generation_or_modification_by_camp_allowed": False,
        "dp_modification_allowed": False,
        "must_remain_default_off_shadow": True,
        "executed_trajectory_change_allowed": False,
        "score_expression": SCORE_EXPRESSION,
        "required_script_terms_missing": _missing_terms(script_text, REQUIRED_SCRIPT_TERMS),
        "required_test_terms_missing": _missing_terms(test_text, REQUIRED_TEST_TERMS),
    }
    checks = _checks(
        paths=paths,
        audit_text=audit_text,
        review=review,
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
            "fresh_evaluation_split_evaluation_execution": False,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_preflight": False,
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
            "deployable_checkpoint_claim": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "paths": {key: str(path) for key, path in paths.items()},
        "source_hashes": {
            key: _sha256(path) for key, path in paths.items() if path.is_file()
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "static_contract_review": review,
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
            "# V13 Fresh Evaluation Split Evaluation Post-Implementation Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Score expression: `{SCORE_EXPRESSION}`",
            "",
            "This gate authorizes only the read-only fresh evaluation execution over "
            "existing fixed-DP candidate logs. Training, replay, candidate generation, "
            "DP modification, promotion, deployment, safety claims, and CAMP-over-DP "
            "claims remain blocked.",
            "",
        ]
    )


def _checks(
    *,
    paths: dict[str, Path],
    audit_text: str,
    review: dict[str, Any],
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
        _check("evaluator_script_exists", paths["evaluator_script_py"].is_file(), str(paths["evaluator_script_py"]), "file exists"),
        _check("evaluator_test_exists", paths["evaluator_test_py"].is_file(), str(paths["evaluator_test_py"]), "file exists"),
        _check("v13_audit_md_exists", paths["v13_audit_md"].is_file(), str(paths["v13_audit_md"]), "file exists"),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_post_implementation_review_authorized",
            _latest_value(
                audit_text,
                "fresh_evaluation_split_evaluation_post_implementation_static_contract_review_authorized_next",
            ),
            "True",
        ),
        _expect(
            "audit_implementation_complete",
            _latest_value(audit_text, "fresh_evaluation_split_evaluation_implementation_complete"),
            "True",
        ),
        _check("script_required_terms_present", not review["required_script_terms_missing"], review["required_script_terms_missing"], []),
        _check("test_required_terms_present", not review["required_test_terms_missing"], review["required_test_terms_missing"], []),
        _expect("review_allows_only_fresh_evaluation_execution_next", review["fresh_evaluation_execution_allowed_next"], True),
        _expect("review_blocks_training_preflight", review["training_preflight_allowed_next"], False),
        _expect("review_blocks_training_execution", review["training_execution_allowed_next"], False),
        _expect("review_blocks_fixed_dp_candidate_generation", review["fixed_dp_candidate_generation_allowed_next"], False),
        _expect("review_blocks_camp_candidate_generation", review["candidate_generation_by_camp_allowed"], False),
        _expect("review_blocks_camp_trajectory_generation_or_modification", review["trajectory_generation_or_modification_by_camp_allowed"], False),
        _expect("review_blocks_dp_modification", review["dp_modification_allowed"], False),
        _expect("review_keeps_default_off_shadow", review["must_remain_default_off_shadow"], True),
        _expect("review_blocks_executed_trajectory_change", review["executed_trajectory_change_allowed"], False),
        _expect("review_score_affine", review["score_expression"], SCORE_EXPRESSION),
    ]
    for flag in CURRENT_AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    return checks


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "fresh_evaluation_split_evaluation_post_implementation_static_contract_review_passed": passed,
        "fresh_evaluation_split_evaluation_execution_authorized_next": passed,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    decision.update({flag: False for flag in DECISION_FALSE_FLAGS})
    return decision


def _missing_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term not in text]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
