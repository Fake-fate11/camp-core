#!/usr/bin/env python3
"""Record auditable integration closeout for objective-3200 online selector activation."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_result_review_module():
    script_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_online_selector_activation_execution_result.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_online_selector_activation_execution_result_review",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RESULT_REVIEW_MODULE = _load_result_review_module()
BASE_MODULE = RESULT_REVIEW_MODULE.BASE_MODULE

FIXED_DP_HEAD = RESULT_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = RESULT_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = RESULT_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = RESULT_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = RESULT_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = RESULT_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_REVIEW_CHECK_COUNT = 120
AUTHORIZED_CURRENT_WORK = RESULT_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
EXECUTED_OUTPUT_POLICY = RESULT_REVIEW_MODULE.EXECUTED_OUTPUT_POLICY
SOURCE_SCOPE = RESULT_REVIEW_MODULE.SOURCE_SCOPE

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_online_selector_activation_"
    "integration_closeout_record_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_integration_"
    "closeout_recorded"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_integration_"
    "closeout_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "no_further_action_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_online_selector_activation_"
    "auditable_integration_complete"
)
RECORD_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_"
    "actual_safetycost_online_selector_activation_integration_closeout_record.json"
)
RECORD_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_"
    "actual_safetycost_online_selector_activation_integration_closeout_record.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_md", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation_integration_closeout_record",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_md=args.source_result_review_md,
        source_result_review_sha256s=args.source_result_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation_integration_closeout_record
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_result_review_artifact_dir.resolve()
    paths = {
        "source_result_review_json": source_result_review_json.resolve(),
        "source_result_review_md": source_result_review_md.resolve(),
        "source_result_review_sha256s": source_result_review_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    files = _artifact_files(artifact_dir)
    source_review = BASE_MODULE._read_json_dict(paths["source_result_review_json"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(files["heads"]))
    root_sha256s = BASE_MODULE._read_sha256sums(files["root_sha256s"])
    nested_sha256s = BASE_MODULE._read_sha256sums(paths["source_result_review_sha256s"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        files=files,
        source_review=source_review,
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
            "integration_closeout_record_only": True,
            "auditable_integration_complete": bool(passed),
            "result_review_executed_by_closeout": False,
            "online_selector_activation_execution_executed_by_closeout": False,
            "deployment_executed_by_closeout": False,
            "training_executed_by_closeout": False,
            "candidate_generation_executed_by_closeout": False,
            "dp_modified_by_closeout": False,
            "candidate_tensor_modified_by_closeout": False,
            "trajectory_modified_by_closeout": False,
            "safety_or_camp_over_dp_claim_by_closeout": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_result_review_artifact_dir": str(artifact_dir),
            **{name: str(path) for name, path in paths.items()},
            "output_dir": str(output_dir.resolve()),
        },
        "source_hashes": {
            name: BASE_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **files}.items()
        },
        "source_result_review_summary": _source_result_review_summary(source_review),
        "integration_closeout_summary": _integration_closeout_summary(source_review, passed=passed),
        "closeout_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_review=source_review),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    files: dict[str, Path],
    source_review: dict[str, Any],
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
    decision = BASE_MODULE._dict(source_review.get("final_decision"))
    analysis = BASE_MODULE._dict(source_review.get("analysis"))
    activation_state = BASE_MODULE._dict(source_review.get("reviewed_activation_state"))
    online_manifest = BASE_MODULE._dict(source_review.get("reviewed_online_runtime_manifest"))
    checks = [
        BASE_MODULE._expect("closeout_record_enabled", enabled, True),
        BASE_MODULE._check("source_result_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        BASE_MODULE._expect("source_result_review_json_path_matches_artifact", paths["source_result_review_json"], files["review_json"]),
        BASE_MODULE._expect("source_result_review_md_path_matches_artifact", paths["source_result_review_md"], files["review_md"]),
        BASE_MODULE._expect("source_result_review_sha256s_path_matches_artifact", paths["source_result_review_sha256s"], files["review_sha256s"]),
        BASE_MODULE._expect("audit_latest_status", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("audit_latest_next_work", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("status_doc_latest_status", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("status_doc_latest_next_work", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        BASE_MODULE._expect("source_artifact_dp_head_fixed", BASE_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        BASE_MODULE._expect("source_result_review_run_exit", BASE_MODULE._read_text(files["run_exit"]).strip(), "0"),
        BASE_MODULE._expect("source_result_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        BASE_MODULE._expect("source_result_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("source_result_review_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_result_review_check_count", decision.get("check_count"), SOURCE_REVIEW_CHECK_COUNT),
        BASE_MODULE._expect("source_result_review_failed_check_count", decision.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_result_review_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_closeout_authorized", decision.get("objective_3200_candidate_index_actual_safetycost_online_selector_activation_integration_closeout_record_authorized"), True),
        BASE_MODULE._expect("source_activation_reviewed", decision.get("online_selector_activation_execution_reviewed_by_this_gate"), True),
        BASE_MODULE._expect("source_activation_not_executed_by_review", decision.get("online_selector_activation_execution_executed_by_review"), False),
        BASE_MODULE._expect("source_activation_execution_passed", decision.get("source_online_selector_activation_execution_passed"), True),
        BASE_MODULE._expect("source_activation_execution_true", decision.get("source_online_selector_activation_execution"), True),
        BASE_MODULE._expect("source_executed_output_policy", decision.get("executed_output_policy"), EXECUTED_OUTPUT_POLICY),
        BASE_MODULE._expect("source_fail_closed_fallback_policy", decision.get("fail_closed_fallback_policy"), "dp_top1"),
        BASE_MODULE._expect("source_dp_modification_false", decision.get("dp_modification"), False),
        BASE_MODULE._expect("source_candidate_generation_false", decision.get("candidate_generation"), False),
        BASE_MODULE._expect("source_training_execution_false", decision.get("training_execution"), False),
        BASE_MODULE._expect("source_closed_loop_training_false", decision.get("closed_loop_outcomes_used_for_training"), False),
        BASE_MODULE._expect("source_closed_loop_online_false", decision.get("closed_loop_outcomes_used_for_online_selector"), False),
        BASE_MODULE._expect("source_safety_claim_false", decision.get("safety_benefit_claim_made_by_review"), False),
        BASE_MODULE._expect("source_camp_claim_false", decision.get("camp_over_dp_top1_claim_made_by_review"), False),
        BASE_MODULE._expect("source_analysis_result_review_only", analysis.get("result_review_only"), True),
        BASE_MODULE._expect("source_analysis_activation_not_executed_by_review", analysis.get("online_selector_activation_execution_executed_by_review"), False),
        BASE_MODULE._expect("source_analysis_deployment_false", analysis.get("deployment_executed_by_review"), False),
        BASE_MODULE._expect("source_analysis_dp_modified_false", analysis.get("dp_modified_by_review"), False),
        BASE_MODULE._expect("source_analysis_claim_false", analysis.get("safety_or_camp_over_dp_claim_by_review"), False),
        BASE_MODULE._expect("source_analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("activation_state_online_enabled", activation_state.get("online_selector_enabled"), True),
        BASE_MODULE._expect("activation_state_source_scope", activation_state.get("source_scope"), SOURCE_SCOPE),
        BASE_MODULE._expect("activation_state_executed_policy", activation_state.get("executed_output_policy"), EXECUTED_OUTPUT_POLICY),
        BASE_MODULE._expect("activation_state_fail_closed", activation_state.get("fail_closed_fallback_policy"), "dp_top1"),
        BASE_MODULE._expect("activation_state_dp_head", activation_state.get("required_dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("activation_state_dp_modification_false", activation_state.get("dp_modification_authorized"), False),
        BASE_MODULE._expect("activation_state_candidate_mutation_false", activation_state.get("candidate_tensor_mutation_authorized"), False),
        BASE_MODULE._expect("activation_state_closed_loop_online_false", activation_state.get("closed_loop_outcomes_used_for_online_selector"), False),
        BASE_MODULE._expect("online_manifest_source_scope", online_manifest.get("source_scope"), SOURCE_SCOPE),
        BASE_MODULE._expect("online_manifest_default_off_false", online_manifest.get("default_off"), False),
        BASE_MODULE._expect("online_manifest_selection_effect", online_manifest.get("selection_effect"), True),
        BASE_MODULE._expect("online_manifest_online_selector_change", online_manifest.get("online_selector_change"), True),
        BASE_MODULE._expect("online_manifest_executed_policy", online_manifest.get("executed_output_policy"), EXECUTED_OUTPUT_POLICY),
        BASE_MODULE._expect("online_manifest_dp_head", online_manifest.get("required_dp_head"), FIXED_DP_HEAD),
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
        BASE_MODULE._expect("root_review_json_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"review/{SOURCE_REVIEW_JSON_NAME}"), BASE_MODULE._sha256(files["review_json"])),
        BASE_MODULE._expect("root_review_md_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"review/{SOURCE_REVIEW_MD_NAME}"), BASE_MODULE._sha256(files["review_md"])),
        BASE_MODULE._expect("root_review_sha256s_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "review/SHA256SUMS"), BASE_MODULE._sha256(files["review_sha256s"])),
        BASE_MODULE._expect("nested_review_json_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_REVIEW_JSON_NAME), BASE_MODULE._sha256(files["review_json"])),
        BASE_MODULE._expect("nested_review_md_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_REVIEW_MD_NAME), BASE_MODULE._sha256(files["review_md"])),
    ]


def _artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "review_json": artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": artifact_dir / "review" / "SHA256SUMS",
    }


def _source_result_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_review.get("final_decision"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "check_count": decision.get("check_count"),
        "failed_check_count": decision.get("failed_check_count"),
        "source_online_selector_activation_execution": decision.get("source_online_selector_activation_execution"),
        "executed_output_policy": decision.get("executed_output_policy"),
        "fail_closed_fallback_policy": decision.get("fail_closed_fallback_policy"),
    }


def _integration_closeout_summary(source_review: dict[str, Any], *, passed: bool) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_review.get("final_decision"))
    return {
        "auditable_integration_complete": bool(passed),
        "integration_scope": "CAMP selector over fixed Diffusion Planner candidate tensor",
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_scope": SOURCE_SCOPE,
        "executed_output_policy": decision.get("executed_output_policy"),
        "fail_closed_fallback_policy": decision.get("fail_closed_fallback_policy"),
        "safety_benefit_claim_made_by_closeout": False,
        "camp_over_dp_top1_claim_made_by_closeout": False,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_review: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    source_decision = BASE_MODULE._dict(source_review.get("final_decision"))
    if passed:
        failure_class = None
    elif "closeout_record_enabled" in failed:
        failure_class = "explicit_online_selector_activation_integration_closeout_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif any("sha" in name for name in failed):
        failure_class = "source_artifact_hash_mismatch"
    elif any(name.startswith(("activation_state_", "online_manifest_")) for name in failed):
        failure_class = "online_selector_activation_runtime_contract_failure"
    elif any(name.startswith("source_") for name in failed):
        failure_class = "source_online_selector_activation_result_review_contract_failure"
    else:
        failure_class = "online_selector_activation_integration_closeout_contract_failure"
    return {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_online_selector_activation_integration_closeout_recorded": bool(passed),
        "auditable_integration_complete": bool(passed),
        "no_further_action_recommended": bool(passed),
        "source_result_review_passed": source_decision.get("passed"),
        "source_online_selector_activation_execution": source_decision.get("source_online_selector_activation_execution"),
        "executed_output_policy": source_decision.get("executed_output_policy"),
        "fail_closed_fallback_policy": source_decision.get("fail_closed_fallback_policy"),
        "integration_scope": "CAMP selector over fixed Diffusion Planner candidate tensor",
        "dp_modification": False,
        "candidate_generation": False,
        "candidate_tensor_modification": False,
        "trajectory_modification": False,
        "training_execution": False,
        "closed_loop_outcomes_used_for_training": False,
        "closed_loop_outcomes_used_for_online_selector": False,
        "safety_benefit_claim_made_by_closeout": False,
        "camp_over_dp_top1_claim_made_by_closeout": False,
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / RECORD_JSON_NAME
    md_path = output_dir / RECORD_MD_NAME
    json_path.write_text(json.dumps(BASE_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{BASE_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["integration_closeout_summary"]
    failed = decision["failed_checks"] or ["none"]
    return "\n".join(
        [
            "# Objective-3200 Online Selector Activation Integration Closeout",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Failed checks: `{', '.join(failed)}`",
            f"- Auditable integration complete: `{summary['auditable_integration_complete']}`",
            f"- Integration scope: `{summary['integration_scope']}`",
            f"- Executed output policy: `{summary['executed_output_policy']}`",
            f"- Fail-closed fallback policy: `{summary['fail_closed_fallback_policy']}`",
            "",
            "This record closes the fixed-DP integration evidence chain for CAMP as a selector over fixed DP candidates.",
            "It does not modify Diffusion Planner, mutate candidates or trajectories, run training, or make a new safety/CAMP-over-DP claim.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
