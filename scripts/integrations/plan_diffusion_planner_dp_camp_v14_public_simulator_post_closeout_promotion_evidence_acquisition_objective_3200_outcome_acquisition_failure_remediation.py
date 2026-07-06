#!/usr/bin/env python3
"""Plan remediation after objective-3200 outcome acquisition failed.

This gate is read-only and plan/preflight only. It consumes the audited failed
objective-3200 outcome acquisition execution artifact, preserves the strict
3200 per-record objective, and preregisters the next static-review boundary for
a fixed-DP candidate-index replay/outcome-acquisition harness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_outcome_acquisition_failure_remediation_plan_v1"
)
SOURCE_EXECUTION_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_outcome_acquisition_execution_v1"
)
SOURCE_FAILURE_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_execution_failed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_execution_failed_user_decision_required"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_failure_remediation_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_failure_remediation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_failure_remediation_plan_static_review_only"
)

PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_failure_remediation_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_failure_remediation_plan.md"
)

OBJECTIVE_REQUIRED_RECORDS = 3200
EXPECTED_EXISTING_RUN_LEVEL_PAIR_COUNT = 32
EXPECTED_FAILED_SOURCE_RECORDS = 0
EXPECTED_MISSING_RECORDS = 3200
EXPECTED_PAIRED_RECORD_KEYS = 3200

BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "training_authorized",
    "training_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
)
FALSE_EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "replay_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
    "outcome_acquisition_executed_by_this_gate",
    "actual_safetycost_outcome_materialization_executed_by_this_gate",
)
SOURCE_EXECUTION_TRUE_FLAGS = {"outcome_acquisition_executed_by_this_gate"}
ANALYSIS_FALSE_FLAGS = (
    "paired_evaluation_execution",
    "candidate_index_replay_execution",
    "outcome_acquisition_execution",
    "training_execution",
    "candidate_generation",
    "dp_modification",
    "candidate_tensor_modification",
    "online_selector_change",
    "promotion_executed",
    "deployment_executed",
    "safety_or_camp_over_dp_claim",
)

EXPECTED_REMEDIATION_PLAN_ITEMS = (
    "static_review_failed_execution_and_runner_capability",
    "pre_register_fixed_candidate_index_replay_harness_contract",
    "implement_or_verify_candidate_index_binding_without_dp_modification",
    "preflight_candidate_index_replay_artifact_contract",
    "execute_candidate_index_outcome_acquisition_only_after_static_review",
    "materialize_actual_safetycost_after_3200_outcomes",
)
EXPECTED_NO_GO = (
    "dp_head_drift",
    "source_failed_execution_artifact_missing_or_not_failed_closed",
    "candidate_tensor_identity_missing_or_mutated",
    "shadow_selected_candidate_not_bound_by_record_key_and_candidate_index",
    "camp_generates_repairs_rewrites_or_blends_trajectory",
    "full36_or_formal_seed_11_12_13_present",
    "closed_loop_outcome_used_for_training_or_online_input",
    "non_affine_score_or_non_simplex_weight",
    "promotion_deployment_online_selector_or_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failed_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--failed_execution_json", type=Path, required=True)
    parser.add_argument("--failed_execution_md", type=Path, required=True)
    parser.add_argument("--failed_execution_sha256s", type=Path, required=True)
    parser.add_argument("--runtime_replay_script_py", type=Path, required=True)
    parser.add_argument("--shadow_outcome_preflight_script_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_failure_remediation_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        failed_execution_artifact_dir=args.failed_execution_artifact_dir,
        failed_execution_json=args.failed_execution_json,
        failed_execution_md=args.failed_execution_md,
        failed_execution_sha256s=args.failed_execution_sha256s,
        runtime_replay_script_py=args.runtime_replay_script_py,
        shadow_outcome_preflight_script_py=args.shadow_outcome_preflight_script_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_failure_remediation_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    failed_execution_artifact_dir: Path,
    failed_execution_json: Path,
    failed_execution_md: Path,
    failed_execution_sha256s: Path,
    runtime_replay_script_py: Path,
    shadow_outcome_preflight_script_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = failed_execution_artifact_dir.resolve()
    paths = {
        "failed_execution_json": failed_execution_json.resolve(),
        "failed_execution_md": failed_execution_md.resolve(),
        "failed_execution_sha256s": failed_execution_sha256s.resolve(),
        "runtime_replay_script_py": runtime_replay_script_py.resolve(),
        "shadow_outcome_preflight_script_py": shadow_outcome_preflight_script_py.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    artifact_files = {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
    }
    source_execution = _read_json_dict(paths["failed_execution_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    nested_sha256s = _read_sha256sums(paths["failed_execution_sha256s"])
    run_exit = _read_text(artifact_files["run_exit"]).strip()
    runtime_script = _read_text(paths["runtime_replay_script_py"])
    shadow_preflight_script = _read_text(paths["shadow_outcome_preflight_script_py"])
    failure = _source_failure_summary(source_execution)
    capability = _capability_inventory(
        runtime_script=runtime_script,
        shadow_preflight_script=shadow_preflight_script,
    )
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        artifact_files=artifact_files,
        source_execution=source_execution,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        failure=failure,
        capability=capability,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "plan_preflight_only": True,
            "source_failure_review": True,
            "strict_objective_3200_preserved": True,
            "selected_remediation_path": "fixed_dp_candidate_index_replay_outcome_acquisition",
            "run_level_32_downgrade_selected": False,
            "score_expression": SCORE_EXPRESSION,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            **{flag: False for flag in ANALYSIS_FALSE_FLAGS},
        },
        "inputs": {
            "failed_execution_artifact_dir": str(artifact_dir),
            "output_dir": str(output_dir.resolve()),
            **{name: str(path) for name, path in paths.items()},
        },
        "source_artifact_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_failed_execution_camp_head": _kv(heads, "CAMP_HEAD", "camp_head"),
            "source_failed_execution_camp_origin_main": _kv(
                heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"
            ),
            "source_failed_execution_dp_head": _kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_failed_execution_summary": failure,
        "runner_capability_inventory": capability,
        "remediation_plan": _remediation_plan(capability),
        "paired_evaluation_protocol": _paired_evaluation_protocol(),
        "artifact_contract": _artifact_contract(),
        "no_go_register": [{"name": name} for name in EXPECTED_NO_GO],
        "plan_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, failure=failure, capability=capability),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    artifact_files: dict[str, Path],
    source_execution: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    failure: dict[str, Any],
    capability: dict[str, Any],
) -> list[dict[str, Any]]:
    decision = _dict(source_execution.get("final_decision"))
    analysis = _dict(source_execution.get("analysis"))
    checks = [
        _expect("remediation_plan_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_FAILURE_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_FAILURE_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _check("source_failed_execution_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        _expect("source_failed_execution_run_exit_failed_closed", run_exit, "1"),
        _expect("source_failed_execution_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        _expect(
            "source_failed_execution_camp_head_matches_origin",
            _kv(heads, "CAMP_HEAD", "camp_head"),
            _kv(heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"),
        ),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, allow_empty=False))
    for name, path in artifact_files.items():
        checks.extend(_path_checks(f"artifact_{name}", path, allow_empty=(name == "stderr")))
    checks.extend(_source_hash_checks(paths, root_sha256s, nested_sha256s))
    checks.extend(
        [
            _expect("source_execution_schema", source_execution.get("schema_version"), SOURCE_EXECUTION_SCHEMA),
            _expect("source_execution_passed_false", decision.get("passed"), False),
            _expect("source_execution_status", decision.get("status"), SOURCE_FAILURE_STATUS),
            _expect(
                "source_execution_failure_class",
                decision.get("failure_class"),
                "objective_3200_outcome_acquisition_execution_source_missing",
            ),
            _expect("source_execution_authorized_next_none", decision.get("authorized_next_work"), None),
            _expect("source_execution_recommended_next_work", decision.get("recommended_next_work"), AUTHORIZED_CURRENT_WORK),
            _expect("source_execution_objective_required_records", failure["objective_required_records"], OBJECTIVE_REQUIRED_RECORDS),
            _expect("source_execution_runtime_records", failure["runtime_record_count"], OBJECTIVE_REQUIRED_RECORDS),
            _expect("source_execution_paired_record_keys", failure["paired_record_key_count"], EXPECTED_PAIRED_RECORD_KEYS),
            _expect("source_execution_candidate_outcome_records", failure["candidate_closed_loop_outcome_records"], EXPECTED_FAILED_SOURCE_RECORDS),
            _expect("source_execution_missing_outcome_records", failure["missing_candidate_closed_loop_outcome_records"], EXPECTED_MISSING_RECORDS),
            _expect("source_execution_satisfied_false", failure["objective_3200_outcome_acquisition_satisfied"], False),
            _expect("source_execution_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False),
            _expect("source_execution_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False),
            _expect("source_analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
            _expect("runtime_script_has_collect_closed_loop_flag", capability["runtime_script_has_collect_closed_loop_flag"], True),
            _expect("runtime_script_lacks_candidate_index_replay_flag", capability["runtime_script_has_candidate_index_replay_flag"], False),
            _expect("shadow_preflight_removes_default_off_selector", capability["shadow_preflight_removes_default_off_selector"], True),
            _expect("shadow_preflight_forbids_closed_loop_collection", capability["shadow_preflight_forbids_closed_loop_collection"], True),
        ]
    )
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(_expect(f"source_execution_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision and flag not in SOURCE_EXECUTION_TRUE_FLAGS:
            checks.append(_expect(f"source_execution_{flag}", decision.get(flag), False))
    return checks


def _source_hash_checks(
    paths: dict[str, Path],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _expect(
            "source_root_execution_json_sha",
            _sha_for_suffix(root_sha256s, paths["failed_execution_json"].name),
            _sha256(paths["failed_execution_json"]),
        ),
        _expect(
            "source_root_execution_md_sha",
            _sha_for_suffix(root_sha256s, paths["failed_execution_md"].name),
            _sha256(paths["failed_execution_md"]),
        ),
        _expect(
            "source_nested_execution_json_sha",
            _sha_for_suffix(nested_sha256s, paths["failed_execution_json"].name),
            _sha256(paths["failed_execution_json"]),
        ),
        _expect(
            "source_nested_execution_md_sha",
            _sha_for_suffix(nested_sha256s, paths["failed_execution_md"].name),
            _sha256(paths["failed_execution_md"]),
        ),
    ]


def _source_failure_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_execution.get("final_decision"))
    acquisition = _dict(source_execution.get("objective_3200_outcome_acquisition_summary"))
    candidate = _dict(source_execution.get("candidate_outcome_source_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "failure_class": decision.get("failure_class"),
        "failed_checks": _list(decision.get("failed_checks")),
        "objective_required_records": int(
            decision.get("objective_required_records")
            or acquisition.get("objective_required_records")
            or OBJECTIVE_REQUIRED_RECORDS
        ),
        "runtime_record_count": int(
            decision.get("runtime_record_count")
            or acquisition.get("runtime_record_count")
            or 0
        ),
        "paired_record_key_count": int(
            decision.get("paired_record_key_count")
            or acquisition.get("paired_record_key_count")
            or 0
        ),
        "candidate_source_record_count": int(
            acquisition.get("candidate_source_record_count")
            or candidate.get("record_count")
            or 0
        ),
        "candidate_closed_loop_outcome_records": int(
            decision.get("candidate_closed_loop_outcome_records")
            or acquisition.get("candidate_closed_loop_outcome_records")
            or candidate.get("candidate_closed_loop_outcome_records")
            or 0
        ),
        "missing_candidate_closed_loop_outcome_records": int(
            decision.get("missing_candidate_closed_loop_outcome_records")
            or acquisition.get("missing_candidate_closed_loop_outcome_records")
            or candidate.get("missing_candidate_closed_loop_outcome_records")
            or 0
        ),
        "objective_3200_outcome_acquisition_satisfied": bool(
            decision.get("objective_3200_outcome_acquisition_satisfied")
            or acquisition.get("objective_3200_outcome_acquisition_satisfied")
        ),
        "no_go_failures": _list(_dict(source_execution.get("no_go_report")).get("failures")),
    }


def _capability_inventory(*, runtime_script: str, shadow_preflight_script: str) -> dict[str, Any]:
    candidate_index_flags = (
        "--camp_force_candidate_index",
        "--camp_fixed_candidate_index",
        "--camp_selected_candidate_index",
        "--fixed_candidate_index",
        "--candidate_index_replay",
    )
    return {
        "runtime_script_has_collect_closed_loop_flag": "--camp_collect_closed_loop_outcomes" in runtime_script,
        "runtime_script_has_default_off_shadow_selector": "--camp_default_off_shadow_selector" in runtime_script,
        "runtime_script_logs_shadow_selected_index": "shadow_selected_index" in runtime_script,
        "runtime_script_executed_output_policy_dp_top1": "executed_output_policy" in runtime_script
        and "dp_top1" in runtime_script,
        "runtime_script_has_candidate_index_replay_flag": any(flag in runtime_script for flag in candidate_index_flags),
        "candidate_index_replay_flag_candidates_checked": list(candidate_index_flags),
        "paper_faithful_boundary_mentions_collect_closed_loop": "camp_collect_closed_loop_outcomes" in runtime_script
        and "PAPER_FAITHFUL_BOUNDARY_ERROR" in runtime_script,
        "shadow_preflight_removes_default_off_selector": "--camp_default_off_shadow_selector" in shadow_preflight_script
        and "REMOVE_FLAGS" in shadow_preflight_script,
        "shadow_preflight_forbids_closed_loop_collection": "--camp_collect_closed_loop_outcomes" in shadow_preflight_script
        and "FORBIDDEN_GENERATED_FLAGS" in shadow_preflight_script,
        "shadow_preflight_is_run_level_command_transform": "_transform_command" in shadow_preflight_script
        and "expected_command_count" in shadow_preflight_script,
        "current_capability_conclusion": "candidate_index_replay_harness_not_yet_audited",
    }


def _remediation_plan(capability: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "static_review_failed_execution_and_runner_capability",
            "this_gate": True,
            "executes_replay": False,
            "purpose": "Preserve the failed source artifact and document why existing artifacts provide 0/3200 per-record shadow outcomes.",
        },
        {
            "name": "pre_register_fixed_candidate_index_replay_harness_contract",
            "this_gate": True,
            "executes_replay": False,
            "purpose": "Require the next gate to prove any replay harness can bind each record to the logged shadow_selected_index from the same fixed DP candidate tensor.",
        },
        {
            "name": "implement_or_verify_candidate_index_binding_without_dp_modification",
            "this_gate": False,
            "executes_replay": False,
            "purpose": "If no audited flag exists, add only CAMP-side harness support that selects an existing candidate index without modifying DP code, config, weights, or checkpoint.",
            "current_candidate_index_flag_present": capability["runtime_script_has_candidate_index_replay_flag"],
        },
        {
            "name": "preflight_candidate_index_replay_artifact_contract",
            "this_gate": False,
            "executes_replay": False,
            "purpose": "Before execution, lock row manifest, candidate tensor digest, shadow_selected_index, source runbook, no-go checks, HEADS, COMMAND, stdout, stderr, JSON/MD, and SHA256SUMS.",
        },
        {
            "name": "execute_candidate_index_outcome_acquisition_only_after_static_review",
            "this_gate": False,
            "executes_replay": False,
            "purpose": "Future execution may acquire outcomes only after static review passes and must fail closed unless all 3200 selected fixed candidates produce per-record outcomes.",
        },
        {
            "name": "materialize_actual_safetycost_after_3200_outcomes",
            "this_gate": False,
            "executes_replay": False,
            "purpose": "Only after 3200 CAMP-selected outcomes exist, pair them with same-key DP Top-1 outcomes and evaluate Actual SafetyCost v1.",
        },
    ]


def _paired_evaluation_protocol() -> dict[str, Any]:
    return {
        "objective_required_records": OBJECTIVE_REQUIRED_RECORDS,
        "unit": "per_record_shadow_selected_fixed_dp_candidate_closed_loop_outcome",
        "camp_candidate_source": "logged shadow_selected_index over immutable fixed DP candidate tensor",
        "top1_candidate_source": "candidate_index_0 from same fixed DP candidate tensor and same record key",
        "pairing_keys": ["scenario", "seed", "traffic_light_mode", "sample", "selection_step"],
        "primary_metric": "Actual SafetyCost v1 paired CAMP shadow-selected minus DP Top-1",
        "pass_rule_before_any_claim": "all 3200 paired outcomes present, no no-go failures, paired CI and better/worse rule preregistered in a later review",
        "forbidden": [
            "Full36",
            "formal seeds 11/12/13",
            "closed-loop outcomes as training or online input",
            "DP code/config/weights/checkpoint modification",
            "trajectory generation repair rewrite blend",
            "reference_blend guidance postprocess postselection",
        ],
    }


def _artifact_contract() -> dict[str, Any]:
    return {
        "required_root_files": ["HEADS", "COMMAND", "stdout", "stderr", "run.exit", "SHA256SUMS"],
        "required_nested_files": [PLAN_JSON_NAME, PLAN_MD_NAME, "SHA256SUMS"],
        "source_artifacts_required": ["objective_3200_outcome_acquisition_execution_failed"],
        "next_gate": AUTHORIZED_NEXT_WORK,
        "execution_authorized_by_this_gate": False,
    }


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    failure: dict[str, Any],
    capability: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "remediation_plan_enabled" in failed:
        failure_class = "explicit_objective_3200_failure_remediation_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_execution_") or name.startswith("source_failed_execution_") for name in failed):
        failure_class = "source_failed_execution_artifact_contract_failure"
    else:
        failure_class = "objective_3200_failure_remediation_plan_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_outcome_acquisition_failure_remediation_plan_ready": bool(passed),
        "objective_3200_outcome_acquisition_failure_remediation_plan_static_review_authorized": bool(passed),
        "candidate_index_replay_harness_static_review_authorized": bool(passed),
        "direct_candidate_index_replay_execution_authorized": False,
        "direct_outcome_acquisition_execution_authorized": False,
        "strict_objective_3200_preserved": True,
        "run_level_32_downgrade_selected": False,
        "objective_required_records": failure["objective_required_records"],
        "candidate_closed_loop_outcome_records": failure["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": failure["missing_candidate_closed_loop_outcome_records"],
        "paired_record_key_count": failure["paired_record_key_count"],
        "runtime_has_candidate_index_replay_flag": capability["runtime_script_has_candidate_index_replay_flag"],
        "requires_candidate_index_replay_harness_review": True,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "recommendation": (
            "static_review_failure_remediation_plan_then_preflight_candidate_index_replay_harness"
            if passed
            else "repair_or_rerun_same_failure_remediation_plan_gate"
        ),
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(
            [
                f"{_sha256(json_path)}  {json_path.name}",
                f"{_sha256(md_path)}  {md_path.name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failure = report["source_failed_execution_summary"]
    capability = report["runner_capability_inventory"]
    return "\n".join(
        [
            "# Objective-3200 Outcome Acquisition Failure Remediation Plan",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "## Source Failure",
            "",
            f"- Runtime records: `{failure['runtime_record_count']}`",
            f"- Paired record keys: `{failure['paired_record_key_count']}`",
            f"- Candidate outcome records: `{failure['candidate_closed_loop_outcome_records']}`",
            f"- Missing candidate outcome records: `{failure['missing_candidate_closed_loop_outcome_records']}`",
            "",
            "## Capability Inventory",
            "",
            f"- Runtime has closed-loop outcome flag: `{capability['runtime_script_has_collect_closed_loop_flag']}`",
            f"- Runtime has audited candidate-index replay flag: `{capability['runtime_script_has_candidate_index_replay_flag']}`",
            f"- Previous shadow preflight forbids closed-loop collection: `{capability['shadow_preflight_forbids_closed_loop_collection']}`",
            "",
            "## Boundary",
            "",
            "- This gate does not run replay, acquire outcomes, train, generate candidates, modify DP, promote, deploy, enable online selection, or make claims.",
            "- The next authorized work is static review only.",
            f"- Score expression: `{report['analysis']['score_expression']}`",
            "",
        ]
    )


def _path_checks(name: str, path: Path, *, allow_empty: bool) -> list[dict[str, Any]]:
    checks = [_check(f"{name}_exists", path.is_file(), str(path), "file")]
    if path.is_file() and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0 bytes"))
    return checks


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_sha256sums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            result[parts[1].strip()] = parts[0]
    return result


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0].strip()


def _kv(mapping: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _sha_for_suffix(mapping: dict[str, str], suffix: str) -> str | None:
    normalized = suffix.replace("\\", "/")
    for path, digest in mapping.items():
        if path.replace("\\", "/").endswith(normalized):
            return digest
    return None


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _check(name: str, passed: bool, actual: Any = None, expected: Any = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual if actual is not None else bool(passed), "expected": expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
