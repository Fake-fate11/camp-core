#!/usr/bin/env python3
"""Plan-only gate for v13 fresh evaluation split evaluation.

This gate consumes the successful fresh evaluation split preflight artifact and
the static contract review artifact, then defines the future evaluation
implementation contract. It does not execute evaluation, run Diffusion Planner,
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
SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_evaluation_plan_v1"
READY_STATUS = "dp_camp_v13_fresh_evaluation_split_evaluation_plan_ready"
REJECT_STATUS = "dp_camp_v13_fresh_evaluation_split_evaluation_plan_rejected"
STATIC_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_static_contract_review_v1"
)
STATIC_REVIEW_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_static_contract_review_passed"
)
PREFLIGHT_SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_preflight_v1"
PREFLIGHT_STATUS = "dp_camp_v13_fresh_evaluation_split_preflight_passed"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_implementation_plan_only"
)
FUTURE_EVALUATION_SCRIPT = (
    "scripts/integrations/evaluate_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split.py"
)
FUTURE_EVALUATION_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_evaluator.py"
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
STATIC_REVIEW_FALSE_FLAGS = (
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
PREFLIGHT_FALSE_FLAGS = (
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
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
        description="Plan-only v13 fresh evaluation split evaluation gate."
    )
    parser.add_argument("--static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--preflight_artifact_dir", type=Path, required=True)
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
        static_review_artifact_dir=args.static_review_artifact_dir,
        preflight_artifact_dir=args.preflight_artifact_dir,
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
    static_review_artifact_dir: Path,
    preflight_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "static_review_artifact_dir": static_review_artifact_dir.resolve(),
        "preflight_artifact_dir": preflight_artifact_dir.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    static_paths = _static_artifact_paths(paths["static_review_artifact_dir"])
    preflight_paths = _preflight_artifact_paths(paths["preflight_artifact_dir"])
    static_texts = {
        name: _read_text(path) for name, path in static_paths.items() if path.is_file()
    }
    preflight_texts = {
        name: _read_text(path) for name, path in preflight_paths.items() if path.is_file()
    }
    static_review = _load_json_dict(
        static_paths["fresh_evaluation_split_evaluation_static_contract_review.json"]
    )
    preflight = _load_json_dict(preflight_paths["fresh_evaluation_split_preflight_report.json"])
    audit_text = _read_text(paths["v13_audit_md"])
    evaluation_plan = _evaluation_plan(static_review=static_review, preflight=preflight)
    checks = _checks(
        paths=paths,
        static_paths=static_paths,
        preflight_paths=preflight_paths,
        static_texts=static_texts,
        preflight_texts=preflight_texts,
        static_review=static_review,
        preflight=preflight,
        audit_text=audit_text,
        evaluation_plan=evaluation_plan,
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
            "plan_only": True,
            "read_only_inputs": True,
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
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_remains_convex": True,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {name: str(path) for name, path in paths.items()},
        "source_hashes": {
            "static_review_json_sha256": _sha256(
                static_paths["fresh_evaluation_split_evaluation_static_contract_review.json"]
            ),
            "preflight_json_sha256": _sha256(
                preflight_paths["fresh_evaluation_split_preflight_report.json"]
            ),
            "v13_audit_md_sha256": _sha256(paths["v13_audit_md"]),
        },
        "static_review_summary": _static_review_summary(static_review, static_texts),
        "preflight_summary": _preflight_summary(preflight, preflight_texts),
        "fresh_evaluation_split_evaluation_plan": evaluation_plan,
        "future_implementation_requirements": _future_implementation_requirements(),
        "forbidden_paths": _forbidden_paths(),
        "plan_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["fresh_evaluation_split_evaluation_plan"]
    return "\n".join(
        [
            "# V13 Fresh Evaluation Split Evaluation Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Plan-only gate: `{plan['plan_only_gate']}`",
            f"- Future evaluation execution by this gate: `{plan['evaluation_execution_by_this_gate']}`",
            f"- Future implementation script: `{plan['future_implementation']['script']}`",
            f"- Selected member count: `{plan['source_requirements']['selected_member_count']}`",
            f"- Score expression: `{plan['math_boundary']['score_expression']}`",
            "",
            "This plan-only gate does not execute evaluation, generate fixed-DP "
            "candidates, replay, train CAMP, modify DP, promote, deploy, or "
            "authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _evaluation_plan(*, static_review: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    preflight_result = _dict(preflight.get("preflight_result"))
    return {
        "objective": (
            "define a future read-only evaluator for the zero-overlap fresh "
            "evaluation split using already materialized fixed DP candidate "
            "tensors and current-tick candidate features"
        ),
        "plan_only_gate": True,
        "evaluation_execution_by_this_gate": False,
        "future_implementation": {
            "script": FUTURE_EVALUATION_SCRIPT,
            "test": FUTURE_EVALUATION_TEST,
            "must_fail_closed_before_execution": True,
            "requires_separate_static_contract_review": True,
            "requires_separate_preflight_before_execution": True,
        },
        "source_requirements": {
            "static_review_status": _dict(static_review.get("final_decision")).get("status"),
            "preflight_status": _dict(preflight.get("final_decision")).get("status"),
            "selected_member_count": preflight_result.get("selected_member_count"),
            "all_required_intersections_zero": preflight_result.get(
                "all_required_intersections_zero"
            ),
            "candidate_tensor_hash_intersection_count": preflight_result.get(
                "candidate_tensor_hash_intersection_count"
            ),
            "path_signature_intersection_count": preflight_result.get(
                "path_signature_intersection_count"
            ),
            "record_identity_intersection_count": preflight_result.get(
                "record_identity_intersection_count"
            ),
            "split_manifest_root_intersection_count": preflight_result.get(
                "split_manifest_root_intersection_count"
            ),
            "rejected_overlap_artifact_must_not_be_holdout": True,
            "split_root_zero_alone_is_insufficient": True,
        },
        "evaluation_contract": {
            "read_only_selection_logs": True,
            "read_only_candidate_tensors": True,
            "read_only_current_tick_candidate_atoms": True,
            "dp_top1_execution_remains_baseline": True,
            "shadow_selected_index_only": True,
            "executed_trajectory_change": False,
            "online_selector_change": False,
            "closed_loop_outcome_input": False,
            "training_input_from_future_evaluation": False,
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_only": True,
            "nonnegative_simplex_weights_only": True,
            "simplex_cvar_l2_master_remains_convex": True,
        },
        "failure_policy": {
            "fail_if_any_zero_overlap_count_is_nonzero": True,
            "fail_if_dp_head_drifts": True,
            "fail_if_static_review_or_preflight_missing": True,
            "fail_if_candidate_tensor_or_atom_schema_drifts": True,
            "fail_if_any_generation_or_modification_path_is_present": True,
        },
    }


def _future_implementation_requirements() -> dict[str, Any]:
    return {
        "inputs": [
            "fresh evaluation split member-source manifest",
            "fresh evaluation split non-overlap report",
            "fixed DP candidate tensor references",
            "default-off shadow selector runtime manifest",
            "approved atom feature schema",
        ],
        "required_checks": [
            "verify DP HEAD is fixed",
            "verify all four zero-overlap intersections remain zero",
            "verify formal seeds 11/12/13 and Full36 are absent",
            "verify candidate tensor hashes are already materialized fixed-DP outputs",
            "verify score remains affine in nonnegative simplex weights",
            "verify selected index is shadow-only and executed DP Top-1 is unchanged",
        ],
        "outputs": [
            "fresh_evaluation_split_evaluation_report.json",
            "fresh_evaluation_split_evaluation_report.md",
            "SHA256SUMS.artifact",
        ],
    }


def _forbidden_paths() -> dict[str, bool]:
    return {
        "execute_evaluation_in_this_gate": True,
        "run_diffusion_planner": True,
        "generate_fixed_dp_candidates": True,
        "generate_candidates_by_camp": True,
        "generate_trajectories_by_camp": True,
        "modify_or_blend_trajectories": True,
        "reference_blend": True,
        "guidance": True,
        "postprocess_or_postselection": True,
        "use_closed_loop_outcomes": True,
        "train_camp": True,
        "modify_dp": True,
        "change_online_selector": True,
        "promote_selector_or_atoms": True,
        "deploy": True,
        "claim_safety_benefit": True,
        "claim_camp_over_dp_top1": True,
    }


def _checks(
    *,
    paths: dict[str, Path],
    static_paths: dict[str, Path],
    preflight_paths: dict[str, Path],
    static_texts: dict[str, str],
    preflight_texts: dict[str, str],
    static_review: dict[str, Any],
    preflight: dict[str, Any],
    audit_text: str,
    evaluation_plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    static_decision = _dict(static_review.get("final_decision"))
    preflight_decision = _dict(preflight.get("final_decision"))
    preflight_result = _dict(preflight.get("preflight_result"))
    static_analysis = _dict(static_review.get("analysis"))
    preflight_analysis = _dict(preflight.get("analysis"))
    static_heads = _key_values(static_texts.get("HEADS", ""))
    preflight_heads = _key_values(preflight_texts.get("HEADS", ""))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("static_review_artifact_dir_exists", paths["static_review_artifact_dir"].is_dir(), str(paths["static_review_artifact_dir"]), "directory exists"),
        _check("preflight_artifact_dir_exists", paths["preflight_artifact_dir"].is_dir(), str(paths["preflight_artifact_dir"]), "directory exists"),
        _check("v13_audit_md_exists", paths["v13_audit_md"].is_file(), str(paths["v13_audit_md"]), "file exists"),
    ]
    for name, path in static_paths.items():
        checks.append(_check(f"static_{name}_exists", path.is_file(), str(path), "file exists"))
    for name, path in preflight_paths.items():
        checks.append(_check(f"preflight_{name}_exists", path.is_file(), str(path), "file exists"))
    checks.extend(
        [
            _expect("static_artifact_run_exit_zero", static_texts.get("run.exit", "").strip(), "0"),
            _expect("static_artifact_sha256_check_exit_zero", static_texts.get("SHA256SUMS_artifact.check.exit", "").strip(), "0"),
            _expect("static_artifact_dp_head_fixed", static_heads.get("dp_head"), FIXED_DP_HEAD),
            _expect("preflight_artifact_run_exit_zero", preflight_texts.get("run.exit", "").strip(), "0"),
            _expect("preflight_artifact_sha256_check_exit_zero", preflight_texts.get("SHA256SUMS_artifact.check.exit", "").strip(), "0"),
            _expect("preflight_artifact_dp_head_fixed", preflight_heads.get("dp_head"), FIXED_DP_HEAD),
            _expect("static_review_schema", static_review.get("schema_version"), STATIC_REVIEW_SCHEMA_VERSION),
            _expect("static_review_status", static_decision.get("status"), STATIC_REVIEW_STATUS),
            _expect("static_review_passed", static_decision.get("passed"), True),
            _expect("static_review_failed_checks_empty", static_decision.get("failed_checks"), []),
            _expect("static_review_authorizes_current_gate", static_decision.get("authorized_next_work"), authorized_current_work),
            _expect("static_review_plan_authorized", static_decision.get("fresh_evaluation_split_evaluation_plan_authorized_next"), True),
            _expect("static_review_candidate_operation", static_analysis.get("candidate_operation"), "fixed DP candidate reranking only"),
            _expect("static_review_score_affine", static_analysis.get("score_expression"), SCORE_EXPRESSION),
            _expect("preflight_schema", preflight.get("schema_version"), PREFLIGHT_SCHEMA_VERSION),
            _expect("preflight_status", preflight_decision.get("status"), PREFLIGHT_STATUS),
            _expect("preflight_passed", preflight_decision.get("passed"), True),
            _expect("preflight_failed_checks_empty", preflight_decision.get("failed_checks"), []),
            _expect("preflight_selected_member_count", preflight_result.get("selected_member_count"), 32),
            _expect("preflight_all_intersections_zero", preflight_result.get("all_required_intersections_zero"), True),
            _expect("preflight_candidate_operation", preflight_analysis.get("candidate_operation"), "fixed DP candidate reranking only"),
            _expect("preflight_score_affine", preflight_analysis.get("score_expression"), SCORE_EXPRESSION),
            _expect("plan_is_plan_only", evaluation_plan.get("plan_only_gate"), True),
            _expect("plan_does_not_execute_evaluation", evaluation_plan.get("evaluation_execution_by_this_gate"), False),
            _expect("plan_future_implementation_fail_closed", evaluation_plan["future_implementation"].get("must_fail_closed_before_execution"), True),
            _expect("plan_math_score_affine", evaluation_plan["math_boundary"].get("score_expression"), SCORE_EXPRESSION),
            _expect("plan_training_input_from_future_evaluation_false", evaluation_plan["evaluation_contract"].get("training_input_from_future_evaluation"), False),
        ]
    )
    for key in ZERO_INTERSECTION_KEYS:
        checks.append(_expect(f"preflight_zero_{key}", preflight_result.get(key), 0))
    for flag in STATIC_REVIEW_FALSE_FLAGS:
        checks.append(_expect(f"static_review_blocks_{flag}", static_decision.get(flag), False))
    for flag in PREFLIGHT_FALSE_FLAGS:
        checks.append(_expect(f"preflight_blocks_{flag}", preflight_decision.get(flag), False))
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    checks = [
        _expect("audit_latest_status", _latest_value(text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_authorizes_plan",
            _latest_value(text, "fresh_evaluation_split_evaluation_plan_authorized_next"),
            "True",
        ),
        _expect(
            "audit_keeps_evaluation_execution_blocked",
            _latest_value(text, "fresh_evaluation_split_evaluation_execution_authorized_next"),
            "False",
        ),
        _expect("audit_has_zero_overlap", _latest_value(text, "all_required_intersections_zero"), "True"),
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
        "fresh_evaluation_split_evaluation_plan_ready": passed,
        "fresh_evaluation_split_evaluation_implementation_plan_authorized_next": passed,
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


def _static_artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "HEADS": root / "HEADS",
        "COMMAND": root / "COMMAND",
        "run.exit": root / "run.exit",
        "stdout.txt": root / "stdout.txt",
        "stderr.txt": root / "stderr.txt",
        "fresh_evaluation_split_evaluation_static_contract_review.json": (
            root / "fresh_evaluation_split_evaluation_static_contract_review.json"
        ),
        "fresh_evaluation_split_evaluation_static_contract_review.md": (
            root / "fresh_evaluation_split_evaluation_static_contract_review.md"
        ),
        "SHA256SUMS.artifact": root / "SHA256SUMS.artifact",
        "SHA256SUMS_artifact.check.exit": root / "SHA256SUMS_artifact.check.exit",
        "SHA256SUMS_artifact.check.stdout": root / "SHA256SUMS_artifact.check.stdout",
        "SHA256SUMS_artifact.check.stderr": root / "SHA256SUMS_artifact.check.stderr",
    }


def _preflight_artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "HEADS": root / "HEADS",
        "COMMAND": root / "COMMAND",
        "run.exit": root / "run.exit",
        "stdout.txt": root / "stdout.txt",
        "stderr.txt": root / "stderr.txt",
        "fresh_evaluation_split_preflight_report.json": root / "fresh_evaluation_split_preflight_report.json",
        "fresh_evaluation_split_preflight_report.md": root / "fresh_evaluation_split_preflight_report.md",
        "SHA256SUMS.artifact": root / "SHA256SUMS.artifact",
        "SHA256SUMS_artifact.check.exit": root / "SHA256SUMS_artifact.check.exit",
        "SHA256SUMS_artifact.check.stdout": root / "SHA256SUMS_artifact.check.stdout",
        "SHA256SUMS_artifact.check.stderr": root / "SHA256SUMS_artifact.check.stderr",
    }


def _static_review_summary(report: dict[str, Any], texts: dict[str, str]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    preflight_result = _dict(report.get("preflight_result"))
    heads = _key_values(texts.get("HEADS", ""))
    return {
        "camp_head": heads.get("camp_head"),
        "camp_origin_main": heads.get("camp_origin_main"),
        "dp_head": heads.get("dp_head"),
        "exit": texts.get("run.exit", "").strip(),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_member_count": preflight_result.get("selected_member_count"),
        "all_required_intersections_zero": preflight_result.get(
            "all_required_intersections_zero"
        ),
    }


def _preflight_summary(report: dict[str, Any], texts: dict[str, str]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    result = _dict(report.get("preflight_result"))
    heads = _key_values(texts.get("HEADS", ""))
    return {
        "camp_head": heads.get("camp_head"),
        "camp_origin_main": heads.get("camp_origin_main"),
        "dp_head": heads.get("dp_head"),
        "exit": texts.get("run.exit", "").strip(),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_member_count": result.get("selected_member_count"),
        "all_required_intersections_zero": result.get("all_required_intersections_zero"),
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
