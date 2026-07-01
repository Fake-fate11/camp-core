#!/usr/bin/env python3
"""Post-implementation static review for the v13 fresh split manifest builder.

This gate is read-only. It verifies that the implemented fresh evaluation split
manifest builder and its materialized manifest artifact stayed manifest-only and
inside the fixed-DP reranking boundary before authorizing the next validation
preflight. It does not run Diffusion Planner, generate candidates, prepare
data, replay, train CAMP, modify DP, promote artifacts, deploy, or make
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
TARGET_SELECTION_LOGS = 32
TARGET_RECORDS = 3200
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
EXPECTED_ROUTES_MINIMUM = 4
EXPECTED_SEEDS_MINIMUM = 2
EXPECTED_ROUTE_TL_BUCKETS_MINIMUM = 8
FORMAL_SEEDS = {11, 12, 13}

SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_manifest_builder_"
    "post_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_manifest_builder_"
    "post_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_manifest_builder_"
    "post_implementation_static_contract_review_rejected"
)
SOURCE_BUILDER_SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_manifest_builder_v1"
SOURCE_BUILDER_STATUS = "dp_camp_v13_fresh_evaluation_split_manifest_builder_complete"
SCOPE_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_scope_manifest_v1"
REGISTRY_REPORT_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_nonoverlap_registry_report_v1"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_post_implementation_static_contract_"
    "review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_preflight_only"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_manifest_builder_complete"
)

OUTPUT_HASH_FIELDS = {
    "fresh_evaluation_split_scope_manifest_sha256": (
        "fresh_evaluation_split_scope_manifest.json"
    ),
    "fresh_evaluation_split_nonoverlap_registry_report_sha256": (
        "fresh_evaluation_split_nonoverlap_registry_report.json"
    ),
    "run_fresh_evaluation_split_preflight_sha256": (
        "run_fresh_evaluation_split_preflight.sh"
    ),
    "sha256sums_txt_sha256": "SHA256SUMS.txt",
}

BLOCKED_DECISION_FLAGS = (
    "data_preparation_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only post-implementation static contract review for the v13 "
            "fresh evaluation split manifest builder."
        )
    )
    parser.add_argument("--manifest_builder_json", type=Path, required=True)
    parser.add_argument("--expected_manifest_builder_json_sha256", required=True)
    parser.add_argument("--manifest_builder_script_py", type=Path, required=True)
    parser.add_argument("--manifest_builder_test_py", type=Path, required=True)
    parser.add_argument("--scope_manifest_json", type=Path, required=True)
    parser.add_argument("--nonoverlap_registry_report_json", type=Path, required=True)
    parser.add_argument("--preflight_runbook_sh", type=Path, required=True)
    parser.add_argument("--sha256sums_txt", type=Path, required=True)
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
        manifest_builder_json=args.manifest_builder_json,
        expected_manifest_builder_json_sha256=args.expected_manifest_builder_json_sha256,
        manifest_builder_script_py=args.manifest_builder_script_py,
        manifest_builder_test_py=args.manifest_builder_test_py,
        scope_manifest_json=args.scope_manifest_json,
        nonoverlap_registry_report_json=args.nonoverlap_registry_report_json,
        preflight_runbook_sh=args.preflight_runbook_sh,
        sha256sums_txt=args.sha256sums_txt,
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
    manifest_builder_json: Path,
    expected_manifest_builder_json_sha256: str,
    manifest_builder_script_py: Path,
    manifest_builder_test_py: Path,
    scope_manifest_json: Path,
    nonoverlap_registry_report_json: Path,
    preflight_runbook_sh: Path,
    sha256sums_txt: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "manifest_builder_json": manifest_builder_json.resolve(),
        "manifest_builder_script_py": manifest_builder_script_py.resolve(),
        "manifest_builder_test_py": manifest_builder_test_py.resolve(),
        "scope_manifest_json": scope_manifest_json.resolve(),
        "nonoverlap_registry_report_json": nonoverlap_registry_report_json.resolve(),
        "preflight_runbook_sh": preflight_runbook_sh.resolve(),
        "sha256sums_txt": sha256sums_txt.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    builder_payload = _load_json_dict(paths["manifest_builder_json"])
    scope_manifest = _load_json_dict(paths["scope_manifest_json"])
    registry_report = _load_json_dict(paths["nonoverlap_registry_report_json"])
    script_text = _read_text(paths["manifest_builder_script_py"])
    test_text = _read_text(paths["manifest_builder_test_py"])
    runbook_text = _read_text(paths["preflight_runbook_sh"])
    sha256sums_text = _read_text(paths["sha256sums_txt"])
    audit_text = _read_text(paths["v13_audit_md"])

    checks = _checks(
        paths=paths,
        builder_payload=builder_payload,
        scope_manifest=scope_manifest,
        registry_report=registry_report,
        script_text=script_text,
        test_text=test_text,
        runbook_text=runbook_text,
        sha256sums_text=sha256sums_text,
        audit_text=audit_text,
        expected_manifest_builder_json_sha256=expected_manifest_builder_json_sha256,
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
            "fresh_split_preflight_execution": False,
            "fresh_split_member_selection_execution": False,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
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
        "source_hashes": {
            f"{name}_sha256": _sha256(path) if path.is_file() else None
            for name, path in paths.items()
        },
        "builder_summary": _builder_summary(builder_payload),
        "manifest_summary": _manifest_summary(scope_manifest, registry_report),
        "review_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    manifest = report["manifest_summary"]
    return "\n".join(
        [
            "# V13 Fresh Evaluation Split Manifest Builder Post-Implementation Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Fresh split preflight authorized next: `{decision['fresh_evaluation_split_preflight_authorized_next']}`",
            f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
            f"- Replay authorized next: `{decision['replay_execution_authorized_next']}`",
            f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "## Manifest",
            "",
            f"- Target selection logs: `{manifest['target_selection_log_count']}`",
            f"- Target records: `{manifest['target_record_count']}`",
            f"- Future zero-intersection proof required: `{manifest['future_zero_intersection_preflight_required']}`",
            f"- Fresh split members selected by builder: `{manifest['fresh_split_members_selected_by_builder']}`",
            f"- Score expression: `{SCORE_EXPRESSION}`",
            "",
            "This review is read-only. It does not run DP, generate candidates, "
            "prepare data, replay, train CAMP, modify DP, promote, deploy, or "
            "authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _checks(
    *,
    paths: dict[str, Path],
    builder_payload: dict[str, Any],
    scope_manifest: dict[str, Any],
    registry_report: dict[str, Any],
    script_text: str,
    test_text: str,
    runbook_text: str,
    sha256sums_text: str,
    audit_text: str,
    expected_manifest_builder_json_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "expected_manifest_builder_json_sha256_valid",
            _is_sha256(expected_manifest_builder_json_sha256),
            expected_manifest_builder_json_sha256,
            "64-char sha256",
        ),
    ]
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    if paths["manifest_builder_json"].is_file():
        checks.append(
            _expect(
                "manifest_builder_json_sha256_matches_expected",
                _sha256(paths["manifest_builder_json"]),
                expected_manifest_builder_json_sha256.lower(),
            )
        )
    checks.extend(_builder_artifact_checks(builder_payload, authorized_current_work))
    checks.extend(_scope_manifest_checks(scope_manifest))
    checks.extend(_registry_report_checks(registry_report))
    checks.extend(_output_hash_checks(paths, builder_payload, sha256sums_text))
    checks.extend(_script_contract_checks(script_text))
    checks.extend(_test_contract_checks(test_text))
    checks.extend(_runbook_checks(runbook_text))
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _builder_artifact_checks(
    payload: dict[str, Any],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    heads = _dict(payload.get("heads"))
    checks = [
        _expect("builder_schema_version", payload.get("schema_version"), SOURCE_BUILDER_SCHEMA_VERSION),
        _expect("builder_status_complete", decision.get("status"), SOURCE_BUILDER_STATUS),
        _expect("builder_passed", decision.get("passed"), True),
        _expect("builder_enabled", decision.get("enabled"), True),
        _expect("builder_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("builder_manifest_files_written", decision.get("manifest_files_written"), True),
        _expect("builder_authorizes_current_gate", decision.get("authorized_next_work"), authorized_current_work),
        _expect(
            "builder_authorizes_post_review_only",
            decision.get("post_implementation_static_contract_review_authorized_next"),
            True,
        ),
        _expect("builder_implemented", decision.get("fresh_evaluation_split_manifest_builder_implemented"), True),
        _expect("builder_did_not_select_fresh_members", decision.get("fresh_evaluation_split_members_selected"), False),
        _expect("builder_did_not_execute_zero_proof", decision.get("zero_intersection_proof_executed_by_this_gate"), False),
        _expect("builder_requires_future_zero_proof", decision.get("future_zero_intersection_preflight_required"), True),
        _expect("builder_analysis_manifest_only", analysis.get("manifest_builder_only"), True),
        _expect("builder_analysis_candidate_operation", analysis.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("builder_analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
        _expect("builder_artifact_camp_head_matches_origin", heads.get("current_camp_head"), heads.get("current_camp_origin_main")),
        _expect("builder_artifact_dp_head_fixed", heads.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("builder_required_dp_head_fixed", heads.get("required_dp_head"), FIXED_DP_HEAD),
    ]
    for flag in BLOCKED_DECISION_FLAGS:
        checks.append(_expect(f"builder_blocks_{flag}", decision.get(flag), False))
    for flag in (
        "data_preparation_executed",
        "fixed_dp_candidate_generation_executed",
        "replay_executed",
        "training_executed",
        "dp_modification_executed",
    ):
        checks.append(_expect(f"builder_did_not_{flag}", decision.get(flag), False))
    return checks


def _scope_manifest_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    executions = _dict(payload.get("executions_requested_by_this_manifest"))
    proof = _dict(payload.get("future_preflight_must_prove"))
    runtime = _dict(payload.get("required_runtime_contract"))
    must_exclude = _dict(payload.get("must_exclude"))
    checks = [
        _expect("scope_manifest_schema_version", payload.get("schema_version"), SCOPE_MANIFEST_SCHEMA_VERSION),
        _expect("scope_target_selection_log_count", payload.get("target_selection_log_count"), TARGET_SELECTION_LOGS),
        _expect("scope_target_record_count", payload.get("target_record_count"), TARGET_RECORDS),
        _expect("scope_expected_steps_per_log", payload.get("expected_steps_per_log"), EXPECTED_STEPS_PER_LOG),
        _expect("scope_expected_candidate_count", payload.get("expected_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("scope_expected_atom_count", payload.get("expected_atom_count"), EXPECTED_ATOM_COUNT),
        _expect("scope_routes_minimum", payload.get("routes_minimum"), EXPECTED_ROUTES_MINIMUM),
        _expect("scope_seeds_minimum", payload.get("seeds_minimum"), EXPECTED_SEEDS_MINIMUM),
        _expect("scope_route_tl_buckets_minimum", payload.get("route_traffic_light_buckets_minimum"), EXPECTED_ROUTE_TL_BUCKETS_MINIMUM),
        _expect("scope_candidate_operation", payload.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("scope_score_expression", payload.get("score_expression"), SCORE_EXPRESSION),
        _expect("scope_nonnegative_simplex", payload.get("nonnegative_simplex_weights_only"), True),
        _expect("scope_members_not_selected_by_builder", payload.get("fresh_split_members_selected_by_this_builder"), False),
        _expect("scope_member_count_zero", payload.get("fresh_split_member_count_selected_by_this_builder"), 0),
        _expect("scope_requires_default_off_shadow_selector", runtime.get("default_off_shadow_selector"), True),
        _expect("scope_requires_executed_dp_top1", runtime.get("executed_dp_top1"), True),
        _expect("scope_blocks_reference_blend", runtime.get("reference_blend"), False),
        _expect("scope_blocks_guidance", runtime.get("guidance"), False),
        _expect("scope_blocks_postprocess", runtime.get("postprocess_or_postselection"), False),
        _expect("scope_blocks_closed_loop_outcomes", runtime.get("closed_loop_outcomes_as_training_or_online_input"), False),
        _expect("scope_excludes_formal_seeds", must_exclude.get("formal_seeds_11_12_13"), True),
        _expect("scope_excludes_full36", must_exclude.get("full36"), True),
    ]
    for key in (
        "candidate_tensor_hash_intersection_count",
        "path_signature_intersection_count",
        "record_identity_intersection_count",
        "split_manifest_root_intersection_count",
    ):
        checks.append(_expect(f"scope_future_preflight_requires_zero_{key}", proof.get(key), 0))
    for key in (
        "fixed_dp_candidate_generation",
        "data_preparation",
        "replay",
        "training",
        "dp_modification",
        "selector_or_atom_promotion",
        "deployment",
    ):
        checks.append(_expect(f"scope_requests_no_{key}", executions.get(key), False))
    return checks


def _registry_report_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = _dict(payload.get("nonoverlap_requirements_for_future_fresh_split"))
    forbidden = _dict(payload.get("forbidden_operations"))
    rejected = _dict(payload.get("rejected_source_overlap_is_exclusion_evidence"))
    checks = [
        _expect("registry_report_schema_version", payload.get("schema_version"), REGISTRY_REPORT_SCHEMA_VERSION),
        _expect("registry_zero_proof_not_executed_by_builder", payload.get("zero_intersection_proof_executed_by_this_builder"), False),
        _expect("registry_future_zero_preflight_required", payload.get("future_zero_intersection_preflight_required"), True),
        _check("registry_rejected_candidate_overlap_positive", _int(rejected.get("candidate_hash_intersection_count")) > 0, rejected.get("candidate_hash_intersection_count"), ">0"),
        _check("registry_rejected_path_overlap_positive", _int(rejected.get("path_signature_intersection_count")) > 0, rejected.get("path_signature_intersection_count"), ">0"),
        _check("registry_rejected_record_overlap_positive", _int(rejected.get("record_identity_intersection_count")) > 0, rejected.get("record_identity_intersection_count"), ">0"),
    ]
    for key in (
        "candidate_tensor_hash_intersection_count",
        "path_signature_intersection_count",
        "record_identity_intersection_count",
        "split_manifest_root_intersection_count",
    ):
        checks.append(_expect(f"registry_future_requires_zero_{key}", requirements.get(key), 0))
    for key in (
        "fixed_dp_candidate_generation",
        "candidate_generation_by_camp",
        "trajectory_generation_by_camp",
        "trajectory_modification_by_camp",
        "reference_blend",
        "guidance",
        "postprocess_or_postselection",
        "closed_loop_outcome_input",
        "replay",
        "training",
        "dp_modification",
        "promotion",
        "claims",
    ):
        checks.append(_expect(f"registry_forbids_{key}", forbidden.get(key), True))
    return checks


def _output_hash_checks(
    paths: dict[str, Path],
    builder_payload: dict[str, Any],
    sha256sums_text: str,
) -> list[dict[str, Any]]:
    output_hashes = _dict(builder_payload.get("output_hashes"))
    sha_entries = _sha256sum_entries(sha256sums_text)
    artifact_dir = paths["scope_manifest_json"].parent
    checks: list[dict[str, Any]] = []
    for field, filename in OUTPUT_HASH_FIELDS.items():
        path = paths["sha256sums_txt"] if filename == "SHA256SUMS.txt" else artifact_dir / filename
        expected = _sha256(path) if path.is_file() else None
        checks.append(_expect(f"output_hash_{field}_matches_file", output_hashes.get(field), expected))
        if filename != "SHA256SUMS.txt":
            checks.append(_expect(f"sha256sums_entry_{_slug(filename)}", sha_entries.get(filename), expected))
    checks.append(
        _check(
            "sha256sums_excludes_report_json",
            "fresh_evaluation_split_manifest_builder_report.json" not in sha_entries,
            sorted(sha_entries),
            "no report json entry",
        )
    )
    return checks


def _script_contract_checks(text: str) -> list[dict[str, Any]]:
    needles = {
        "builder_default_off_disabled_status": "default_off_disabled",
        "builder_enable_flag_present": "--enable_v13_fresh_evaluation_split_manifest_builder",
        "builder_returns_before_reads_when_disabled": "if not enabled:\n        return report",
        "builder_manifest_only_analysis": "\"manifest_builder_only\": True",
        "builder_no_data_preparation_execution": "\"data_preparation_execution\": False",
        "builder_no_fixed_dp_generation_execution": "\"fixed_dp_candidate_generation_execution\": False",
        "builder_no_training_execution": "\"training_execution\": False",
        "builder_no_replay_execution": "\"replay_execution\": False",
        "builder_no_dp_modification": "\"dp_modification\": False",
        "builder_no_camp_candidate_generation": "\"candidate_generation_by_camp\": False",
        "builder_score_expression": SCORE_EXPRESSION,
        "builder_formal_seed_constant": "FORMAL_SEEDS = {11, 12, 13}",
        "builder_output_files_constant": "OUTPUT_FILES = (",
        "builder_write_sha256sums_output_files_only": "_write_sha256sums(args.output_dir, list(OUTPUT_FILES))",
        "builder_writes_scope_manifest": "fresh_evaluation_split_scope_manifest.json",
        "builder_writes_registry_report": "fresh_evaluation_split_nonoverlap_registry_report.json",
        "builder_writes_preflight_runbook": "run_fresh_evaluation_split_preflight.sh",
        "builder_future_zero_proof_required": "\"future_zero_intersection_preflight_required\": True",
        "builder_fresh_members_not_selected": "\"fresh_evaluation_split_members_selected\": False",
    }
    return [_contains(name, text, needle) for name, needle in needles.items()]


def _test_contract_checks(text: str) -> list[dict[str, Any]]:
    needles = {
        "test_default_off_no_side_effects": "test_manifest_builder_is_default_off_and_has_no_side_effects",
        "test_manifest_only_outputs": "test_manifest_builder_writes_manifest_only_outputs_when_enabled",
        "test_sha256sums_excludes_report": '"fresh_evaluation_split_manifest_builder_report.json" not in sha_text',
        "test_rejects_wrong_audit_target": "test_manifest_builder_rejects_wrong_audit_target",
        "test_rejects_source_action_leak": "test_manifest_builder_rejects_source_action_leak",
        "test_rejects_missing_required_behavior": "test_manifest_builder_rejects_missing_required_behavior",
        "test_accepts_optional_scope_minima_absent": "test_manifest_builder_accepts_static_review_without_optional_scope_minima",
        "test_rejects_empty_recovered_registry": "test_manifest_builder_rejects_empty_recovered_registry",
        "test_rejects_missing_registry_file": "test_manifest_builder_rejects_missing_registry_file",
        "test_rejects_formal_seed": "test_manifest_builder_rejects_formal_seed_in_training_manifest",
        "test_rejects_dp_drift": "test_manifest_builder_rejects_dp_head_drift",
        "test_rejects_output_escape": "test_manifest_builder_rejects_output_path_outside_output_dir",
    }
    return [_contains(name, text, needle) for name, needle in needles.items()]


def _runbook_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains("runbook_validation_only", text, "validation-only runbook"),
        _contains("runbook_checks_sha256sums", text, "sha256sum -c SHA256SUMS.txt"),
        _contains("runbook_no_dp_execution", text, "no DP execution"),
        _contains("runbook_no_candidate_generation", text, "no candidate generation"),
        _contains("runbook_no_replay", text, "no replay"),
        _contains("runbook_no_training", text, "no training"),
    ]


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_next_work_target", _latest_audit_value(text, "next_work_target"), authorized_current_work),
        _expect("audit_latest_status_manifest_builder_complete", _latest_audit_value(text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_authorizes_post_review", _latest_audit_value(text, "post_implementation_static_contract_review_authorized_next"), "True"),
        _expect("audit_blocks_data_preparation", _latest_audit_value(text, "data_preparation_authorized_next"), "False"),
        _expect("audit_blocks_training_preflight", _latest_audit_value(text, "training_preflight_authorized_next"), "False"),
        _expect("audit_blocks_training", _latest_audit_value(text, "training_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_replay", _latest_audit_value(text, "replay_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_fixed_dp_generation", _latest_audit_value(text, "fixed_dp_candidate_generation_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_camp_candidate_generation", _latest_audit_value(text, "candidate_generation_by_camp_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_dp_modification", _latest_audit_value(text, "dp_modification_authorized_by_current_boundary"), "False"),
    ]


def _builder_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    output_hashes = _dict(payload.get("output_hashes"))
    return {
        "schema_version": payload.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "enabled": decision.get("enabled"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "manifest_files_written": decision.get("manifest_files_written"),
        "analysis": analysis,
        "output_hashes": output_hashes,
    }


def _manifest_summary(scope_manifest: dict[str, Any], registry_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope_schema_version": scope_manifest.get("schema_version"),
        "registry_schema_version": registry_report.get("schema_version"),
        "target_selection_log_count": scope_manifest.get("target_selection_log_count"),
        "target_record_count": scope_manifest.get("target_record_count"),
        "fresh_split_members_selected_by_builder": scope_manifest.get(
            "fresh_split_members_selected_by_this_builder"
        ),
        "future_zero_intersection_preflight_required": registry_report.get(
            "future_zero_intersection_preflight_required"
        ),
    }


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
        "post_implementation_static_contract_review_complete": passed,
        "fresh_evaluation_split_preflight_authorized_next": passed,
        "fresh_evaluation_split_member_selection_authorized_next": False,
        "data_preparation_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
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
        "fresh_split_preflight_executed": False,
        "data_preparation_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256sum_entries(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and _is_sha256(parts[0]):
            entries[parts[-1]] = parts[0]
    return entries


def _latest_audit_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
