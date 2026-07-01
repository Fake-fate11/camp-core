#!/usr/bin/env python3
"""Plan remediation for a rejected fresh evaluation split member source.

This gate is plan-only. It consumes a rejected fresh evaluation split preflight
artifact and defines the contract for selecting a truly fresh member source
before any evaluation, replay, candidate generation, training, promotion, or
deployment is considered.
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
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_plan_rejected"
)
SOURCE_PREFLIGHT_SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_preflight_v1"
SOURCE_PREFLIGHT_REJECT_STATUS = "dp_camp_v13_fresh_evaluation_split_preflight_rejected"
SOURCE_FAILURE_CLASS = "candidate_tensor_hash_overlap_with_training_registry"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_preflight_rejected"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_static_"
    "contract_review_only"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan-only remediation for a rejected fresh split member source."
    )
    parser.add_argument("--fresh_evaluation_split_preflight_json", type=Path, required=True)
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
        fresh_evaluation_split_preflight_json=args.fresh_evaluation_split_preflight_json,
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
    fresh_evaluation_split_preflight_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    preflight_path = fresh_evaluation_split_preflight_json.resolve()
    audit_path = v13_audit_md.resolve()
    preflight = _load_json_dict(preflight_path)
    audit_text = _read_text(audit_path)
    source_payloads = _load_source_payloads(preflight)
    plan = _member_source_remediation_plan(preflight, source_payloads)
    checks = _checks(
        preflight_path=preflight_path,
        audit_path=audit_path,
        audit_text=audit_text,
        preflight=preflight,
        source_payloads=source_payloads,
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
            "read_only_inputs": True,
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
        "inputs": {
            "fresh_evaluation_split_preflight_json": str(preflight_path),
            "v13_audit_md": str(audit_path),
        },
        "source_hashes": _source_hashes(preflight_path, audit_path, preflight),
        "preflight_summary": _preflight_summary(preflight),
        "source_payload_summary": _source_payload_summary(source_payloads),
        "member_source_remediation_plan": plan,
        "plan_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "member_source_remediation_static_contract_review_authorized_next": passed,
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
        },
    }


def _member_source_remediation_plan(
    preflight: dict[str, Any],
    source_payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = _dict(preflight.get("preflight_result"))
    summary = _dict(preflight.get("manifest_summary"))
    return {
        "objective": (
            "replace the rejected fixed split member source with a truly fresh "
            "member source before any later evaluation, replay, candidate "
            "generation, or CAMP training gate"
        ),
        "failure_attribution": {
            "canonical_failure_class": _dict(preflight.get("final_decision")).get(
                "failure_class"
            ),
            "candidate_tensor_hash_intersection_count": result.get(
                "candidate_tensor_hash_intersection_count"
            ),
            "path_signature_intersection_count": result.get(
                "path_signature_intersection_count"
            ),
            "record_identity_intersection_count": result.get(
                "record_identity_intersection_count"
            ),
            "split_manifest_root_intersection_count": result.get(
                "split_manifest_root_intersection_count"
            ),
            "root_zero_is_not_sufficient": True,
            "failed_checks_empty_is_not_pass": True,
        },
        "rejected_source_constraints": {
            "rejected_overlap_artifact_is_not_evaluation_holdout": True,
            "source_builder_did_not_select_fresh_members": summary.get(
                "fresh_split_members_selected_by_builder"
            )
            is False,
            "candidate_path_record_overlap_requires_member_source_replacement": True,
            "do_not_relabel_overlapping_members_as_fresh": True,
        },
        "required_fresh_member_source_contract": {
            "candidate_tensor_hash_intersection_count": 0,
            "path_signature_intersection_count": 0,
            "record_identity_intersection_count": 0,
            "split_manifest_root_intersection_count": 0,
            "candidate_tensor_hash_registry_required": True,
            "path_signature_registry_required": True,
            "record_identity_hash_registry_required": True,
            "split_manifest_root_registry_required": True,
            "training_registry_must_be_loaded": True,
            "recovered_prior_registry_must_be_loaded": True,
            "rejected_source_registry_must_be_loaded": True,
            "zero_intersection_preflight_required_before_evaluation": True,
        },
        "next_gate_requirements": {
            "next_gate": "fresh_evaluation_split_member_source_remediation_static_contract_review_only",
            "review_must_reject_missing_registry_inputs": True,
            "review_must_reject_split_root_only_acceptance": True,
            "review_must_reject_reusing_rejected_overlap_source": True,
            "review_must_reject_any_action_authorization_leak": True,
            "review_must_preserve_fixed_dp_head": FIXED_DP_HEAD,
            "review_must_preserve_score_affine": SCORE_EXPRESSION,
        },
        "boundary": {
            "plan_only": True,
            "fresh_member_selection_execution_authorized": False,
            "evaluation_execution_authorized": False,
            "data_preparation_authorized": False,
            "fixed_dp_candidate_generation_authorized": False,
            "replay_authorized": False,
            "training_authorized": False,
            "dp_modification_authorized": False,
            "candidate_generation_by_camp_authorized": False,
            "camp_trajectory_generation_or_modification_authorized": False,
            "reference_blend_guidance_postselection_authorized": False,
            "closed_loop_outcome_input_authorized": False,
            "promotion_or_deployment_authorized": False,
            "safety_or_camp_over_dp_claim_authorized": False,
        },
        "source_payload_summary": _source_payload_summary(source_payloads),
    }


def _checks(
    *,
    preflight_path: Path,
    audit_path: Path,
    audit_text: str,
    preflight: dict[str, Any],
    source_payloads: dict[str, dict[str, Any]],
    plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(preflight.get("final_decision"))
    result = _dict(preflight.get("preflight_result"))
    summary = _dict(preflight.get("manifest_summary"))
    return [
        _check("preflight_json_exists", preflight_path.is_file(), str(preflight_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("preflight_schema_version", preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA_VERSION),
        _expect("preflight_status_rejected", decision.get("status"), SOURCE_PREFLIGHT_REJECT_STATUS),
        _expect("preflight_passed_false", decision.get("passed"), False),
        _expect("preflight_authorizes_this_plan", decision.get("authorized_next_work"), authorized_current_work),
        _expect("preflight_failure_class_expected", decision.get("failure_class"), SOURCE_FAILURE_CLASS),
        _expect("preflight_failed_checks_empty", decision.get("failed_checks"), []),
        _check("candidate_overlap_nonzero", _int(result.get("candidate_tensor_hash_intersection_count")) > 0, result.get("candidate_tensor_hash_intersection_count"), ">0"),
        _check("path_overlap_nonzero", _int(result.get("path_signature_intersection_count")) > 0, result.get("path_signature_intersection_count"), ">0"),
        _check("record_identity_overlap_nonzero", _int(result.get("record_identity_intersection_count")) > 0, result.get("record_identity_intersection_count"), ">0"),
        _expect("split_root_intersection_zero_but_insufficient", result.get("split_manifest_root_intersection_count"), 0),
        _expect("all_required_intersections_not_zero", result.get("all_required_intersections_zero"), False),
        _expect("source_builder_did_not_select_fresh_members", summary.get("fresh_split_members_selected_by_builder"), False),
        _expect("builder_completed", summary.get("builder_status"), "dp_camp_v13_fresh_evaluation_split_manifest_builder_complete"),
        _check("source_manifest_builder_payload_loaded", bool(source_payloads.get("manifest_builder")), list(source_payloads), "manifest_builder loaded"),
        _check("source_scope_payload_loaded", bool(source_payloads.get("scope_manifest")), list(source_payloads), "scope_manifest loaded"),
        _check("source_registry_report_payload_loaded", bool(source_payloads.get("nonoverlap_registry_report")), list(source_payloads), "nonoverlap_registry_report loaded"),
        _check("source_registry_manifest_payload_loaded", bool(source_payloads.get("source_registry_manifest")), list(source_payloads), "source_registry_manifest loaded"),
        _expect("plan_requires_zero_candidate_overlap", plan["required_fresh_member_source_contract"]["candidate_tensor_hash_intersection_count"], 0),
        _expect("plan_requires_zero_path_overlap", plan["required_fresh_member_source_contract"]["path_signature_intersection_count"], 0),
        _expect("plan_requires_zero_record_overlap", plan["required_fresh_member_source_contract"]["record_identity_intersection_count"], 0),
        _expect("plan_requires_zero_root_overlap", plan["required_fresh_member_source_contract"]["split_manifest_root_intersection_count"], 0),
        _expect("plan_rejects_root_only_acceptance", plan["next_gate_requirements"]["review_must_reject_split_root_only_acceptance"], True),
        _expect("plan_rejects_rejected_source_reuse", plan["next_gate_requirements"]["review_must_reject_reusing_rejected_overlap_source"], True),
        _expect("plan_blocks_evaluation", plan["boundary"]["evaluation_execution_authorized"], False),
        _expect("plan_blocks_replay", plan["boundary"]["replay_authorized"], False),
        _expect("plan_blocks_fixed_dp_candidate_generation", plan["boundary"]["fixed_dp_candidate_generation_authorized"], False),
        _expect("plan_blocks_training", plan["boundary"]["training_authorized"], False),
        _expect("plan_blocks_dp_modification", plan["boundary"]["dp_modification_authorized"], False),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["member_source_remediation_plan"]
    failure = plan["failure_attribution"]
    lines = [
        "# V13 Fresh Evaluation Split Member-Source Remediation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Failure Attribution",
        "",
        f"- Failure class: `{failure['canonical_failure_class']}`",
        f"- Candidate hash overlap: `{failure['candidate_tensor_hash_intersection_count']}`",
        f"- Path signature overlap: `{failure['path_signature_intersection_count']}`",
        f"- Record identity overlap: `{failure['record_identity_intersection_count']}`",
        f"- Split-root overlap: `{failure['split_manifest_root_intersection_count']}`",
        "",
        "The rejected-overlap artifact is not an evaluation holdout. A zero split-root "
        "intersection alone is insufficient because candidate, path, and record "
        "registry overlaps are nonzero.",
        "",
        "## Required Fresh Member Source",
        "",
    ]
    for key, value in plan["required_fresh_member_source_contract"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This gate is plan-only. It authorizes only a static contract review "
            "of the member-source remediation plan and does not authorize evaluation, "
            "replay, fixed-DP candidate generation, CAMP training, DP modification, "
            "promotion, deployment, or safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_source_payloads(preflight: dict[str, Any]) -> dict[str, dict[str, Any]]:
    inputs = _dict(preflight.get("inputs"))
    payloads = {
        "manifest_builder": _load_json_dict(Path(str(inputs.get("manifest_builder_json", "")))),
        "scope_manifest": _load_json_dict(Path(str(inputs.get("scope_manifest_json", "")))),
        "nonoverlap_registry_report": _load_json_dict(
            Path(str(inputs.get("nonoverlap_registry_report_json", "")))
        ),
        "source_registry_manifest": _load_json_dict(
            Path(str(preflight.get("source_registry_manifest", "")))
        ),
    }
    return {key: value for key, value in payloads.items() if value}


def _preflight_summary(preflight: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(preflight.get("final_decision"))
    result = _dict(preflight.get("preflight_result"))
    summary = _dict(preflight.get("manifest_summary"))
    return {
        "schema_version": preflight.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "failure_class": decision.get("failure_class"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "builder_status": summary.get("builder_status"),
        "fresh_split_members_selected_by_builder": summary.get(
            "fresh_split_members_selected_by_builder"
        ),
        "candidate_tensor_hash_intersection_count": result.get(
            "candidate_tensor_hash_intersection_count"
        ),
        "path_signature_intersection_count": result.get(
            "path_signature_intersection_count"
        ),
        "record_identity_intersection_count": result.get(
            "record_identity_intersection_count"
        ),
        "split_manifest_root_intersection_count": result.get(
            "split_manifest_root_intersection_count"
        ),
    }


def _source_payload_summary(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    builder_decision = _dict(_dict(payloads.get("manifest_builder")).get("final_decision"))
    scope = _dict(payloads.get("scope_manifest"))
    registry = _dict(payloads.get("nonoverlap_registry_report"))
    source_registry = _dict(payloads.get("source_registry_manifest"))
    return {
        "manifest_builder_status": builder_decision.get("status"),
        "manifest_builder_passed": builder_decision.get("passed"),
        "scope_schema_version": scope.get("schema_version"),
        "scope_target_selection_log_count": scope.get("target_selection_log_count"),
        "scope_target_record_count": scope.get("target_record_count"),
        "scope_fresh_split_members_selected_by_builder": scope.get(
            "fresh_split_members_selected_by_this_builder"
        ),
        "registry_report_schema_version": registry.get("schema_version"),
        "registry_report_future_zero_intersection_required": registry.get(
            "future_zero_intersection_preflight_required"
        ),
        "source_registry_schema_version": source_registry.get("schema_version"),
        "source_registry_evaluation_candidate_hash_count": source_registry.get(
            "evaluation_candidate_hash_count"
        ),
    }


def _source_hashes(
    preflight_path: Path,
    audit_path: Path,
    preflight: dict[str, Any],
) -> dict[str, str | None]:
    paths = {
        "fresh_evaluation_split_preflight_json": preflight_path,
        "v13_audit_md": audit_path,
    }
    inputs = _dict(preflight.get("inputs"))
    for key in (
        "manifest_builder_json",
        "scope_manifest_json",
        "nonoverlap_registry_report_json",
        "sha256sums_txt",
    ):
        paths[key] = Path(str(inputs.get(key, "")))
    paths["source_registry_manifest"] = Path(str(preflight.get("source_registry_manifest", "")))
    return {
        f"{name}_sha256": _sha256(path) if path.is_file() else None
        for name, path in paths.items()
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
    marker = f"{key}="
    if marker not in text:
        return None
    return text.rsplit(marker, maxsplit=1)[1].splitlines()[0].strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


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
