#!/usr/bin/env python3
"""Fail-closed builder for v13 default-off member-source generation outputs.

The builder consumes already materialized fixed-DP candidate member records and
training registries, then emits a default-off member-source generation manifest
and derived registries. It does not run Diffusion Planner, generate candidates,
modify trajectories, run replay, prepare training data, train CAMP, modify DP,
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
DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_runtime_v1"
)
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_default_off_member_source_generation_implementation_"
    "static_contract_review_v1"
)
SOURCE_REVIEW_PASS_STATUS = (
    "dp_camp_v13_default_off_member_source_generation_implementation_"
    "static_contract_review_passed"
)
SCHEMA_VERSION = "dp_camp_v13_default_off_member_source_generation_builder_v1"
READY_STATUS = "dp_camp_v13_default_off_member_source_generation_builder_complete"
REJECT_STATUS = "dp_camp_v13_default_off_member_source_generation_builder_rejected"
DISABLED_STATUS = "dp_camp_v13_default_off_member_source_generation_builder_default_off_disabled"
MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_member_source_generation_manifest_v1"
REGISTRY_SCHEMA_VERSION = "dp_camp_v13_default_off_member_source_generation_registry_v1"
PREFLIGHT_INPUTS_SCHEMA_VERSION = (
    "dp_camp_v13_default_off_member_source_generation_zero_overlap_preflight_inputs_v1"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_default_off_"
    "member_source_generation_implementation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_implementation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_post_implementation_static_contract_review_only"
)
FORMAL_SEEDS = {11, 12, 13}
OUTPUT_FILES = (
    "default_off_member_source_generation_manifest.json",
    "candidate_tensor_hash_registry.json",
    "path_signature_registry.json",
    "record_identity_registry.json",
    "split_manifest_root_registry.json",
    "zero_overlap_preflight_inputs.json",
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
SOURCE_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "replay_execution_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fresh_member_source_materialization_execution_authorized_next",
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation_static_contract_review_json", type=Path, required=True)
    parser.add_argument("--candidate_member_source_manifest_json", type=Path, required=True)
    parser.add_argument("--training_candidate_tensor_hash_registry_json", type=Path, required=True)
    parser.add_argument("--training_path_signature_registry_json", type=Path, required=True)
    parser.add_argument("--training_record_identity_registry_json", type=Path, required=True)
    parser.add_argument("--training_split_manifest_root_registry_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument(
        "--enable_default_off_member_source_generation_builder",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_generation_report(
        implementation_static_contract_review_json=(
            args.implementation_static_contract_review_json
        ),
        candidate_member_source_manifest_json=args.candidate_member_source_manifest_json,
        training_candidate_tensor_hash_registry_json=(
            args.training_candidate_tensor_hash_registry_json
        ),
        training_path_signature_registry_json=args.training_path_signature_registry_json,
        training_record_identity_registry_json=args.training_record_identity_registry_json,
        training_split_manifest_root_registry_json=(
            args.training_split_manifest_root_registry_json
        ),
        v13_audit_md=args.v13_audit_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        enabled=args.enable_default_off_member_source_generation_builder,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_generation_report(
    *,
    implementation_static_contract_review_json: Path,
    candidate_member_source_manifest_json: Path,
    training_candidate_tensor_hash_registry_json: Path,
    training_path_signature_registry_json: Path,
    training_record_identity_registry_json: Path,
    training_split_manifest_root_registry_json: Path,
    v13_audit_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    enabled: bool = False,
) -> dict[str, Any]:
    source_review = _load_json_dict(implementation_static_contract_review_json)
    source_summary = _source_summary(source_review)
    audit_text = _read_text(v13_audit_md)
    output_dir = output_dir.resolve()
    candidate_payload = _load_json_dict(candidate_member_source_manifest_json)
    training_registries = {
        "candidate_tensor_hashes": _load_registry_values(training_candidate_tensor_hash_registry_json),
        "path_signatures": _load_registry_values(training_path_signature_registry_json),
        "record_identity_hashes": _load_registry_values(training_record_identity_registry_json),
        "split_manifest_roots": _load_registry_values(training_split_manifest_root_registry_json),
    }
    selected, rejected = _select_members(candidate_payload, training_registries)
    selected_sets = _member_sets(selected)
    zero_counts = _zero_counts(selected_sets, training_registries)
    checks = _checks(
        implementation_static_contract_review_json=implementation_static_contract_review_json,
        candidate_member_source_manifest_json=candidate_member_source_manifest_json,
        training_candidate_tensor_hash_registry_json=training_candidate_tensor_hash_registry_json,
        training_path_signature_registry_json=training_path_signature_registry_json,
        training_record_identity_registry_json=training_record_identity_registry_json,
        training_split_manifest_root_registry_json=training_split_manifest_root_registry_json,
        v13_audit_md=v13_audit_md,
        source_review=source_review,
        source_summary=source_summary,
        audit_text=audit_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        enabled=enabled,
        selected=selected,
        zero_counts=zero_counts,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    output_paths = _output_paths(output_dir)
    if passed:
        _write_outputs(
            output_paths=output_paths,
            selected=selected,
            rejected=rejected,
            zero_counts=zero_counts,
            selected_sets=selected_sets,
            training_registries=training_registries,
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "implementation_only": True,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "replay_execution": False,
            "data_preparation": False,
            "training_preflight": False,
            "training_execution": False,
            "dp_modification": False,
            "promotion": False,
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
            "implementation_static_contract_review_json": str(
                implementation_static_contract_review_json.resolve()
            ),
            "candidate_member_source_manifest_json": str(
                candidate_member_source_manifest_json.resolve()
            ),
            "training_candidate_tensor_hash_registry_json": str(
                training_candidate_tensor_hash_registry_json.resolve()
            ),
            "training_path_signature_registry_json": str(
                training_path_signature_registry_json.resolve()
            ),
            "training_record_identity_registry_json": str(
                training_record_identity_registry_json.resolve()
            ),
            "training_split_manifest_root_registry_json": str(
                training_split_manifest_root_registry_json.resolve()
            ),
            "v13_audit_md": str(v13_audit_md.resolve()),
        },
        "source_hashes": {
            "implementation_static_contract_review_json_sha256": _sha256(
                implementation_static_contract_review_json
            ),
            "candidate_member_source_manifest_json_sha256": _sha256(
                candidate_member_source_manifest_json
            ),
            "training_candidate_tensor_hash_registry_json_sha256": _sha256(
                training_candidate_tensor_hash_registry_json
            ),
            "training_path_signature_registry_json_sha256": _sha256(
                training_path_signature_registry_json
            ),
            "training_record_identity_registry_json_sha256": _sha256(
                training_record_identity_registry_json
            ),
            "training_split_manifest_root_registry_json_sha256": _sha256(
                training_split_manifest_root_registry_json
            ),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "selection_summary": {
            "candidate_member_count": len(_list(candidate_payload.get("members"))),
            "selected_member_count": len(selected),
            "rejected_member_count": len(rejected),
            "rejected_reasons": _reason_counts(rejected),
            "zero_intersection_counts": zero_counts,
            "manifest_written": passed,
        },
        "output_paths": {key: str(path) for key, path in output_paths.items()},
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            enabled=enabled,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["selection_summary"]
    return "\n".join(
        [
            "# V13 Default-Off Member-Source Generation Builder",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Selected members: `{summary['selected_member_count']}`",
            f"- Rejected members: `{summary['rejected_member_count']}`",
            f"- Candidate generation executed: `{decision['fixed_dp_candidate_generation_executed']}`",
            f"- Training executed: `{decision['training_executed']}`",
            "",
        ]
    )


def _checks(
    *,
    implementation_static_contract_review_json: Path,
    candidate_member_source_manifest_json: Path,
    training_candidate_tensor_hash_registry_json: Path,
    training_path_signature_registry_json: Path,
    training_record_identity_registry_json: Path,
    training_split_manifest_root_registry_json: Path,
    v13_audit_md: Path,
    source_review: dict[str, Any],
    source_summary: dict[str, Any],
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    enabled: bool,
    selected: list[dict[str, Any]],
    zero_counts: dict[str, int],
) -> list[dict[str, Any]]:
    checks = [
        _check("builder_enabled", enabled, enabled, True),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("implementation_static_contract_review_json_exists", implementation_static_contract_review_json.is_file(), str(implementation_static_contract_review_json), "file exists"),
        _check("candidate_member_source_manifest_json_exists", candidate_member_source_manifest_json.is_file(), str(candidate_member_source_manifest_json), "file exists"),
        _check("training_candidate_tensor_hash_registry_json_exists", training_candidate_tensor_hash_registry_json.is_file(), str(training_candidate_tensor_hash_registry_json), "file exists"),
        _check("training_path_signature_registry_json_exists", training_path_signature_registry_json.is_file(), str(training_path_signature_registry_json), "file exists"),
        _check("training_record_identity_registry_json_exists", training_record_identity_registry_json.is_file(), str(training_record_identity_registry_json), "file exists"),
        _check("training_split_manifest_root_registry_json_exists", training_split_manifest_root_registry_json.is_file(), str(training_split_manifest_root_registry_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("source_review_status", source_summary["status"], SOURCE_REVIEW_PASS_STATUS),
        _expect("source_review_passed", source_summary["passed"], True),
        _expect("source_authorizes_this_gate", source_summary["authorized_next_work"], authorized_current_work),
        _expect("source_implementation_authorized", source_summary["implementation_authorized_next"], True),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_implementation", _latest_value(audit_text, "default_off_member_source_generation_implementation_authorized_next"), "True"),
        _check("selected_members_nonempty", len(selected) > 0, len(selected), ">0"),
    ]
    for key, observed in zero_counts.items():
        checks.append(_expect(f"{key}_zero", observed, 0))
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", source_summary.get(flag), False))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    return checks


def _select_members(
    candidate_payload: dict[str, Any],
    training_registries: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw_member in _list(candidate_payload.get("members")):
        member = _dict(raw_member)
        normalized = _normalize_member(member)
        reasons = _member_rejection_reasons(normalized, training_registries)
        if reasons:
            rejected.append({"member_id": normalized["member_id"], "reasons": sorted(reasons)})
        else:
            selected.append(normalized)
    return selected, rejected


def _normalize_member(member: dict[str, Any]) -> dict[str, Any]:
    source_path = member.get("selection_log_json") or member.get("source_path")
    return {
        "member_id": str(member.get("member_id") or ""),
        "route": str(member.get("route") or ""),
        "seed": _as_int(member.get("seed")),
        "source_path": str(source_path or ""),
        "candidate_tensor_hashes": sorted(_values(member, ("candidate_tensor_hashes", "candidate_tensor_hash"))),
        "path_signatures": sorted(_values(member, ("path_signatures", "path_signature"))),
        "record_identity_hashes": sorted(_values(member, ("record_identity_hashes", "record_identity_hash", "record_identity"))),
        "split_manifest_roots": sorted(_values(member, ("split_manifest_roots", "split_manifest_root"))),
    }


def _member_rejection_reasons(
    member: dict[str, Any],
    training_registries: dict[str, set[str]],
) -> set[str]:
    reasons: set[str] = set()
    if not member["member_id"]:
        reasons.add("member_id_missing")
    if not member["source_path"]:
        reasons.add("selection_log_missing")
    if "full36" in member["route"].lower():
        reasons.add("full36_forbidden")
    if member["seed"] in FORMAL_SEEDS:
        reasons.add("formal_seed_forbidden")
    for field in (
        "candidate_tensor_hashes",
        "path_signatures",
        "record_identity_hashes",
        "split_manifest_roots",
    ):
        if not member[field]:
            reasons.add(f"{field}_empty")
    if set(member["candidate_tensor_hashes"]) & training_registries["candidate_tensor_hashes"]:
        reasons.add("candidate_tensor_hash_overlap")
    if set(member["path_signatures"]) & training_registries["path_signatures"]:
        reasons.add("path_signature_overlap")
    if set(member["record_identity_hashes"]) & training_registries["record_identity_hashes"]:
        reasons.add("record_identity_overlap")
    if set(member["split_manifest_roots"]) & training_registries["split_manifest_roots"]:
        reasons.add("split_manifest_root_overlap")
    reasons.update(_selection_log_errors(Path(member["source_path"])))
    return reasons


def _selection_log_errors(path: Path) -> set[str]:
    payload = _load_json_dict(path)
    records = _list(payload.get("records"))
    if not records and payload:
        records = [payload]
    if not records:
        return {"selection_log_records_empty"}
    errors: set[str] = set()
    for record_value in records:
        record = _dict(record_value)
        selected_index = _as_int(record.get("selected_index"))
        executed_index = _as_int(record.get("executed_index"))
        shadow_selected_index = _as_int(record.get("shadow_selected_index"))
        num_candidates = _as_int(record.get("num_candidates"))
        selector = _dict(record.get("default_off_shadow_selector"))
        if selected_index != 0:
            errors.add("default_off_selected_index_not_zero")
        if executed_index != 0:
            errors.add("default_off_executed_index_not_zero")
        if shadow_selected_index is None:
            errors.add("shadow_selected_index_missing")
        if num_candidates is None or num_candidates <= 0:
            errors.add("num_candidates_invalid")
        elif shadow_selected_index is not None and not (0 <= shadow_selected_index < num_candidates):
            errors.add("shadow_selected_index_out_of_range")
        if selector.get("schema_version") != DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION:
            errors.add("selector_schema_mismatch")
        if selector.get("enabled") is not True or selector.get("default_off") is not True:
            errors.add("selector_not_default_off_enabled")
        if selector.get("candidate_operation") != "fixed DP candidate reranking only":
            errors.add("selector_candidate_operation_mismatch")
        if selector.get("executed_output_policy") != "dp_top1":
            errors.add("selector_executed_output_not_dp_top1")
        if selector.get("score_expression") != SCORE_EXPRESSION:
            errors.add("selector_score_expression_mismatch")
        if selector.get("selection_effect") is not False:
            errors.add("selector_selection_effect_not_false")
        if selector.get("online_selector_change") is not False:
            errors.add("selector_online_change_not_false")
        if _as_int(selector.get("executed_index")) != executed_index:
            errors.add("selector_executed_index_mismatch")
        if _as_int(selector.get("shadow_selected_index")) != shadow_selected_index:
            errors.add("selector_shadow_selected_index_mismatch")
    return errors


def _write_outputs(
    *,
    output_paths: dict[str, Path],
    selected: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    zero_counts: dict[str, int],
    selected_sets: dict[str, set[str]],
    training_registries: dict[str, set[str]],
) -> None:
    output_paths["manifest"].parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_paths["manifest"],
        {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "members": selected,
            "rejected_members": rejected,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "default_off_execution": "selected_index=0 and executed_index=0 for every record",
            "fixed_dp_candidate_generation_executed": False,
            "training_executed": False,
        },
    )
    registry_specs = {
        "candidate_tensor_hash_registry": "candidate_tensor_hashes",
        "path_signature_registry": "path_signatures",
        "record_identity_registry": "record_identity_hashes",
        "split_manifest_root_registry": "split_manifest_roots",
    }
    for path_key, set_key in registry_specs.items():
        _write_json(
            output_paths[path_key],
            {
                "schema_version": REGISTRY_SCHEMA_VERSION,
                "values": sorted(selected_sets[set_key]),
                "value_count": len(selected_sets[set_key]),
            },
        )
    _write_json(
        output_paths["preflight_inputs"],
        {
            "schema_version": PREFLIGHT_INPUTS_SCHEMA_VERSION,
            "zero_intersection_counts": zero_counts,
            "candidate_tensor_hash_registry_json": str(output_paths["candidate_tensor_hash_registry"]),
            "path_signature_registry_json": str(output_paths["path_signature_registry"]),
            "record_identity_registry_json": str(output_paths["record_identity_registry"]),
            "split_manifest_root_registry_json": str(output_paths["split_manifest_root_registry"]),
            "training_registry_counts": {key: len(value) for key, value in training_registries.items()},
        },
    )
    sha_lines = []
    for name in OUTPUT_FILES:
        path = output_paths[_output_key(name)]
        sha_lines.append(f"{_sha256(path)}  {name}")
    output_paths["sha256sums"].write_text("\n".join(sha_lines) + "\n", encoding="utf-8")


def _output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "manifest": output_dir / "default_off_member_source_generation_manifest.json",
        "candidate_tensor_hash_registry": output_dir / "candidate_tensor_hash_registry.json",
        "path_signature_registry": output_dir / "path_signature_registry.json",
        "record_identity_registry": output_dir / "record_identity_registry.json",
        "split_manifest_root_registry": output_dir / "split_manifest_root_registry.json",
        "preflight_inputs": output_dir / "zero_overlap_preflight_inputs.json",
        "sha256sums": output_dir / "SHA256SUMS",
    }


def _output_key(filename: str) -> str:
    return {
        "default_off_member_source_generation_manifest.json": "manifest",
        "candidate_tensor_hash_registry.json": "candidate_tensor_hash_registry",
        "path_signature_registry.json": "path_signature_registry",
        "record_identity_registry.json": "record_identity_registry",
        "split_manifest_root_registry.json": "split_manifest_root_registry",
        "zero_overlap_preflight_inputs.json": "preflight_inputs",
    }[filename]


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "schema_version": payload.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_authorized_next": decision.get("implementation_authorized_next"),
        **{flag: decision.get(flag) for flag in SOURCE_FALSE_FLAGS},
    }


def _member_sets(members: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {
        "candidate_tensor_hashes": set().union(*(set(member["candidate_tensor_hashes"]) for member in members)) if members else set(),
        "path_signatures": set().union(*(set(member["path_signatures"]) for member in members)) if members else set(),
        "record_identity_hashes": set().union(*(set(member["record_identity_hashes"]) for member in members)) if members else set(),
        "split_manifest_roots": set().union(*(set(member["split_manifest_roots"]) for member in members)) if members else set(),
    }


def _zero_counts(
    selected_sets: dict[str, set[str]],
    training_registries: dict[str, set[str]],
) -> dict[str, int]:
    return {
        "candidate_tensor_hash_intersection_count": len(selected_sets["candidate_tensor_hashes"] & training_registries["candidate_tensor_hashes"]),
        "path_signature_intersection_count": len(selected_sets["path_signatures"] & training_registries["path_signatures"]),
        "record_identity_intersection_count": len(selected_sets["record_identity_hashes"] & training_registries["record_identity_hashes"]),
        "split_manifest_root_intersection_count": len(selected_sets["split_manifest_roots"] & training_registries["split_manifest_roots"]),
    }


def _reason_counts(rejected: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in rejected:
        for reason in _list(item.get("reasons")):
            counts[str(reason)] = counts.get(str(reason), 0) + 1
    return dict(sorted(counts.items()))


def _values(payload: dict[str, Any], keys: tuple[str, ...]) -> set[str]:
    values: set[str] = set()
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            values.update(str(item) for item in value if str(item))
        elif value:
            values.add(str(value))
    return values


def _load_registry_values(path: Path) -> set[str]:
    payload = _load_json_dict(path)
    values = set()
    for key in ("values", "items", "hashes", "signatures", "roots"):
        values.update(_values(payload, (key,)))
    values.update(str(key) for key in payload.keys() if key not in {"schema_version", "value_count"})
    return {value for value in values if value}


def _decision(
    *,
    passed: bool,
    failed: list[str],
    enabled: bool,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": (READY_STATUS if passed else REJECT_STATUS) if enabled else DISABLED_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "implementation_complete": passed,
        "post_implementation_static_contract_review_authorized_next": passed,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "replay_execution_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "fixed_dp_candidate_generation_executed": False,
        "training_executed": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
    if isinstance(value, set):
        return sorted(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
