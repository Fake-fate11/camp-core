#!/usr/bin/env python3
"""Plan implementation for v13 materialization failure remediation.

This gate consumes the passed failure-remediation plan and defines the future
implementation contract for producing the missing candidate member-source
manifest and training split-root registry inputs. It is plan-only: it does not
implement code, materialize inputs, run DP, generate candidates, replay, train
CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_plan_v1"
)
SOURCE_PLAN_READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_failure_remediation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_static_contract_review_only"
)
FUTURE_INPUT_MATERIALIZER_SCRIPT = (
    "scripts/integrations/materialize_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_missing_inputs.py"
)
FUTURE_INPUT_MATERIALIZER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_missing_input_materializer.py"
)
FUTURE_OUTPUTS = (
    "candidate_member_source_manifest.json",
    "training_split_manifest_roots.json",
    "candidate_member_source_manifest_provenance_report.json",
    "SHA256SUMS",
)
REQUIRED_MEMBER_FIELDS = (
    "member_id",
    "source_path",
    "route",
    "seed",
    "candidate_tensor_hashes",
    "path_signatures",
    "record_identity_hashes",
    "split_manifest_roots",
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
BLOCKED_SOURCE_FLAGS = (
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
    "validation_preflight_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
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
REQUIRED_IMPLEMENTATION_CONTRACTS = (
    "read_only_existing_fixed_dp_current_source_artifacts",
    "derive_candidate_members_only_from_explicit_candidate_tensor_and_identity_evidence",
    "write_nonempty_candidate_member_source_manifest_or_reject",
    "write_nonempty_training_split_manifest_root_registry_or_reject",
    "require_member_id_source_path_route_seed_and_four_identity_sets",
    "exclude_full36_and_formal_seeds_11_12_13",
    "exclude_rejected_overlap_source_as_holdout_or_training_data",
    "reject_split_root_zero_alone_acceptance",
    "require_future_zero_overlap_preflight_before_training",
    "preserve_affine_score_and_nonnegative_simplex_boundary",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation plan for remediating missing v13 fresh "
            "member-source materialization inputs."
        )
    )
    parser.add_argument("--failure_remediation_plan_json", type=Path, required=True)
    parser.add_argument("--expected_failure_remediation_plan_sha256", required=True)
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
        failure_remediation_plan_json=args.failure_remediation_plan_json,
        expected_failure_remediation_plan_sha256=(
            args.expected_failure_remediation_plan_sha256
        ),
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
    args.output_json.write_text(
        json.dumps(_stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    failure_remediation_plan_json: Path,
    expected_failure_remediation_plan_sha256: str,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_path = failure_remediation_plan_json.resolve()
    audit_path = v13_audit_md.resolve()
    source_plan = _load_json_dict(plan_path)
    audit_text = _read_text(audit_path)
    implementation_plan = _implementation_plan(source_plan)
    checks = _checks(
        plan_path=plan_path,
        audit_path=audit_path,
        audit_text=audit_text,
        source_plan=source_plan,
        implementation_plan=implementation_plan,
        expected_failure_remediation_plan_sha256=(
            expected_failure_remediation_plan_sha256
        ),
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
            "implementation_execution": False,
            "input_materialization_execution": False,
            "fresh_member_selection_execution": False,
            "validation_preflight_execution": False,
            "data_preparation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "selector_promotion": False,
            "deployment": False,
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
            "failure_remediation_plan_json": str(plan_path),
            "v13_audit_md": str(audit_path),
        },
        "source_hashes": {
            "failure_remediation_plan_json_sha256": _sha256(plan_path),
            "v13_audit_md_sha256": _sha256(audit_path),
        },
        "source_plan_summary": _source_plan_summary(source_plan),
        "implementation_plan": implementation_plan,
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
    plan = report["implementation_plan"]
    lines = [
        "# V13 Fresh Member-Source Materialization Failure Remediation Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation execution authorized: `{decision['implementation_execution_authorized_next']}`",
        f"- Input materialization execution authorized: `{decision['input_materialization_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Future script: `{plan['future_input_materializer_script']}`",
        "",
        "## Required Implementation Contracts",
        "",
    ]
    for item in plan["required_implementation_contracts"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This plan-only gate authorizes only a static contract review. It "
            "does not implement code, materialize inputs, run DP, generate "
            "candidates, replay, train CAMP, modify DP, promote, deploy, or "
            "make safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _implementation_plan(source_plan: dict[str, Any]) -> dict[str, Any]:
    summary = _source_plan_summary(source_plan)
    return {
        "implementation_performed_by_this_gate": False,
        "input_materialization_performed_by_this_gate": False,
        "future_input_materializer_script": FUTURE_INPUT_MATERIALIZER_SCRIPT,
        "future_input_materializer_test": FUTURE_INPUT_MATERIALIZER_TEST,
        "future_outputs": list(FUTURE_OUTPUTS),
        "required_member_fields": list(REQUIRED_MEMBER_FIELDS),
        "required_zero_intersections_after_materialization": {
            key: 0 for key in ZERO_INTERSECTION_KEYS
        },
        "source_failure_to_remediate": summary,
        "required_implementation_contracts": list(REQUIRED_IMPLEMENTATION_CONTRACTS),
        "candidate_member_source_strategy": {
            "allowed_sources": [
                "existing fixed-DP current-source artifact manifests",
                "existing fixed-DP current-source candidate tensor metadata",
                "existing fixed-DP current-source selection logs with identity fields",
            ],
            "must_reject_if_no_existing_member_source_evidence": True,
            "must_not_synthesize_identity_hashes": True,
            "must_not_use_rejected_overlap_artifact_as_holdout": True,
        },
        "training_split_root_registry_strategy": {
            "must_write_nonempty_training_split_root_registry": True,
            "must_link_roots_to_training_source_manifests": True,
            "split_root_zero_alone_is_insufficient": True,
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
            "executed_trajectory_remains_dp_top1": True,
        },
        "next_gate": (
            "fresh_evaluation_split_member_source_materialization_failure_"
            "remediation_implementation_static_contract_review_only"
        ),
    }


def _checks(
    *,
    plan_path: Path,
    audit_path: Path,
    audit_text: str,
    source_plan: dict[str, Any],
    implementation_plan: dict[str, Any],
    expected_failure_remediation_plan_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(source_plan.get("final_decision"))
    source_summary = _source_plan_summary(source_plan)
    checks = [
        _check("source_plan_json_exists", plan_path.is_file(), str(plan_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _expect("source_plan_sha256", _sha256(plan_path), expected_failure_remediation_plan_sha256),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_failure_plan_ready", _latest_value(audit_text, "fresh_evaluation_split_member_source_materialization_failure_remediation_plan_ready"), "True"),
        _expect("audit_candidate_manifest_missing", _latest_value(audit_text, "candidate_member_source_manifest_missing"), "True"),
        _expect("audit_training_split_root_registry_missing", _latest_value(audit_text, "training_split_manifest_root_registry_missing"), "True"),
        _expect("source_schema_version", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_status_ready", decision.get("status"), SOURCE_PLAN_READY_STATUS),
        _expect("source_passed", decision.get("passed"), True),
        _expect("source_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_authorizes_this_plan", decision.get("authorized_next_work"), authorized_current_work),
        _expect("source_implementation_plan_authorized", decision.get("materialization_failure_remediation_implementation_plan_authorized_next"), True),
        _expect("source_candidate_manifest_structures_zero", source_summary["candidate_member_source_manifest_structures_found"], 0),
        _expect("source_candidate_member_count_zero", source_summary["candidate_member_count"], 0),
        _expect("source_training_split_roots_zero", source_summary["training_split_manifest_root_count"], 0),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    for flag in BLOCKED_SOURCE_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", decision.get(flag), False))
    checks.extend(_plan_checks(implementation_plan))
    return checks


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    contracts = set(plan["required_implementation_contracts"])
    member_fields = set(plan["required_member_fields"])
    math_boundary = plan["math_boundary"]
    candidate_strategy = plan["candidate_member_source_strategy"]
    split_strategy = plan["training_split_root_registry_strategy"]
    return [
        _expect("plan_does_not_implement", plan["implementation_performed_by_this_gate"], False),
        _expect("plan_does_not_materialize_inputs", plan["input_materialization_performed_by_this_gate"], False),
        _expect("plan_next_gate_static_review", plan["next_gate"], "fresh_evaluation_split_member_source_materialization_failure_remediation_implementation_static_contract_review_only"),
        _check("plan_lists_all_future_outputs", set(FUTURE_OUTPUTS) <= set(plan["future_outputs"]), plan["future_outputs"], "future outputs"),
        _check("plan_requires_all_member_fields", set(REQUIRED_MEMBER_FIELDS) <= member_fields, plan["required_member_fields"], "member fields"),
        _check("plan_requires_all_contracts", set(REQUIRED_IMPLEMENTATION_CONTRACTS) <= contracts, plan["required_implementation_contracts"], "contracts"),
        _check("plan_requires_zero_intersections_after_materialization", all(value == 0 for value in plan["required_zero_intersections_after_materialization"].values()), plan["required_zero_intersections_after_materialization"], "all zero"),
        _expect("plan_rejects_missing_member_source_evidence", candidate_strategy["must_reject_if_no_existing_member_source_evidence"], True),
        _expect("plan_does_not_synthesize_identity_hashes", candidate_strategy["must_not_synthesize_identity_hashes"], True),
        _expect("plan_rejects_rejected_artifact_as_holdout", candidate_strategy["must_not_use_rejected_overlap_artifact_as_holdout"], True),
        _expect("plan_writes_nonempty_training_split_roots", split_strategy["must_write_nonempty_training_split_root_registry"], True),
        _expect("plan_rejects_split_root_zero_only", split_strategy["split_root_zero_alone_is_insufficient"], True),
        _expect("plan_score_affine", math_boundary["score_expression"], SCORE_EXPRESSION),
        _expect("plan_nonnegative_simplex", math_boundary["nonnegative_simplex_weights_only"], True),
        _expect("plan_master_convex", math_boundary["master_problem_remains_convex"], True),
    ]


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
        "materialization_failure_remediation_implementation_plan_ready": passed,
        "materialization_failure_remediation_implementation_static_contract_review_authorized_next": passed,
        "implementation_execution_authorized_next": False,
        "input_materialization_execution_authorized_next": False,
        "materialization_execution_authorized_next": False,
        "member_source_builder_execution_authorized_next": False,
        "validation_preflight_authorized_next": False,
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
        "implementation_executed": False,
        "input_materialization_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    summary = _dict(source_plan.get("materialization_rejection_summary"))
    remediation_plan = _dict(source_plan.get("remediation_plan"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "candidate_member_source_manifest_structures_found": summary.get(
            "candidate_member_source_manifest_structures_found"
        ),
        "candidate_member_count": summary.get("candidate_member_count"),
        "training_split_manifest_root_count": summary.get(
            "training_split_manifest_root_count"
        ),
        "source_next_gate": remediation_plan.get("next_gate"),
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
