#!/usr/bin/env python3
"""Static review for the v13 fresh evaluation split evaluator implementation plan.

This gate consumes the implementation-plan artifact and verifies the future
evaluator contract before implementation is considered. It does not implement
or execute the evaluator, run Diffusion Planner, generate candidates, replay,
train CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
    "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_plan_v1"
)
SOURCE_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_implementation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_implementation_static_"
    "contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_implementation_only"
)
FUTURE_EVALUATOR_SCRIPT = (
    "scripts/integrations/evaluate_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split.py"
)
FUTURE_EVALUATOR_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_evaluator.py"
)
SOURCE_FALSE_FLAGS = (
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "fresh_evaluation_split_evaluation_executed",
    "fixed_dp_candidate_generation_executed",
    "replay_executed",
    "training_executed",
    "dp_modification_executed",
)
AUDIT_FALSE_FLAGS = (
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only static review for v13 fresh split evaluation implementation."
    )
    parser.add_argument("--implementation_plan_artifact_dir", type=Path, required=True)
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
        implementation_plan_artifact_dir=args.implementation_plan_artifact_dir,
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
    implementation_plan_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    artifact_dir = implementation_plan_artifact_dir.resolve()
    v13_audit_md = v13_audit_md.resolve()
    artifact_paths = _artifact_paths(artifact_dir)
    artifact_texts = {
        name: _read_text(path) for name, path in artifact_paths.items() if path.is_file()
    }
    source = _load_json_dict(
        artifact_paths["fresh_evaluation_split_evaluation_implementation_plan.json"]
    )
    audit_text = _read_text(v13_audit_md)
    review = _review_contract(source)
    checks = _checks(
        artifact_dir=artifact_dir,
        v13_audit_md=v13_audit_md,
        artifact_paths=artifact_paths,
        artifact_texts=artifact_texts,
        source=source,
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
            "implementation_execution": False,
            "evaluation_execution": False,
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
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "implementation_plan_artifact_dir": str(artifact_dir),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "implementation_plan_json_sha256": _sha256(
                artifact_paths["fresh_evaluation_split_evaluation_implementation_plan.json"]
            ),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": _source_summary(source, artifact_texts),
        "static_contract_review": review,
        "static_contract_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    return "\n".join(
        [
            "# V13 Fresh Evaluation Split Evaluation Implementation Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Future implementation allowed next: `{review['future_implementation_allowed_next']}`",
            f"- Evaluation execution authorized: `{decision['fresh_evaluation_split_evaluation_execution_authorized_next']}`",
            f"- Score expression: `{review['math_boundary']['score_expression']}`",
            "",
            "This static review authorizes only future implementation. It does "
            "not execute evaluation, replay, train CAMP, modify DP, promote, "
            "deploy, or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _review_contract(source: dict[str, Any]) -> dict[str, Any]:
    implementation_plan = _dict(source.get("implementation_plan"))
    future = _dict(implementation_plan.get("future_evaluator"))
    output_contract = _dict(future.get("output_contract"))
    return {
        "future_implementation_allowed_next": True,
        "implementation_execution_by_this_gate": False,
        "evaluation_execution_by_this_gate": False,
        "future_evaluator_script": future.get("script"),
        "future_evaluator_test": future.get("test"),
        "must_remain_default_off_shadow": output_contract.get("shadow_selected_index_only") is True,
        "executed_trajectory_change_allowed": output_contract.get("executed_trajectory_change") is True,
        "required_fail_closed_checks": implementation_plan.get("future_fail_closed_checks", []),
        "math_boundary": _dict(implementation_plan.get("math_boundary")),
    }


def _checks(
    *,
    artifact_dir: Path,
    v13_audit_md: Path,
    artifact_paths: dict[str, Path],
    artifact_texts: dict[str, str],
    source: dict[str, Any],
    audit_text: str,
    review: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    heads = _key_values(artifact_texts.get("HEADS", ""))
    decision = _dict(source.get("final_decision"))
    implementation_plan = _dict(source.get("implementation_plan"))
    future = _dict(implementation_plan.get("future_evaluator"))
    output_contract = _dict(future.get("output_contract"))
    source_invariants = _dict(implementation_plan.get("source_invariants"))
    math_boundary = _dict(implementation_plan.get("math_boundary"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("implementation_plan_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
    ]
    for name, path in artifact_paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    checks.extend(
        [
            _expect("artifact_run_exit_zero", artifact_texts.get("run.exit", "").strip(), "0"),
            _expect("artifact_sha256_check_exit_zero", artifact_texts.get("SHA256SUMS_artifact.check.exit", "").strip(), "0"),
            _expect("artifact_dp_head_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
            _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
            _expect("source_status", decision.get("status"), SOURCE_STATUS),
            _expect("source_passed", decision.get("passed"), True),
            _expect("source_failed_checks_empty", decision.get("failed_checks"), []),
            _expect("source_authorizes_current_gate", decision.get("authorized_next_work"), authorized_current_work),
            _expect(
                "source_static_review_authorized",
                decision.get("fresh_evaluation_split_evaluation_implementation_static_contract_review_authorized_next"),
                True,
            ),
            _expect("source_no_implementation_execution", implementation_plan.get("implementation_execution_by_this_gate"), False),
            _expect("source_no_evaluation_execution", implementation_plan.get("evaluation_execution_by_this_gate"), False),
            _expect("source_future_script", future.get("script"), FUTURE_EVALUATOR_SCRIPT),
            _expect("source_future_test", future.get("test"), FUTURE_EVALUATOR_TEST),
            _expect("source_shadow_selected_index_only", output_contract.get("shadow_selected_index_only"), True),
            _expect("source_no_executed_trajectory_change", output_contract.get("executed_trajectory_change"), False),
            _expect("source_selected_member_count", source_invariants.get("selected_member_count"), 32),
            _expect("source_all_intersections_zero", source_invariants.get("all_required_intersections_zero"), True),
            _expect("source_score_affine", math_boundary.get("score_expression"), SCORE_EXPRESSION),
            _expect("source_candidate_operation", math_boundary.get("candidate_operation"), "fixed DP candidate reranking only"),
            _expect("review_allows_future_implementation", review.get("future_implementation_allowed_next"), True),
            _expect("review_does_not_execute_implementation", review.get("implementation_execution_by_this_gate"), False),
            _expect("review_does_not_execute_evaluation", review.get("evaluation_execution_by_this_gate"), False),
            _expect("review_shadow_default_off", review.get("must_remain_default_off_shadow"), True),
            _expect("review_executed_change_not_allowed", review.get("executed_trajectory_change_allowed"), False),
            _expect("review_score_affine", review["math_boundary"].get("score_expression"), SCORE_EXPRESSION),
        ]
    )
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", decision.get(flag), False))
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    checks = [
        _expect("audit_latest_status", _latest_value(text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_authorizes_static_review",
            _latest_value(
                text,
                "fresh_evaluation_split_evaluation_implementation_static_contract_review_authorized_next",
            ),
            "True",
        ),
        _expect(
            "audit_keeps_evaluation_execution_blocked",
            _latest_value(text, "fresh_evaluation_split_evaluation_execution_authorized_next"),
            "False",
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
        "fresh_evaluation_split_evaluation_implementation_static_contract_review_passed": passed,
        "fresh_evaluation_split_evaluation_implementation_authorized_next": passed,
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
        "fresh_evaluation_split_evaluation_executed": False,
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
        "stdout.txt": root / "stdout.txt",
        "stderr.txt": root / "stderr.txt",
        "fresh_evaluation_split_evaluation_implementation_plan.json": (
            root / "fresh_evaluation_split_evaluation_implementation_plan.json"
        ),
        "fresh_evaluation_split_evaluation_implementation_plan.md": (
            root / "fresh_evaluation_split_evaluation_implementation_plan.md"
        ),
        "SHA256SUMS.artifact": root / "SHA256SUMS.artifact",
        "SHA256SUMS_artifact.check.exit": root / "SHA256SUMS_artifact.check.exit",
        "SHA256SUMS_artifact.check.stdout": root / "SHA256SUMS_artifact.check.stdout",
        "SHA256SUMS_artifact.check.stderr": root / "SHA256SUMS_artifact.check.stderr",
    }


def _source_summary(source: dict[str, Any], texts: dict[str, str]) -> dict[str, Any]:
    heads = _key_values(texts.get("HEADS", ""))
    decision = _dict(source.get("final_decision"))
    implementation_plan = _dict(source.get("implementation_plan"))
    source_invariants = _dict(implementation_plan.get("source_invariants"))
    return {
        "camp_head": heads.get("camp_head"),
        "camp_origin_main": heads.get("camp_origin_main"),
        "dp_head": heads.get("dp_head"),
        "exit": texts.get("run.exit", "").strip(),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_member_count": source_invariants.get("selected_member_count"),
        "all_required_intersections_zero": source_invariants.get("all_required_intersections_zero"),
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


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


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
