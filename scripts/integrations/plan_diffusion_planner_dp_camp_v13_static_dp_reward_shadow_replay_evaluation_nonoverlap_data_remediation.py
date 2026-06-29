#!/usr/bin/env python3
"""Plan non-overlap data remediation for v13 static DP-reward evaluation.

This is a plan-only gate. It consumes the read-only overlap failure diagnosis
and proposes the next contract needed before any new training preflight. It
does not run replay, generate candidates, train CAMP, modify Diffusion Planner,
promote artifacts, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_plan_rejected"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_static_contract_review_only"
)
DIAGNOSED_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "overlap_failure_diagnosed"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only non-overlap data remediation after a v13 static "
            "DP-reward evaluation overlap failure diagnosis."
        )
    )
    parser.add_argument("--overlap_failure_diagnosis_json", type=Path, required=True)
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
        overlap_failure_diagnosis_json=args.overlap_failure_diagnosis_json,
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
    overlap_failure_diagnosis_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    overlap_failure_diagnosis_json = overlap_failure_diagnosis_json.resolve()
    v13_audit_md = v13_audit_md.resolve()
    diagnosis = _load_json_dict(overlap_failure_diagnosis_json)
    audit_text = _read_text(v13_audit_md)
    remediation_plan = _remediation_plan()
    checks = _checks(
        overlap_failure_diagnosis_json=overlap_failure_diagnosis_json,
        v13_audit_md=v13_audit_md,
        audit_text=audit_text,
        diagnosis=diagnosis,
        remediation_plan=remediation_plan,
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
            "replay_execution": False,
            "candidate_generation_execution": False,
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
            "overlap_failure_diagnosis_json": str(overlap_failure_diagnosis_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "diagnosis_summary": _diagnosis_summary(diagnosis),
        "remediation_plan": remediation_plan,
        "review_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "static_contract_review_authorized_next": passed,
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
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _remediation_plan() -> dict[str, Any]:
    return {
        "objective": (
            "prevent static DP-reward training/evaluation readiness from using "
            "selection logs whose candidate tensors are already present in the "
            "training evidence source"
        ),
        "root_cause": (
            "prior training_summary.selection_logs included a previous "
            "evaluation replay root; the later evaluation reused the same "
            "route/seed/npc/spawn/tl/static_shadow path signatures and step "
            "candidate tensor hashes"
        ),
        "required_contracts": {
            "split_manifest_required": True,
            "training_selection_logs_must_exclude_holdout_roots": True,
            "holdout_selection_logs_must_exclude_training_roots": True,
            "candidate_tensor_hash_registry_required": True,
            "path_signature_registry_required": True,
            "record_identity_hash_registry_required": True,
            "train_eval_candidate_tensor_intersection_must_be_zero": True,
            "train_eval_path_signature_intersection_must_be_zero": True,
            "result_readiness_must_compare_against_all_training_summary_selection_logs": True,
            "formal_seeds_11_12_13_excluded": True,
        },
        "future_preflight_requirements": {
            "new_nonoverlap_source_root_required": True,
            "reuse_of_diagnosed_prior_eval_root_for_holdout_forbidden": True,
            "reuse_of_training_summary_selection_logs_for_holdout_forbidden": True,
            "minimum_holdout_records": 3200,
            "minimum_holdout_selection_logs": 32,
            "expected_candidate_count": 8,
            "expected_atom_count": 14,
            "fixed_dp_candidate_generation_requires_later_explicit_preflight": True,
        },
        "verification_requirements": {
            "sha256_artifact_manifest_required": True,
            "selection_log_count_check_required": True,
            "record_count_check_required": True,
            "candidate_tensor_hash_overlap_check_required": True,
            "path_signature_overlap_check_required": True,
            "same_signature_and_step_hash_overlap_check_required": True,
            "default_off_contract_validation_required": True,
            "affine_score_contract_required": True,
            "dp_head_fixed_check_required": True,
        },
        "blocked_by_this_plan": {
            "training_preflight": True,
            "training_execution": True,
            "replay_execution": True,
            "candidate_generation_execution": True,
            "candidate_generation_by_camp": True,
            "dp_modification": True,
            "selector_promotion": True,
            "atom_promotion": True,
            "deployment": True,
            "safety_benefit_claim": True,
            "camp_over_dp_top1_claim": True,
        },
    }


def _diagnosis_summary(diagnosis: dict[str, Any]) -> dict[str, Any]:
    final_decision = _dict(diagnosis.get("final_decision"))
    diagnosis_body = _dict(diagnosis.get("diagnosis"))
    path = _dict(diagnosis.get("path_provenance"))
    hashes = _dict(diagnosis.get("hash_provenance"))
    return {
        "status": final_decision.get("status"),
        "passed": final_decision.get("passed"),
        "failure_class": diagnosis_body.get("failure_class"),
        "current_evaluation_is_not_independent_holdout": diagnosis_body.get(
            "current_evaluation_is_not_independent_holdout"
        ),
        "evaluation_selection_log_count": path.get("evaluation_selection_log_count"),
        "previous_training_summary_selection_log_count": path.get(
            "previous_training_summary_selection_log_count"
        ),
        "evaluation_signatures_in_previous_count": path.get(
            "evaluation_signatures_in_previous_count"
        ),
        "matched_evaluation_record_count": hashes.get("matched_evaluation_record_count"),
        "same_signature_and_step_hash_match_records": hashes.get(
            "same_signature_and_step_hash_match_records"
        ),
        "matched_evaluation_record_rate": hashes.get("matched_evaluation_record_rate"),
    }


def _checks(
    *,
    overlap_failure_diagnosis_json: Path,
    v13_audit_md: Path,
    audit_text: str,
    diagnosis: dict[str, Any],
    remediation_plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    final_decision = _dict(diagnosis.get("final_decision"))
    diagnosis_body = _dict(diagnosis.get("diagnosis"))
    path = _dict(diagnosis.get("path_provenance"))
    hashes = _dict(diagnosis.get("hash_provenance"))
    eval_records = hashes.get("evaluation_record_count")
    return [
        _check("overlap_failure_diagnosis_json_exists", overlap_failure_diagnosis_json.is_file(), str(overlap_failure_diagnosis_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_gate_authorized_in_audit", f"next_work_target={authorized_current_work}" in audit_text, authorized_current_work, "present as next_work_target"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("diagnosis_status_passed", final_decision.get("passed") is True, final_decision.get("passed"), True),
        _check("diagnosis_status_expected", final_decision.get("status") == DIAGNOSED_STATUS, final_decision.get("status"), DIAGNOSED_STATUS),
        _check("diagnosis_requires_nonoverlap_data", diagnosis_body.get("nonoverlap_data_required_before_training_preflight") is True, diagnosis_body.get("nonoverlap_data_required_before_training_preflight"), True),
        _check("diagnosis_not_independent_holdout", diagnosis_body.get("current_evaluation_is_not_independent_holdout") is True, diagnosis_body.get("current_evaluation_is_not_independent_holdout"), True),
        _check("diagnosis_path_signatures_fully_overlap", path.get("evaluation_signatures_missing_in_previous_count") == 0, path.get("evaluation_signatures_missing_in_previous_count"), 0),
        _check("diagnosis_records_fully_overlap", hashes.get("matched_evaluation_record_count") == eval_records and eval_records not in (None, 0), hashes.get("matched_evaluation_record_count"), eval_records),
        _check("diagnosis_same_signature_step_fully_overlap", hashes.get("same_signature_and_step_hash_match_records") == eval_records and eval_records not in (None, 0), hashes.get("same_signature_and_step_hash_match_records"), eval_records),
        _check("plan_requires_hash_registry", remediation_plan["required_contracts"]["candidate_tensor_hash_registry_required"], True, True),
        _check("plan_blocks_training_preflight", remediation_plan["blocked_by_this_plan"]["training_preflight"], True, True),
        _check("plan_blocks_candidate_generation_execution", remediation_plan["blocked_by_this_plan"]["candidate_generation_execution"], True, True),
        _check("plan_preserves_affine_score_contract", remediation_plan["verification_requirements"]["affine_score_contract_required"], True, True),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["diagnosis_summary"]
    plan = report["remediation_plan"]
    lines = [
        "# V13 Static DP-Reward Non-Overlap Data Remediation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Diagnosis failure class: `{summary['failure_class']}`",
        f"- Matched evaluation records: `{summary['matched_evaluation_record_count']}`",
        f"- Same signature/step matches: `{summary['same_signature_and_step_hash_match_records']}`",
        "",
        "## Objective",
        "",
        plan["objective"],
        "",
        "## Required Contracts",
        "",
    ]
    for key, value in plan["required_contracts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Boundary", ""])
    lines.append(
        "This plan is read-only and plan-only. It does not run replay, generate "
        "candidates, train CAMP, modify DP, promote selectors or atoms, deploy, "
        "or make safety/CAMP-over-DP claims."
    )
    lines.append("")
    return "\n".join(lines)


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
