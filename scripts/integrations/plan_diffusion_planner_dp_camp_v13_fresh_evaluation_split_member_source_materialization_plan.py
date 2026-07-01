#!/usr/bin/env python3
"""Plan materialization for v13 fresh member-source inputs.

This gate is plan-only. It consumes the rejected validation preflight that
proved materialized fresh member-source inputs are missing, then defines the
future materialization contract. It does not run the member-source builder,
select members, run DP, generate candidates, replay, train CAMP, modify DP,
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
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_plan_rejected"
)
SOURCE_VALIDATION_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_validation_preflight_v1"
)
SOURCE_VALIDATION_REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_validation_preflight_rejected"
)
SOURCE_FAILURE_CLASS = "fresh_member_source_artifact_missing"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_validation_preflight_rejected_missing_materialized_source"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_static_contract_review_only"
)
FUTURE_MATERIALIZER_SCRIPT = (
    "scripts/integrations/materialize_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_inputs.py"
)
FUTURE_MATERIALIZER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_materializer.py"
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
REQUIRED_SOURCE_INPUTS = (
    "candidate_member_source_manifest_json",
    "training_candidate_tensor_hash_registry_json",
    "training_path_signature_registry_json",
    "training_record_identity_registry_json",
    "training_split_manifest_root_registry_json",
    "recovered_prior_registry_manifest_json",
    "rejected_overlap_source_registry_manifest_json",
)
FUTURE_OUTPUTS = (
    "fresh_evaluation_split_member_source_manifest.json",
    "fresh_evaluation_split_member_source_nonoverlap_report.json",
    "fresh_evaluation_split_member_source_preflight_inputs.json",
    "SHA256SUMS.txt",
)
SOURCE_FALSE_FLAGS = (
    "fresh_evaluation_split_preflight_authorized_next",
    "fresh_member_selection_execution_authorized_next",
    "fresh_evaluation_split_evaluation_authorized_next",
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
)
SOURCE_EXECUTION_FALSE_FLAGS = (
    "member_source_builder_executed",
    "real_fresh_member_selection_executed",
    "fixed_dp_candidate_generation_executed",
    "replay_executed",
    "training_executed",
    "dp_modification_executed",
)
AUDIT_FALSE_FLAGS = (
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
REQUIRED_BUILDER_TERMS = (
    "--candidate_member_source_manifest_json",
    "--training_candidate_tensor_hash_registry_json",
    "--training_path_signature_registry_json",
    "--training_record_identity_registry_json",
    "--training_split_manifest_root_registry_json",
    "--recovered_prior_registry_manifest_json",
    "--rejected_overlap_source_registry_manifest_json",
    "fail_closed_when_any_required_registry_is_missing_empty_or_unreadable",
    "exclude_every_member_from_the_rejected_overlap_source",
    "prove_zero_candidate_tensor_hash_intersection",
    "reject_split_root_only_acceptance",
    "exclude_formal_seeds_11_12_13_and_full36",
    SCORE_EXPRESSION,
)
REQUIRED_PREFLIGHT_TERMS = (
    "MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION",
    "NONOVERLAP_REPORT_SCHEMA_VERSION",
    "PREFLIGHT_INPUTS_SCHEMA_VERSION",
    "sha256sums_matches",
    "fresh_member_source_artifact_missing",
    AUTHORIZED_CURRENT_WORK,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for materializing missing v13 fresh member-source "
            "inputs after validation preflight rejected them as absent."
        )
    )
    parser.add_argument("--validation_preflight_json", type=Path, required=True)
    parser.add_argument("--member_source_builder_script_py", type=Path, required=True)
    parser.add_argument("--validation_preflight_script_py", type=Path, required=True)
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
        validation_preflight_json=args.validation_preflight_json,
        member_source_builder_script_py=args.member_source_builder_script_py,
        validation_preflight_script_py=args.validation_preflight_script_py,
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
    validation_preflight_json: Path,
    member_source_builder_script_py: Path,
    validation_preflight_script_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "validation_preflight_json": validation_preflight_json.resolve(),
        "member_source_builder_script_py": member_source_builder_script_py.resolve(),
        "validation_preflight_script_py": validation_preflight_script_py.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    source = _load_json_dict(paths["validation_preflight_json"])
    builder_text = _read_text(paths["member_source_builder_script_py"])
    preflight_text = _read_text(paths["validation_preflight_script_py"])
    audit_text = _read_text(paths["v13_audit_md"])
    plan = _materialization_plan(source)
    checks = _checks(
        paths=paths,
        source=source,
        builder_text=builder_text,
        preflight_text=preflight_text,
        audit_text=audit_text,
        plan=plan,
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
            "materialization_execution": False,
            "member_source_builder_execution": False,
            "fresh_member_selection_execution": False,
            "evaluation_execution": False,
            "data_preparation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
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
        "inputs": {name: str(path) for name, path in paths.items()},
        "source_hashes": {name: _sha256(path) for name, path in paths.items()},
        "source_validation_summary": _source_validation_summary(source),
        "materialization_plan": plan,
        "future_static_contract_review_requirements": (
            _future_static_contract_review_requirements()
        ),
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
    plan = report["materialization_plan"]
    lines = [
        "# V13 Fresh Member-Source Materialization Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Materialization execution authorized: `{decision['materialization_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Training authorized: `{decision['training_execution_authorized_next']}`",
        "",
        "## Missing Inputs",
        "",
    ]
    for item in plan["missing_inputs_to_materialize"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Future Materializer Contract", ""])
    for item in plan["future_materializer_contract"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This plan-only gate does not materialize inputs, run DP, generate "
            "candidates, run replay, train CAMP, modify DP, promote, deploy, "
            "or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _materialization_plan(source: dict[str, Any]) -> dict[str, Any]:
    source_summary = _source_validation_summary(source)
    return {
        "plan_ready_no_inputs_materialized": True,
        "materialization_performed_by_this_gate": False,
        "source_rejected_validation_preflight": True,
        "source_failure_class": source_summary["failure_class"],
        "future_materializer_script": FUTURE_MATERIALIZER_SCRIPT,
        "future_materializer_test": FUTURE_MATERIALIZER_TEST,
        "missing_inputs_to_materialize": list(REQUIRED_SOURCE_INPUTS),
        "future_outputs": list(FUTURE_OUTPUTS),
        "required_zero_intersections": {
            key: 0 for key in ZERO_INTERSECTION_KEYS
        },
        "candidate_member_manifest_contract": {
            "candidate_members_nonempty": True,
            "each_member_has_candidate_tensor_hashes": True,
            "each_member_has_path_signatures": True,
            "each_member_has_record_identity_hashes": True,
            "each_member_has_split_manifest_roots": True,
            "each_member_has_source_path_route_and_seed": True,
            "formal_seeds_11_12_13_excluded": True,
            "full36_excluded": True,
            "source_members_are_not_rejected_overlap_source": True,
            "source_members_are_not_relabelled_from_rejected_overlap_artifact": True,
        },
        "registry_materialization_contract": {
            "training_registries_loaded_before_selection": True,
            "recovered_prior_registry_loaded_before_selection": True,
            "rejected_overlap_source_registry_loaded_before_selection": True,
            "missing_empty_or_unreadable_registry_fails_closed": True,
            "split_root_zero_alone_is_insufficient": True,
        },
        "future_materializer_contract": [
            "read only already materialized candidate-member and registry inputs",
            "do not run DP or generate candidates in the materializer gate",
            "do not run the member-source builder in the materialization plan gate",
            "fail closed if any required source input is missing, empty, or unreadable",
            "write no fresh member-source outputs until a future implementation gate",
            "require zero candidate/path/record/split-root intersections before preflight can pass",
            "write SHA256SUMS for future materialized outputs",
        ],
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
            "executed_trajectory_remains_dp_top1": True,
        },
        "next_gate": (
            "fresh_evaluation_split_member_source_remediation_"
            "materialization_static_contract_review_only"
        ),
    }


def _checks(
    *,
    paths: dict[str, Path],
    source: dict[str, Any],
    builder_text: str,
    preflight_text: str,
    audit_text: str,
    plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(source.get("final_decision"))
    failed_checks = _list(decision.get("failed_checks"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_materialization_plan_authorized", _latest_value(audit_text, "member_source_materialization_plan_authorized_next"), "True"),
        _expect("source_schema_version", source.get("schema_version"), SOURCE_VALIDATION_SCHEMA_VERSION),
        _expect("source_status_rejected", decision.get("status"), SOURCE_VALIDATION_REJECT_STATUS),
        _expect("source_passed_false", decision.get("passed"), False),
        _expect("source_failure_class_missing", decision.get("failure_class"), SOURCE_FAILURE_CLASS),
        _expect("source_authorizes_this_plan", decision.get("authorized_next_work"), authorized_current_work),
        _expect("source_materialization_plan_authorized", decision.get("member_source_materialization_plan_authorized_next"), True),
        _expect("source_fresh_preflight_not_authorized", decision.get("fresh_evaluation_split_preflight_authorized_next"), False),
    ]
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", decision.get(flag), False))
    for flag in SOURCE_EXECUTION_FALSE_FLAGS:
        checks.append(_expect(f"source_did_not_execute_{flag}", decision.get(flag), False))
    for failed_name in (
        "member_source_manifest_json_exists",
        "nonoverlap_report_json_exists",
        "preflight_inputs_json_exists",
        "sha256sums_txt_exists",
    ):
        checks.append(_check(f"source_failed_check_contains_{failed_name}", failed_name in failed_checks, failed_checks, failed_name))
    checks.extend(
        _contains(f"builder_contains_{_slug(term)}", builder_text, term)
        for term in REQUIRED_BUILDER_TERMS
    )
    checks.extend(
        _contains(f"preflight_contains_{_slug(term)}", preflight_text, term)
        for term in REQUIRED_PREFLIGHT_TERMS
    )
    checks.extend(_plan_checks(plan))
    return checks


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("plan_does_not_materialize_inputs", plan["materialization_performed_by_this_gate"], False),
        _expect("plan_next_gate_static_review_only", plan["next_gate"], "fresh_evaluation_split_member_source_remediation_materialization_static_contract_review_only"),
        _check("plan_lists_all_required_source_inputs", set(REQUIRED_SOURCE_INPUTS) <= set(plan["missing_inputs_to_materialize"]), plan["missing_inputs_to_materialize"], "all required source inputs"),
        _check("plan_lists_all_future_outputs", set(FUTURE_OUTPUTS) <= set(plan["future_outputs"]), plan["future_outputs"], "all future outputs"),
        _check("plan_requires_all_zero_intersections", all(plan["required_zero_intersections"].get(key) == 0 for key in ZERO_INTERSECTION_KEYS), plan["required_zero_intersections"], "all zero"),
        _expect("plan_requires_member_identity_fields", plan["candidate_member_manifest_contract"]["each_member_has_record_identity_hashes"], True),
        _expect("plan_excludes_formal_seeds", plan["candidate_member_manifest_contract"]["formal_seeds_11_12_13_excluded"], True),
        _expect("plan_rejects_root_only_acceptance", plan["registry_materialization_contract"]["split_root_zero_alone_is_insufficient"], True),
        _expect("plan_score_affine", plan["math_boundary"]["score_expression"], SCORE_EXPRESSION),
        _expect("plan_nonnegative_simplex", plan["math_boundary"]["nonnegative_simplex_weights_only"], True),
        _expect("plan_master_convex", plan["math_boundary"]["master_problem_remains_convex"], True),
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
        "materialization_plan_ready": passed,
        "materialization_static_contract_review_authorized_next": passed,
        "materialization_execution_authorized_next": False,
        "member_source_builder_execution_authorized_next": False,
        "fresh_member_selection_execution_authorized_next": False,
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
        "materialization_executed": False,
        "member_source_builder_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _future_static_contract_review_requirements() -> list[str]:
    return [
        "reject_if_plan_materializes_inputs_or_runs_builder",
        "reject_if_future_materializer_can_run_dp_or_generate_candidates",
        "reject_if_candidate_member_manifest_identity_fields_are_optional",
        "reject_if_training_recovered_or_rejected_registries_are_optional",
        "reject_if_split_root_zero_alone_can_pass",
        "reject_if_formal_seeds_11_12_13_or_full36_can_enter_member_source",
        "reject_if_rejected_overlap_source_can_be_reused_or_relabelled",
        "reject_if_future_outputs_lack_sha256_manifest",
        "reject_if_score_is_not_affine_or_weights_are_not_nonnegative_simplex",
        "reject_if_replay_training_dp_modification_promotion_deployment_or_safety_claims_are_authorized",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "materializing candidate_member_source_manifest_json in this plan gate",
        "running the existing member-source builder in this plan gate",
        "running Diffusion Planner or fixed-DP candidate generation in this plan gate",
        "using CAMP to generate, repair, rewrite, or blend trajectories",
        "using rejected-overlap artifacts as evaluation holdout or training data",
        "modifying DP code, config, weights, or checkpoint",
        "running replay, preparing training data, or training CAMP",
        "promoting selectors or atoms, deploying, or claiming safety/CAMP-over-DP benefit",
    ]


def _source_validation_summary(source: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source.get("final_decision"))
    member_summary = _dict(source.get("member_source_summary"))
    return {
        "schema_version": source.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failure_class": decision.get("failure_class"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failed_check_count": len(_list(decision.get("failed_checks"))),
        "selected_member_count": member_summary.get("selected_member_count"),
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


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


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


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


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
