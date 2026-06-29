#!/usr/bin/env python3
"""Plan non-overlap holdout data preparation after v13 result-review rejection.

This is a plan-only gate. It consumes the rejected static DP-reward result
readiness report and defines the contract for preparing a future independent
holdout/evaluation dataset. It does not run replay, generate fixed-DP
candidates, train CAMP, modify Diffusion Planner, promote artifacts, deploy, or
make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_plan_rejected"
)
SOURCE_REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "result_readiness_rejected"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_static_contract_review_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_STEPS_PER_LOG = 100
MINIMUM_HOLDOUT_SELECTION_LOGS = 32
MINIMUM_HOLDOUT_RECORDS = 3200
TARGET_HOLDOUT_SELECTION_LOGS = 128
TARGET_HOLDOUT_RECORDS = TARGET_HOLDOUT_SELECTION_LOGS * EXPECTED_STEPS_PER_LOG
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
FORMAL_SEEDS = [11, 12, 13]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only non-overlap holdout data preparation after v13 static "
            "DP-reward result-readiness rejection."
        )
    )
    parser.add_argument("--result_readiness_json", type=Path, required=True)
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
        result_readiness_json=args.result_readiness_json,
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
    result_readiness_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    result_readiness_json = result_readiness_json.resolve()
    v13_audit_md = v13_audit_md.resolve()
    result = _load_json_dict(result_readiness_json)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(result)
    holdout_plan = _holdout_plan(result)
    checks = _checks(
        result_readiness_json=result_readiness_json,
        v13_audit_md=v13_audit_md,
        result=result,
        audit_text=audit_text,
        source_summary=source_summary,
        holdout_plan=holdout_plan,
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
            "training_execution": False,
            "training_preflight": False,
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
            "result_readiness_json": str(result_readiness_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_summary": source_summary,
        "holdout_data_preparation_plan": holdout_plan,
        "plan_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "static_contract_review_authorized_next": passed,
            "implementation_authorized_next": False,
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
        },
    }


def _source_summary(result: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(result.get("final_decision"))
    analysis = _dict(result.get("analysis"))
    candidate_registry = _dict(result.get("candidate_tensor_hash_registry"))
    path_registry = _dict(result.get("path_signature_registry"))
    record_registry = _dict(result.get("record_identity_hash_registry"))
    overlap = _dict(result.get("candidate_tensor_overlap"))
    training = _dict(result.get("training_readiness"))
    split = _dict(result.get("split_manifest"))
    source_paths = _dict(result.get("source_paths"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "training_preflight_authorized_next": decision.get(
            "static_dp_reward_training_preflight_authorized_next"
        ),
        "training_execution_authorized_next": decision.get(
            "static_dp_reward_training_execution_authorized_next"
        ),
        "replay_executed": decision.get("replay_executed"),
        "training_executed": decision.get("training_executed"),
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
        "safety_benefit_claim_authorized": decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": decision.get(
            "camp_over_dp_top1_claim_authorized"
        ),
        "candidate_operation": analysis.get("candidate_operation"),
        "score_expression": analysis.get("score_expression"),
        "records_total": training.get("records_total"),
        "selection_log_count": training.get("selection_log_count"),
        "candidate_count_values": training.get("candidate_count_values"),
        "atom_count_values": training.get("atom_count_values"),
        "candidate_tensor_registry_intersection_count": candidate_registry.get(
            "intersection_count"
        ),
        "path_signature_registry_intersection_count": path_registry.get("intersection_count"),
        "record_identity_registry_intersection_count": record_registry.get(
            "intersection_count"
        ),
        "candidate_tensor_overlap_unique_intersection_count": overlap.get(
            "intersection_unique_hash_count"
        ),
        "candidate_tensor_overlap_rate": overlap.get("unique_intersection_rate"),
        "formal_holdout_seeds": split.get("formal_holdout_seeds"),
        "formal_training_seeds": split.get("formal_training_seeds"),
        "previous_training_summary_json": source_paths.get("previous_training_summary_json"),
        "previous_training_output_dir": source_paths.get("previous_training_output_dir"),
        "evaluation_output_dir": source_paths.get("evaluation_output_dir"),
        "split_manifest_json": source_paths.get("split_manifest_json"),
        "candidate_tensor_hash_registry_json": source_paths.get(
            "candidate_tensor_hash_registry_json"
        ),
        "path_signature_registry_json": source_paths.get("path_signature_registry_json"),
        "record_identity_hash_registry_json": source_paths.get(
            "record_identity_hash_registry_json"
        ),
    }


def _holdout_plan(result: dict[str, Any]) -> dict[str, Any]:
    summary = _source_summary(result)
    return {
        "status": "plan_ready_no_data_prepared",
        "data_preparation_performed_by_this_gate": False,
        "objective": (
            "prepare a future independent holdout/evaluation dataset whose "
            "fixed-DP candidate tensors, path signatures, and record identities "
            "have zero overlap with the prior training artifact and the rejected "
            "evaluation artifact"
        ),
        "minimum_scale": {
            "minimum_holdout_selection_logs": MINIMUM_HOLDOUT_SELECTION_LOGS,
            "minimum_holdout_records": MINIMUM_HOLDOUT_RECORDS,
            "expected_steps_per_log": EXPECTED_STEPS_PER_LOG,
        },
        "target_scale": {
            "target_holdout_selection_logs": TARGET_HOLDOUT_SELECTION_LOGS,
            "target_holdout_records": TARGET_HOLDOUT_RECORDS,
            "expected_candidate_count": EXPECTED_CANDIDATE_COUNT,
            "expected_atom_count": EXPECTED_ATOM_COUNT,
        },
        "exclusion_sources": {
            "previous_training_summary_json": summary["previous_training_summary_json"],
            "previous_training_output_dir": summary["previous_training_output_dir"],
            "rejected_evaluation_output_dir": summary["evaluation_output_dir"],
            "rejected_split_manifest_json": summary["split_manifest_json"],
            "rejected_candidate_tensor_hash_registry_json": summary[
                "candidate_tensor_hash_registry_json"
            ],
            "rejected_path_signature_registry_json": summary["path_signature_registry_json"],
            "rejected_record_identity_hash_registry_json": summary[
                "record_identity_hash_registry_json"
            ],
        },
        "required_nonoverlap_contracts": {
            "train_holdout_root_intersection_must_be_zero": True,
            "train_eval_candidate_tensor_intersection_must_be_zero": True,
            "train_eval_path_signature_intersection_must_be_zero": True,
            "train_eval_record_identity_intersection_must_be_zero": True,
            "holdout_must_exclude_rejected_eval_path_signatures": True,
            "holdout_must_exclude_rejected_eval_record_identities": True,
            "holdout_must_exclude_rejected_eval_candidate_tensors": True,
            "formal_seeds_11_12_13_excluded": True,
            "selection_log_count_check_required": True,
            "record_count_check_required": True,
            "sha256_manifest_required": True,
        },
        "future_data_preparation_steps": [
            "derive a candidate holdout scenario manifest from non-formal seeds only",
            "exclude all roots, path signatures, and record identities seen in prior training",
            "exclude all roots, path signatures, and record identities from the rejected evaluation",
            "run a later explicitly authorized fixed-DP candidate preparation gate only after static contract review",
            "materialize split, candidate tensor hash, path signature, and record identity registries",
            "rerun result-readiness and require all registry intersections to be zero before training preflight",
        ],
        "future_execution_constraints": {
            "fixed_dp_candidate_generation_requires_later_explicit_gate": True,
            "candidate_generation_by_camp_forbidden": True,
            "trajectory_generation_by_camp_forbidden": True,
            "trajectory_modification_by_camp_forbidden": True,
            "dp_modification_forbidden": True,
            "reference_blend_forbidden": True,
            "guidance_forbidden": True,
            "postprocess_or_postselection_forbidden": True,
            "closed_loop_outcome_input_forbidden": True,
            "executed_trajectory_must_remain_dp_top1": True,
        },
        "math_contract": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_only": True,
            "nonnegative_simplex_weights_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "blocked_by_this_plan": {
            "implementation": True,
            "training_preflight": True,
            "training_execution": True,
            "replay_execution": True,
            "fixed_dp_candidate_generation": True,
            "candidate_generation_by_camp": True,
            "dp_modification": True,
            "selector_promotion": True,
            "atom_promotion": True,
            "deployment": True,
            "deployable_checkpoint_claim": True,
            "safety_benefit_claim": True,
            "camp_over_dp_top1_claim": True,
        },
    }


def _checks(
    *,
    result_readiness_json: Path,
    v13_audit_md: Path,
    result: dict[str, Any],
    audit_text: str,
    source_summary: dict[str, Any],
    holdout_plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    failed_checks = source_summary.get("failed_checks") or []
    candidate_count_values = source_summary.get("candidate_count_values") or []
    atom_count_values = source_summary.get("atom_count_values") or []
    return [
        _check("result_readiness_json_exists", result_readiness_json.is_file(), str(result_readiness_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_gate_authorized_in_audit", f"next_work_target={authorized_current_work}" in audit_text, authorized_current_work, "present as next_work_target"),
        _check("current_status_result_review_rejected", "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_result_review_rejected_nonoverlap_registry_overlap_with_prior_training" in audit_text, "result_review_rejected_nonoverlap_registry_overlap_with_prior_training", "present in audit"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("required_dp_head_fixed", required_dp_head == FIXED_DP_HEAD, required_dp_head, FIXED_DP_HEAD),
        _check("source_schema_is_result_readiness_v2", result.get("schema_version") == "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_v2", result.get("schema_version"), "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_v2"),
        _check("source_result_readiness_rejected", source_summary["status"] == SOURCE_REJECT_STATUS, source_summary["status"], SOURCE_REJECT_STATUS),
        _check("source_result_readiness_failed", source_summary["passed"] is False, source_summary["passed"], False),
        _check("source_authorizes_no_next_work", source_summary["authorized_next_work"] is None, source_summary["authorized_next_work"], None),
        _check("source_failed_candidate_tensor_registry_intersection", "candidate_tensor_hash_registry_intersection_zero" in failed_checks, failed_checks, "candidate_tensor_hash_registry_intersection_zero"),
        _check("source_failed_path_signature_registry_intersection", "path_signature_registry_intersection_zero" in failed_checks, failed_checks, "path_signature_registry_intersection_zero"),
        _check("source_failed_record_identity_registry_intersection", "record_identity_hash_registry_intersection_zero" in failed_checks, failed_checks, "record_identity_hash_registry_intersection_zero"),
        _check("source_failed_candidate_overlap_rate", "candidate_tensor_overlap_rate_within_limit" in failed_checks, failed_checks, "candidate_tensor_overlap_rate_within_limit"),
        _check("candidate_registry_intersection_positive", _positive(source_summary["candidate_tensor_registry_intersection_count"]), source_summary["candidate_tensor_registry_intersection_count"], "> 0"),
        _check("path_registry_intersection_positive", _positive(source_summary["path_signature_registry_intersection_count"]), source_summary["path_signature_registry_intersection_count"], "> 0"),
        _check("record_registry_intersection_positive", _positive(source_summary["record_identity_registry_intersection_count"]), source_summary["record_identity_registry_intersection_count"], "> 0"),
        _check("candidate_overlap_intersection_positive", _positive(source_summary["candidate_tensor_overlap_unique_intersection_count"]), source_summary["candidate_tensor_overlap_unique_intersection_count"], "> 0"),
        _check("source_records_meet_minimum", _at_least(source_summary["records_total"], MINIMUM_HOLDOUT_RECORDS), source_summary["records_total"], f">= {MINIMUM_HOLDOUT_RECORDS}"),
        _check("source_logs_meet_minimum", _at_least(source_summary["selection_log_count"], MINIMUM_HOLDOUT_SELECTION_LOGS), source_summary["selection_log_count"], f">= {MINIMUM_HOLDOUT_SELECTION_LOGS}"),
        _check("source_candidate_count_expected", candidate_count_values == [EXPECTED_CANDIDATE_COUNT], candidate_count_values, [EXPECTED_CANDIDATE_COUNT]),
        _check("source_atom_count_expected", atom_count_values == [EXPECTED_ATOM_COUNT], atom_count_values, [EXPECTED_ATOM_COUNT]),
        _check("source_formal_holdout_seeds_empty", source_summary["formal_holdout_seeds"] in ([], None), source_summary["formal_holdout_seeds"], []),
        _check("source_formal_training_seeds_empty", source_summary["formal_training_seeds"] in ([], None), source_summary["formal_training_seeds"], []),
        _expect_summary(source_summary, "training_preflight_authorized_next", False),
        _expect_summary(source_summary, "training_execution_authorized_next", False),
        _expect_summary(source_summary, "replay_executed", False),
        _expect_summary(source_summary, "training_executed", False),
        _expect_summary(source_summary, "candidate_generation_executed", False),
        _expect_summary(source_summary, "candidate_generation_by_camp_authorized", False),
        _expect_summary(source_summary, "trajectory_generation_by_camp_authorized", False),
        _expect_summary(source_summary, "trajectory_modification_by_camp_authorized", False),
        _expect_summary(source_summary, "dp_modification_authorized", False),
        _expect_summary(source_summary, "selector_promotion_authorized", False),
        _expect_summary(source_summary, "atom_promotion_authorized", False),
        _expect_summary(source_summary, "deployment_authorized", False),
        _expect_summary(source_summary, "safety_benefit_claim_authorized", False),
        _expect_summary(source_summary, "camp_over_dp_top1_claim_authorized", False),
        _expect_summary(source_summary, "candidate_operation", "fixed DP candidate reranking only"),
        _expect_summary(source_summary, "score_expression", SCORE_EXPRESSION),
        _check("plan_prepares_no_data", holdout_plan["data_preparation_performed_by_this_gate"] is False, holdout_plan["data_preparation_performed_by_this_gate"], False),
        _check("plan_targets_larger_holdout_than_minimum", holdout_plan["target_scale"]["target_holdout_records"] > MINIMUM_HOLDOUT_RECORDS, holdout_plan["target_scale"]["target_holdout_records"], f"> {MINIMUM_HOLDOUT_RECORDS}"),
        _check("plan_requires_zero_candidate_intersection", holdout_plan["required_nonoverlap_contracts"]["train_eval_candidate_tensor_intersection_must_be_zero"] is True, True, True),
        _check("plan_requires_zero_path_intersection", holdout_plan["required_nonoverlap_contracts"]["train_eval_path_signature_intersection_must_be_zero"] is True, True, True),
        _check("plan_requires_zero_record_intersection", holdout_plan["required_nonoverlap_contracts"]["train_eval_record_identity_intersection_must_be_zero"] is True, True, True),
        _check("plan_excludes_formal_seeds", holdout_plan["required_nonoverlap_contracts"]["formal_seeds_11_12_13_excluded"] is True, True, True),
        _check("plan_forbids_camp_candidate_generation", holdout_plan["future_execution_constraints"]["candidate_generation_by_camp_forbidden"] is True, True, True),
        _check("plan_forbids_dp_modification", holdout_plan["future_execution_constraints"]["dp_modification_forbidden"] is True, True, True),
        _check("plan_preserves_affine_score", holdout_plan["math_contract"]["score_expression"] == SCORE_EXPRESSION, holdout_plan["math_contract"]["score_expression"], SCORE_EXPRESSION),
        _contains("audit_blocks_training_preflight", audit_text, "static_dp_reward_training_preflight_authorized_by_current_boundary=False"),
        _contains("audit_blocks_training_execution", audit_text, "training_execution_authorized_by_current_boundary=False"),
        _contains("audit_blocks_replay", audit_text, "replay_execution_authorized_by_current_boundary=False"),
        _contains("audit_blocks_fixed_dp_candidate_generation", audit_text, "fixed_dp_candidate_generation_authorized_by_current_boundary=False"),
        _contains("audit_blocks_camp_candidate_generation", audit_text, "candidate_generation_by_camp_authorized_by_current_boundary=False"),
        _contains("audit_blocks_dp_modification", audit_text, "dp_modification_authorized_by_current_boundary=False"),
        _contains("audit_blocks_formal_seeds", audit_text, "formal_seed_11_12_13_execution_authorized=False"),
        _contains("audit_blocks_promotion", audit_text, "selector_promotion_authorized=False"),
        _contains("audit_blocks_safety_claim", audit_text, "safety_benefit_claim_authorized=False"),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_summary"]
    plan = report["holdout_data_preparation_plan"]
    lines = [
        "# V13 Static DP-Reward Non-Overlap Holdout Data Preparation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Source result review status: `{summary['status']}`",
        f"- Candidate tensor registry intersection: `{summary['candidate_tensor_registry_intersection_count']}`",
        f"- Path signature registry intersection: `{summary['path_signature_registry_intersection_count']}`",
        f"- Record identity registry intersection: `{summary['record_identity_registry_intersection_count']}`",
        "",
        "## Objective",
        "",
        plan["objective"],
        "",
        "## Target Scale",
        "",
    ]
    for key, value in plan["target_scale"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Required Non-Overlap Contracts", ""])
    for key, value in plan["required_nonoverlap_contracts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Future Data Preparation Steps", ""])
    for item in plan["future_data_preparation_steps"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundary", ""])
    lines.append(
        "This gate is plan-only. It does not prepare data, run replay, generate "
        "fixed-DP candidates, generate or modify trajectories with CAMP, train "
        "CAMP, modify DP, promote, deploy, or authorize safety/CAMP-over-DP claims."
    )
    lines.append("")
    return "\n".join(lines)


def _expect_summary(summary: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(key, summary.get(key) == expected, summary.get(key), expected)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else None, needle)


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and value > 0


def _at_least(value: Any, threshold: int) -> bool:
    return isinstance(value, (int, float)) and value >= threshold


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
