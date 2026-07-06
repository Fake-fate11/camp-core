#!/usr/bin/env python3
"""Read-only review for objective-3200 online selector activation execution."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_execution_module():
    script_path = Path(__file__).resolve().with_name(
        "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_online_selector_activation.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_online_selector_activation_execution",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


EXECUTION_MODULE = _load_execution_module()
BASE_MODULE = EXECUTION_MODULE.BASE_MODULE

FIXED_DP_HEAD = EXECUTION_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = EXECUTION_MODULE.SCORE_EXPRESSION
SOURCE_EXECUTION_SCHEMA = EXECUTION_MODULE.SCHEMA_VERSION
SOURCE_EXECUTION_STATUS = EXECUTION_MODULE.READY_STATUS
SOURCE_EXECUTION_JSON_NAME = EXECUTION_MODULE.EXECUTION_JSON_NAME
SOURCE_EXECUTION_MD_NAME = EXECUTION_MODULE.EXECUTION_MD_NAME
SOURCE_ACTIVATION_STATE_JSON_NAME = EXECUTION_MODULE.ACTIVATION_STATE_JSON_NAME
SOURCE_ONLINE_RUNTIME_MANIFEST_JSON_NAME = EXECUTION_MODULE.ONLINE_RUNTIME_MANIFEST_JSON_NAME
SOURCE_EXECUTION_CHECK_COUNT = 92
SOURCE_REVIEW_CHECK_COUNT = EXECUTION_MODULE.EXPECTED_SOURCE_REVIEW_CHECK_COUNT
SOURCE_SCOPE = EXECUTION_MODULE.SOURCE_SCOPE
EXECUTED_OUTPUT_POLICY = EXECUTION_MODULE.EXECUTED_OUTPUT_POLICY
EXPECTED_CANDIDATE_COUNT = EXECUTION_MODULE.EXPECTED_CANDIDATE_COUNT
AUTHORIZED_CURRENT_WORK = EXECUTION_MODULE.AUTHORIZED_NEXT_WORK

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_online_selector_activation_"
    "execution_result_review_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_"
    "result_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_"
    "result_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_integration_"
    "closeout_record_only"
)
REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_"
    "result_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_"
    "result_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_execution_json", type=Path, required=True)
    parser.add_argument("--source_execution_md", type=Path, required=True)
    parser.add_argument("--source_activation_state_json", type=Path, required=True)
    parser.add_argument("--source_online_runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--source_execution_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_execution_artifact_dir=args.source_execution_artifact_dir,
        source_execution_json=args.source_execution_json,
        source_execution_md=args.source_execution_md,
        source_activation_state_json=args.source_activation_state_json,
        source_online_runtime_manifest_json=args.source_online_runtime_manifest_json,
        source_execution_sha256s=args.source_execution_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_result_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_activation_state_json: Path,
    source_online_runtime_manifest_json: Path,
    source_execution_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_execution_artifact_dir.resolve()
    paths = {
        "source_execution_json": source_execution_json.resolve(),
        "source_execution_md": source_execution_md.resolve(),
        "source_activation_state_json": source_activation_state_json.resolve(),
        "source_online_runtime_manifest_json": source_online_runtime_manifest_json.resolve(),
        "source_execution_sha256s": source_execution_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    files = _artifact_files(artifact_dir)
    source_execution = BASE_MODULE._read_json_dict(paths["source_execution_json"])
    activation_state = BASE_MODULE._read_json_dict(paths["source_activation_state_json"])
    online_manifest = BASE_MODULE._read_json_dict(paths["source_online_runtime_manifest_json"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(files["heads"]))
    root_sha256s = BASE_MODULE._read_sha256sums(files["root_sha256s"])
    nested_sha256s = BASE_MODULE._read_sha256sums(paths["source_execution_sha256s"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        files=files,
        source_execution=source_execution,
        activation_state=activation_state,
        online_manifest=online_manifest,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "result_review_only": True,
            "online_selector_activation_execution_executed_by_review": False,
            "deployment_executed_by_review": False,
            "training_executed_by_review": False,
            "candidate_generation_executed_by_review": False,
            "dp_modified_by_review": False,
            "candidate_tensor_modified_by_review": False,
            "trajectory_modified_by_review": False,
            "safety_or_camp_over_dp_claim_by_review": False,
            "closed_loop_outcomes_used_for_training": False,
            "closed_loop_outcomes_used_for_online_selector": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_execution_artifact_dir": str(artifact_dir),
            **{name: str(path) for name, path in paths.items()},
            "output_dir": str(output_dir.resolve()),
        },
        "source_hashes": {
            name: BASE_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **files}.items()
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": BASE_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
            "source_artifact_camp_origin_main": BASE_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
            "source_artifact_dp_head": BASE_MODULE._kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_execution_summary": _source_execution_summary(source_execution),
        "reviewed_activation_state": activation_state if passed else {},
        "reviewed_online_runtime_manifest": online_manifest if passed else {},
        "review_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_execution=source_execution),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    files: dict[str, Path],
    source_execution: dict[str, Any],
    activation_state: dict[str, Any],
    online_manifest: dict[str, Any],
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_execution.get("final_decision"))
    analysis = BASE_MODULE._dict(source_execution.get("analysis"))
    manifest_auth = BASE_MODULE._dict(online_manifest.get("authorizations"))
    checks = [
        BASE_MODULE._expect("result_review_enabled", enabled, True),
        BASE_MODULE._check("source_execution_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        BASE_MODULE._expect("source_execution_json_path_matches_artifact", paths["source_execution_json"], files["execution_json"]),
        BASE_MODULE._expect("source_execution_md_path_matches_artifact", paths["source_execution_md"], files["execution_md"]),
        BASE_MODULE._expect("source_activation_state_path_matches_artifact", paths["source_activation_state_json"], files["activation_state"]),
        BASE_MODULE._expect("source_online_runtime_manifest_path_matches_artifact", paths["source_online_runtime_manifest_json"], files["online_runtime_manifest"]),
        BASE_MODULE._expect("source_execution_sha256s_path_matches_artifact", paths["source_execution_sha256s"], files["execution_sha256s"]),
        BASE_MODULE._expect("audit_latest_status", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_EXECUTION_STATUS),
        BASE_MODULE._expect("audit_latest_next_work", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("status_doc_latest_status", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_EXECUTION_STATUS),
        BASE_MODULE._expect("status_doc_latest_next_work", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        BASE_MODULE._expect("source_artifact_dp_head_fixed", BASE_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        BASE_MODULE._expect("source_artifact_camp_head_matches_origin", BASE_MODULE._kv(heads, "CAMP_HEAD", "camp_head"), BASE_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main")),
        BASE_MODULE._expect("source_execution_run_exit", BASE_MODULE._read_text(files["run_exit"]).strip(), "0"),
        BASE_MODULE._expect("source_execution_schema", source_execution.get("schema_version"), SOURCE_EXECUTION_SCHEMA),
        BASE_MODULE._expect("source_execution_status", decision.get("status"), SOURCE_EXECUTION_STATUS),
        BASE_MODULE._expect("source_execution_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_execution_check_count", decision.get("check_count"), SOURCE_EXECUTION_CHECK_COUNT),
        BASE_MODULE._expect("source_execution_failed_check_count", decision.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_execution_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_execution_result_review_authorized", decision.get("objective_3200_candidate_index_actual_safetycost_online_selector_activation_result_review_authorized"), True),
        BASE_MODULE._expect("source_online_selector_activation_execution", decision.get("online_selector_activation_execution"), True),
        BASE_MODULE._expect("source_execution_dp_modification_false", decision.get("dp_modification"), False),
        BASE_MODULE._expect("source_execution_candidate_generation_false", decision.get("candidate_generation"), False),
        BASE_MODULE._expect("source_execution_training_execution_false", decision.get("training_execution"), False),
        BASE_MODULE._expect("source_execution_closed_loop_training_false", decision.get("closed_loop_outcomes_used_for_training"), False),
        BASE_MODULE._expect("source_execution_closed_loop_online_false", decision.get("closed_loop_outcomes_used_for_online_selector"), False),
        BASE_MODULE._expect("source_execution_source_static_review_passed", decision.get("source_static_review_passed"), True),
        BASE_MODULE._expect("source_analysis_online_activation_execution", analysis.get("online_selector_activation_execution"), True),
        BASE_MODULE._expect("source_analysis_selection_effect", analysis.get("selection_effect"), True),
        BASE_MODULE._expect("source_analysis_online_selector_change", analysis.get("online_selector_change"), True),
        BASE_MODULE._expect("source_analysis_deployment_execution_false", analysis.get("deployment_execution"), False),
        BASE_MODULE._expect("source_analysis_dp_modification_false", analysis.get("dp_modification"), False),
        BASE_MODULE._expect("source_analysis_closed_loop_training_false", analysis.get("closed_loop_outcomes_used_for_training"), False),
        BASE_MODULE._expect("source_analysis_closed_loop_online_false", analysis.get("closed_loop_outcomes_used_for_online_selector"), False),
        BASE_MODULE._expect("source_analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("activation_state_online_enabled", activation_state.get("online_selector_enabled"), True),
        BASE_MODULE._expect("activation_state_runtime_switch", activation_state.get("runtime_switch_state"), "online_enabled"),
        BASE_MODULE._expect("activation_state_source_scope", activation_state.get("source_scope"), SOURCE_SCOPE),
        BASE_MODULE._expect("activation_state_candidate_count", activation_state.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        BASE_MODULE._expect("activation_state_score_expression", activation_state.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("activation_state_dp_head", activation_state.get("required_dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("activation_state_fail_closed", activation_state.get("fail_closed_fallback_policy"), "dp_top1"),
        BASE_MODULE._expect("activation_state_executed_policy", activation_state.get("executed_output_policy"), EXECUTED_OUTPUT_POLICY),
        BASE_MODULE._expect("activation_state_dp_modification_false", activation_state.get("dp_modification_authorized"), False),
        BASE_MODULE._expect("activation_state_candidate_mutation_false", activation_state.get("candidate_tensor_mutation_authorized"), False),
        BASE_MODULE._expect("activation_state_trajectory_generation_false", activation_state.get("trajectory_generation_authorized"), False),
        BASE_MODULE._expect("activation_state_trajectory_rewrite_false", activation_state.get("trajectory_rewrite_authorized"), False),
        BASE_MODULE._expect("activation_state_reference_blend_false", activation_state.get("reference_blend_authorized"), False),
        BASE_MODULE._expect("activation_state_guidance_false", activation_state.get("guidance_authorized"), False),
        BASE_MODULE._expect("activation_state_postselection_false", activation_state.get("postselection_authorized"), False),
        BASE_MODULE._expect("activation_state_closed_loop_training_false", activation_state.get("closed_loop_outcomes_used_for_training"), False),
        BASE_MODULE._expect("activation_state_closed_loop_online_false", activation_state.get("closed_loop_outcomes_used_for_online_selector"), False),
        BASE_MODULE._expect("online_manifest_schema", online_manifest.get("schema_version"), EXECUTION_MODULE.ONLINE_RUNTIME_MANIFEST_SCHEMA_VERSION),
        BASE_MODULE._expect("online_manifest_source_scope", online_manifest.get("source_scope"), SOURCE_SCOPE),
        BASE_MODULE._expect("online_manifest_default_off_false", online_manifest.get("default_off"), False),
        BASE_MODULE._expect("online_manifest_fail_closed", online_manifest.get("fail_closed"), True),
        BASE_MODULE._expect("online_manifest_selection_effect", online_manifest.get("selection_effect"), True),
        BASE_MODULE._expect("online_manifest_online_selector_change", online_manifest.get("online_selector_change"), True),
        BASE_MODULE._expect("online_manifest_executed_policy", online_manifest.get("executed_output_policy"), EXECUTED_OUTPUT_POLICY),
        BASE_MODULE._expect("online_manifest_candidate_count", online_manifest.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        BASE_MODULE._expect("online_manifest_score_expression", online_manifest.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("online_manifest_dp_head", online_manifest.get("required_dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("online_manifest_dp_modification_false", manifest_auth.get("dp_modification_authorized"), False),
        BASE_MODULE._expect("online_manifest_candidate_generation_false", manifest_auth.get("candidate_generation_authorized"), False),
        BASE_MODULE._expect("online_manifest_training_false", manifest_auth.get("training_execution_authorized"), False),
        BASE_MODULE._expect("online_manifest_closed_loop_training_false", manifest_auth.get("closed_loop_outcomes_used_for_training"), False),
        BASE_MODULE._expect("online_manifest_closed_loop_online_false", manifest_auth.get("closed_loop_outcomes_used_for_online_selector"), False),
    ]
    for name, path in paths.items():
        checks.extend(BASE_MODULE._path_checks(name, path, allow_empty=False))
    for name, path in files.items():
        checks.extend(BASE_MODULE._path_checks(f"source_artifact_{name}", path, allow_empty=name == "stderr"))
    checks.extend(_sha_checks(root_sha256s=root_sha256s, nested_sha256s=nested_sha256s, files=files))
    return checks


def _sha_checks(
    *,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    files: dict[str, Path],
) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("root_heads_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "HEADS"), BASE_MODULE._sha256(files["heads"])),
        BASE_MODULE._expect("root_command_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "COMMAND"), BASE_MODULE._sha256(files["command"])),
        BASE_MODULE._expect("root_stdout_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "stdout"), BASE_MODULE._sha256(files["stdout"])),
        BASE_MODULE._expect("root_stderr_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "stderr"), BASE_MODULE._sha256(files["stderr"])),
        BASE_MODULE._expect("root_run_exit_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "run.exit"), BASE_MODULE._sha256(files["run_exit"])),
        BASE_MODULE._expect("root_execution_json_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"execution/{SOURCE_EXECUTION_JSON_NAME}"), BASE_MODULE._sha256(files["execution_json"])),
        BASE_MODULE._expect("root_execution_md_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"execution/{SOURCE_EXECUTION_MD_NAME}"), BASE_MODULE._sha256(files["execution_md"])),
        BASE_MODULE._expect("root_activation_state_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"execution/{SOURCE_ACTIVATION_STATE_JSON_NAME}"), BASE_MODULE._sha256(files["activation_state"])),
        BASE_MODULE._expect("root_online_manifest_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"execution/{SOURCE_ONLINE_RUNTIME_MANIFEST_JSON_NAME}"), BASE_MODULE._sha256(files["online_runtime_manifest"])),
        BASE_MODULE._expect("root_execution_sha256s_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "execution/SHA256SUMS"), BASE_MODULE._sha256(files["execution_sha256s"])),
        BASE_MODULE._expect("nested_execution_json_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_EXECUTION_JSON_NAME), BASE_MODULE._sha256(files["execution_json"])),
        BASE_MODULE._expect("nested_execution_md_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_EXECUTION_MD_NAME), BASE_MODULE._sha256(files["execution_md"])),
        BASE_MODULE._expect("nested_activation_state_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_ACTIVATION_STATE_JSON_NAME), BASE_MODULE._sha256(files["activation_state"])),
        BASE_MODULE._expect("nested_online_manifest_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_ONLINE_RUNTIME_MANIFEST_JSON_NAME), BASE_MODULE._sha256(files["online_runtime_manifest"])),
    ]


def _artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "execution_json": artifact_dir / "execution" / SOURCE_EXECUTION_JSON_NAME,
        "execution_md": artifact_dir / "execution" / SOURCE_EXECUTION_MD_NAME,
        "activation_state": artifact_dir / "execution" / SOURCE_ACTIVATION_STATE_JSON_NAME,
        "online_runtime_manifest": artifact_dir / "execution" / SOURCE_ONLINE_RUNTIME_MANIFEST_JSON_NAME,
        "execution_sha256s": artifact_dir / "execution" / "SHA256SUMS",
    }


def _source_execution_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_execution.get("final_decision"))
    analysis = BASE_MODULE._dict(source_execution.get("analysis"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "check_count": decision.get("check_count"),
        "failed_check_count": decision.get("failed_check_count"),
        "online_selector_activation_execution": decision.get("online_selector_activation_execution"),
        "online_selector_change_authorized": decision.get("online_selector_change_authorized"),
        "selection_effect": analysis.get("selection_effect"),
        "executed_output_policy": EXECUTED_OUTPUT_POLICY,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_execution: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    source_decision = BASE_MODULE._dict(source_execution.get("final_decision"))
    if passed:
        failure_class = None
    elif "result_review_enabled" in failed:
        failure_class = "explicit_online_selector_activation_execution_result_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif any("sha" in name for name in failed):
        failure_class = "source_artifact_hash_mismatch"
    elif any(name.startswith("activation_state_") or name.startswith("online_manifest_") for name in failed):
        failure_class = "online_selector_activation_runtime_contract_failure"
    elif any(name.startswith("source_execution") or name.startswith("source_analysis") for name in failed):
        failure_class = "source_online_selector_activation_execution_contract_failure"
    else:
        failure_class = "online_selector_activation_execution_result_review_contract_failure"
    return {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_result_review_passed": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_online_selector_activation_integration_closeout_record_authorized": bool(passed),
        "online_selector_activation_execution_reviewed_by_this_gate": True,
        "online_selector_activation_execution_executed_by_review": False,
        "source_online_selector_activation_execution_passed": source_decision.get("passed"),
        "source_online_selector_activation_execution": source_decision.get("online_selector_activation_execution"),
        "source_online_selector_change_authorized": source_decision.get("online_selector_change_authorized"),
        "executed_output_policy": EXECUTED_OUTPUT_POLICY,
        "fail_closed_fallback_policy": "dp_top1",
        "dp_modification": False,
        "candidate_generation": False,
        "training_execution": False,
        "closed_loop_outcomes_used_for_training": False,
        "closed_loop_outcomes_used_for_online_selector": False,
        "safety_benefit_claim_made_by_review": False,
        "camp_over_dp_top1_claim_made_by_review": False,
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(BASE_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{BASE_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_execution_summary"]
    failed = decision["failed_checks"] or ["none"]
    return "\n".join(
        [
            "# Objective-3200 Online Selector Activation Execution Result Review",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Failed checks: `{', '.join(failed)}`",
            "",
            "## Reviewed Evidence",
            "",
            f"- Source execution passed: `{summary['passed']}`",
            f"- Source execution checks: `{summary['check_count']} / {summary['failed_check_count']}`",
            f"- Online selector activation execution: `{summary['online_selector_activation_execution']}`",
            f"- Selection effect: `{summary['selection_effect']}`",
            f"- Executed output policy: `{summary['executed_output_policy']}`",
            "",
            "## Boundary",
            "",
            "- Review only: no activation execution, deployment, training, candidate generation, DP modification, trajectory mutation, or claim.",
            "- The reviewed runtime manifest selects only fixed DP candidate indices and keeps fail-closed fallback to DP Top-1.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
