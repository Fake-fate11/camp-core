#!/usr/bin/env python3
"""Preflight a future strict paired-evaluation execution gate.

This read-only gate consumes the audited paired-evaluation execution-plan
static review plus existing non-claim evidence summaries. It locks the evidence
inputs required for a future CAMP shadow-selected candidate vs DP Top-1 paired
evaluation, but it does not execute paired evaluation, replay, training,
candidate generation, promotion, deployment, online selector activation,
Diffusion Planner modification, or any safety/CAMP-over-DP claim.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_paired_evaluation_execution_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
BASE_MODULE = SOURCE_REVIEW_MODULE.BASE_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_evidence_acquisition_paired_evaluation_execution_preflight_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_only"
)

SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
PREFLIGHT_JSON_NAME = "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight.json"
PREFLIGHT_MD_NAME = "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight.md"

RUNTIME_RESULT_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_result_review_passed"
)
DELTA_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_passed"
)
READINESS_RESULT_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_passed"
)

EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 150
EXPECTED_SOURCE_PLAN_CHECK_COUNT = SOURCE_REVIEW_MODULE.EXPECTED_PLAN_CHECK_COUNT
EXPECTED_SOURCE_REQUIRED_INPUT_COUNT = SOURCE_REVIEW_MODULE.EXPECTED_REQUIRED_INPUT_COUNT
EXPECTED_SOURCE_EXECUTION_PLAN_COUNT = SOURCE_REVIEW_MODULE.EXPECTED_EXECUTION_PLAN_COUNT
EXPECTED_SOURCE_PLANNED_OUTPUT_COUNT = SOURCE_REVIEW_MODULE.EXPECTED_PLANNED_OUTPUT_COUNT
EXPECTED_SOURCE_NO_GO_COUNT = SOURCE_REVIEW_MODULE.EXPECTED_NO_GO_COUNT
EXPECTED_RECORD_COUNT = 3200
EXPECTED_SELECTION_LOG_COUNT = 32
EXPECTED_SHADOW_DIFF_RECORDS = 2832
EXPECTED_NO_GO = SOURCE_REVIEW_MODULE.PLAN_MODULE.SOURCE_REVIEW_MODULE.EXPECTED_NO_GO

EXPECTED_EVIDENCE_LOCKS = (
    "passed_execution_plan_static_review_artifact",
    "source_execution_plan_artifact",
    "runtime_result_review_json",
    "shadow_vs_top1_delta_review_json",
    "readiness_result_review_json",
    "safetycost_v1_contract",
    "v14_eof_contract",
    "artifact_hash_and_heads_contract",
)
EXPECTED_REQUIRED_INPUT_MANIFESTS = (
    "fixed_dp_candidate_tensor_manifest",
    "camp_shadow_selection_log_manifest",
    "dp_top1_candidate_index_manifest",
    "strict_paired_run_key_manifest",
    "safetycost_v1_hard_gate_config",
    "coverage_uncertainty_bucket_manifest",
    "no_go_condition_manifest",
    "source_artifact_sha256_manifest",
)
EXPECTED_PREFLIGHT_ITEMS = (
    "lock_source_static_review_and_plan_artifacts",
    "lock_runtime_result_review_candidate_tensor_evidence",
    "lock_shadow_vs_top1_delta_review_as_nonclaim_support",
    "lock_readiness_result_review_no_promotion_boundary",
    "verify_fixed_dp_affine_simplex_and_convex_master_boundary",
    "verify_no_formal_seed_full36_closed_loop_or_postprocessing_scope",
    "predeclare_paired_execution_inputs_and_outputs",
    "emit_static_review_ready_execution_preflight_artifact",
)
EXPECTED_FUTURE_OUTPUTS = (
    "paired_run_key_index",
    "candidate_tensor_identity_table",
    "shadow_vs_top1_metric_delta_table",
    "safetycost_v1_confidence_interval_table",
    "coverage_uncertainty_bucket_table",
    "paired_execution_no_go_report",
)
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_REVIEW_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = SOURCE_REVIEW_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution_plan_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--execution_plan_static_review_json", type=Path, required=True)
    parser.add_argument("--execution_plan_static_review_md", type=Path, required=True)
    parser.add_argument("--execution_plan_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--runtime_result_review_json", type=Path, required=True)
    parser.add_argument("--shadow_delta_review_json", type=Path, required=True)
    parser.add_argument("--readiness_result_review_json", type=Path, required=True)
    parser.add_argument("--safety_score_doc", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight",
        action="store_true",
        help="Explicit opt-in for read-only paired-evaluation execution preflight.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        execution_plan_static_review_artifact_dir=args.execution_plan_static_review_artifact_dir,
        execution_plan_static_review_json=args.execution_plan_static_review_json,
        execution_plan_static_review_md=args.execution_plan_static_review_md,
        execution_plan_static_review_sha256s=args.execution_plan_static_review_sha256s,
        runtime_result_review_json=args.runtime_result_review_json,
        shadow_delta_review_json=args.shadow_delta_review_json,
        readiness_result_review_json=args.readiness_result_review_json,
        safety_score_doc=args.safety_score_doc,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    execution_plan_static_review_artifact_dir: Path,
    execution_plan_static_review_json: Path,
    execution_plan_static_review_md: Path,
    execution_plan_static_review_sha256s: Path,
    runtime_result_review_json: Path,
    shadow_delta_review_json: Path,
    readiness_result_review_json: Path,
    safety_score_doc: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = execution_plan_static_review_artifact_dir.resolve()
    paths = {
        "execution_plan_static_review_json": execution_plan_static_review_json.resolve(),
        "execution_plan_static_review_md": execution_plan_static_review_md.resolve(),
        "execution_plan_static_review_sha256s": execution_plan_static_review_sha256s.resolve(),
        "runtime_result_review_json": runtime_result_review_json.resolve(),
        "shadow_delta_review_json": shadow_delta_review_json.resolve(),
        "readiness_result_review_json": readiness_result_review_json.resolve(),
        "safety_score_doc": safety_score_doc.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    artifact_files = {
        "command": artifact_dir / "COMMAND",
        "heads": artifact_dir / "HEADS",
        "stdout": artifact_dir / "stdout.txt",
        "stderr": artifact_dir / "stderr.txt",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "review_json": artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": artifact_dir / "review" / "SHA256SUMS",
    }
    source_review = BASE_MODULE._read_json_dict(paths["execution_plan_static_review_json"])
    runtime_result_review = BASE_MODULE._read_json_dict(paths["runtime_result_review_json"])
    delta_review = BASE_MODULE._read_json_dict(paths["shadow_delta_review_json"])
    readiness_result_review = BASE_MODULE._read_json_dict(paths["readiness_result_review_json"])
    root_sha256s = BASE_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    review_sha256s = BASE_MODULE._read_sha256sums(paths["execution_plan_static_review_sha256s"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(artifact_files["heads"]))
    safety_score_text = BASE_MODULE._read_text(paths["safety_score_doc"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        BASE_MODULE._expect("execution_preflight_enabled", enabled, True),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        BASE_MODULE._check("current_camp_head_is_sha", BASE_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        BASE_MODULE._check("execution_plan_static_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(BASE_MODULE._path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(
            BASE_MODULE._path_checks(
                f"artifact_{name}",
                path,
                require_file=True,
                allow_empty=(name == "stderr"),
            )
        )
    checks.extend(
        [
            BASE_MODULE._expect("review_json_matches_artifact_layout", paths["execution_plan_static_review_json"], artifact_files["review_json"]),
            BASE_MODULE._expect("review_md_matches_artifact_layout", paths["execution_plan_static_review_md"], artifact_files["review_md"]),
            BASE_MODULE._expect("review_sha256s_matches_artifact_layout", paths["execution_plan_static_review_sha256s"], artifact_files["review_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, review_sha256s))
    checks.extend(_heads_checks(heads, source_review))
    checks.extend(_source_review_contract_checks(source_review))
    checks.extend(_runtime_result_review_checks(runtime_result_review))
    checks.extend(_delta_review_checks(delta_review, runtime_result_review))
    checks.extend(_readiness_result_review_checks(readiness_result_review))
    checks.extend(_safety_score_doc_checks(safety_score_text))
    checks.extend(_audit_checks(v14_text, status_text))

    evidence_locks = _evidence_locks(
        label=label,
        source_review=source_review,
        runtime_result_review=runtime_result_review,
        delta_review=delta_review,
        readiness_result_review=readiness_result_review,
    )
    required_input_manifests = _required_input_manifests(runtime_result_review, delta_review)
    preflight_plan = _preflight_plan()
    future_outputs = _future_outputs()
    no_go = _no_go_register()
    checks.extend(
        _preflight_contract_checks(
            evidence_locks,
            required_input_manifests,
            preflight_plan,
            future_outputs,
            no_go,
        )
    )

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "preflight_only": True,
            "read_only": True,
            "paired_evaluation_execution": False,
            "source_execution_plan_static_review_artifact_dir": str(artifact_dir),
            "source_execution_plan_static_review_json": str(paths["execution_plan_static_review_json"]),
            "runtime_result_review_json": str(paths["runtime_result_review_json"]),
            "shadow_delta_review_json": str(paths["shadow_delta_review_json"]),
            "readiness_result_review_json": str(paths["readiness_result_review_json"]),
            "safety_score_doc": str(paths["safety_score_doc"]),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "source_hashes": {
            name: BASE_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_static_review_summary": _source_static_review_summary(source_review),
        "runtime_result_summary": _runtime_result_summary(runtime_result_review),
        "delta_review_summary": _delta_review_summary(delta_review),
        "readiness_result_summary": _readiness_result_summary(readiness_result_review),
        "evidence_locks": evidence_locks,
        "required_input_manifests": required_input_manifests,
        "preflight_plan": preflight_plan,
        "future_outputs": future_outputs,
        "no_go_register": no_go,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "preflight_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    BASE_MODULE._write_json(output_dir / PREFLIGHT_JSON_NAME, report)
    (output_dir / PREFLIGHT_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    BASE_MODULE._write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion Evidence Acquisition Paired Evaluation Execution Preflight",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Evidence Locks",
    ]
    for item in report["evidence_locks"]:
        lines.append(f"- `{item['name']}`: `{item['requirement']}`")
    lines.extend(["", "## Required Input Manifests"])
    for item in report["required_input_manifests"]:
        lines.append(f"- `{item['name']}`: `{item['requirement']}`")
    lines.extend(["", "## Checks"])
    for check in report["preflight_checks"]:
        lines.append(
            f"- [{'x' if check['passed'] else ' '}] {check['name']}: "
            f"observed=`{BASE_MODULE._compact(check['observed'])}` expected=`{BASE_MODULE._compact(check['expected'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        BASE_MODULE._sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        BASE_MODULE._sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        BASE_MODULE._sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        BASE_MODULE._sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        BASE_MODULE._sha256sums_expect("artifact_review_json_root_sha", artifact_files["review_json"], root_sha256s, (f"review/{SOURCE_REVIEW_JSON_NAME}", f"./review/{SOURCE_REVIEW_JSON_NAME}", SOURCE_REVIEW_JSON_NAME)),
        BASE_MODULE._sha256sums_expect("artifact_review_md_root_sha", artifact_files["review_md"], root_sha256s, (f"review/{SOURCE_REVIEW_MD_NAME}", f"./review/{SOURCE_REVIEW_MD_NAME}", SOURCE_REVIEW_MD_NAME)),
        BASE_MODULE._sha256sums_expect("artifact_review_sha256s_root_sha", artifact_files["review_sha256s"], root_sha256s, ("review/SHA256SUMS", "./review/SHA256SUMS", "SHA256SUMS")),
        BASE_MODULE._sha256sums_expect("source_review_json_nested_sha", artifact_files["review_json"], review_sha256s, (SOURCE_REVIEW_JSON_NAME, f"./{SOURCE_REVIEW_JSON_NAME}")),
        BASE_MODULE._sha256sums_expect("source_review_md_nested_sha", artifact_files["review_md"], review_sha256s, (SOURCE_REVIEW_MD_NAME, f"./{SOURCE_REVIEW_MD_NAME}")),
        BASE_MODULE._expect("artifact_run_exit_zero", BASE_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_review: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = BASE_MODULE._dict(source_review.get("analysis"))
    return [
        BASE_MODULE._expect("artifact_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("artifact_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        BASE_MODULE._expect("artifact_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        BASE_MODULE._expect("artifact_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_review_contract_checks(source_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_review.get("final_decision"))
    analysis = BASE_MODULE._dict(source_review.get("analysis"))
    source_plan = BASE_MODULE._dict(source_review.get("source_plan_summary"))
    contract = BASE_MODULE._dict(source_review.get("contract_summary"))
    checks = [
        BASE_MODULE._expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        BASE_MODULE._expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("source_review_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_review_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_review_static_review_passed", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_static_review_passed"), True),
        BASE_MODULE._expect("source_review_execution_preflight_authorized", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_authorized"), True),
        BASE_MODULE._expect("source_review_no_paired_execution", decision.get("paired_evaluation_executed_by_this_gate"), False),
        BASE_MODULE._expect("source_review_check_count", len(BASE_MODULE._list(source_review.get("review_checks"))), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        BASE_MODULE._expect("source_review_failed_check_count", len(BASE_MODULE._list(decision.get("failed_checks"))), 0),
        BASE_MODULE._expect("source_plan_status", source_plan.get("status"), SOURCE_REVIEW_MODULE.SOURCE_PLAN_STATUS),
        BASE_MODULE._expect("source_plan_check_count", source_plan.get("plan_check_count"), EXPECTED_SOURCE_PLAN_CHECK_COUNT),
        BASE_MODULE._expect("source_plan_failed_count", source_plan.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_plan_no_paired_execution", source_plan.get("paired_evaluation_executed_by_this_gate"), False),
        BASE_MODULE._expect("source_required_input_count", contract.get("required_input_count"), EXPECTED_SOURCE_REQUIRED_INPUT_COUNT),
        BASE_MODULE._expect("source_execution_plan_count", contract.get("execution_plan_count"), EXPECTED_SOURCE_EXECUTION_PLAN_COUNT),
        BASE_MODULE._expect("source_planned_output_count", contract.get("planned_output_count"), EXPECTED_SOURCE_PLANNED_OUTPUT_COUNT),
        BASE_MODULE._expect("source_no_go_count", contract.get("no_go_count"), EXPECTED_SOURCE_NO_GO_COUNT),
        BASE_MODULE._expect("source_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("source_analysis_no_paired_execution", analysis.get("paired_evaluation_execution"), False),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(BASE_MODULE._expect(f"source_review_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(BASE_MODULE._expect(f"source_review_decision_{flag}", decision.get(flag), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(BASE_MODULE._expect(f"source_review_analysis_{flag}", analysis.get(flag), False))
    return checks


def _runtime_result_review_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(report.get("final_decision"))
    analysis = BASE_MODULE._dict(report.get("analysis"))
    heads = BASE_MODULE._dict(report.get("heads"))
    records = BASE_MODULE._dict(report.get("records"))
    execution = BASE_MODULE._dict(report.get("execution"))
    return [
        BASE_MODULE._expect("runtime_result_review_status", decision.get("status"), RUNTIME_RESULT_REVIEW_STATUS),
        BASE_MODULE._expect("runtime_result_review_passed", decision.get("passed"), True),
        BASE_MODULE._expect("runtime_result_review_dp_fixed", heads.get("current_dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("runtime_result_review_artifact_dp_fixed", heads.get("artifact_dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("runtime_result_review_executed_output_policy", decision.get("executed_output_policy"), "dp_top1"),
        BASE_MODULE._expect("runtime_result_review_candidate_operation", decision.get("candidate_operation"), "fixed DP candidate reranking only"),
        BASE_MODULE._expect("runtime_result_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("runtime_result_review_record_count", records.get("record_count"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("runtime_result_review_selection_log_count", execution.get("selection_log_count"), EXPECTED_SELECTION_LOG_COUNT),
        BASE_MODULE._expect("runtime_result_review_executed_top1_records", records.get("executed_top1_records"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("runtime_result_review_default_off_records", records.get("default_off_selector_records"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("runtime_result_review_artifact_contract_records", records.get("artifact_contract_ready_records"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("runtime_result_review_shadow_diff_records", records.get("shadow_selected_index_differs_from_executed_index_records"), EXPECTED_SHADOW_DIFF_RECORDS),
        BASE_MODULE._expect("runtime_result_review_selection_effect_count", BASE_MODULE._dict(records.get("violation_counts")).get("selection_effect_true_count"), 0),
        BASE_MODULE._expect("runtime_result_review_formal_seed_path_count", execution.get("formal_seed_path_count"), 0),
        BASE_MODULE._expect("runtime_result_review_analysis_read_only", analysis.get("result_review_only"), True),
        BASE_MODULE._expect("runtime_result_review_analysis_no_training", analysis.get("training_executed_by_review"), False),
        BASE_MODULE._expect("runtime_result_review_analysis_no_replay_by_review", analysis.get("replay_executed_by_review"), False),
        BASE_MODULE._expect("runtime_result_review_analysis_no_generation_by_review", analysis.get("candidate_generation_executed_by_review"), False),
        BASE_MODULE._expect("runtime_result_review_selector_promotion_false", decision.get("selector_promotion_authorized"), False),
        BASE_MODULE._expect("runtime_result_review_deployment_false", decision.get("deployment_authorized"), False),
        BASE_MODULE._expect("runtime_result_review_safety_claim_false", decision.get("safety_benefit_claim_authorized"), False),
        BASE_MODULE._expect("runtime_result_review_camp_claim_false", decision.get("camp_over_dp_top1_claim_authorized"), False),
    ]


def _delta_review_checks(delta: dict[str, Any], runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(delta.get("final_decision"))
    analysis = BASE_MODULE._dict(delta.get("analysis"))
    records = BASE_MODULE._dict(delta.get("records"))
    source = BASE_MODULE._dict(delta.get("source_result_review"))
    runtime_records = BASE_MODULE._dict(runtime_result.get("records"))
    return [
        BASE_MODULE._expect("delta_review_status", decision.get("status"), DELTA_REVIEW_STATUS),
        BASE_MODULE._expect("delta_review_passed", decision.get("passed"), True),
        BASE_MODULE._expect("delta_review_static_objective_supported", decision.get("static_objective_delta_supported"), True),
        BASE_MODULE._expect("delta_review_record_count", records.get("record_count"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("delta_review_source_record_count", source.get("record_count"), runtime_records.get("record_count")),
        BASE_MODULE._expect("delta_review_source_selection_log_count", source.get("selection_log_count"), EXPECTED_SELECTION_LOG_COUNT),
        BASE_MODULE._expect("delta_review_shadow_diff_records", records.get("shadow_selected_index_differs_from_executed_index_records"), EXPECTED_SHADOW_DIFF_RECORDS),
        BASE_MODULE._expect("delta_review_formal_seed_path_count", records.get("formal_seed_path_count"), 0),
        BASE_MODULE._expect("delta_review_candidate_operation_records", records.get("candidate_operation_records"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("delta_review_score_expression_records", records.get("score_expression_records"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("delta_review_claim_scope", analysis.get("claim_scope"), "Supports static objective delta only; does not prove safety, closed-loop outcome, deployability, or CAMP superiority over DP Top-1."),
        BASE_MODULE._expect("delta_review_replay_authorized_false", decision.get("replay_execution_authorized"), False),
        BASE_MODULE._expect("delta_review_selector_promotion_false", decision.get("selector_promotion_authorized"), False),
        BASE_MODULE._expect("delta_review_deployment_false", decision.get("deployment_authorized"), False),
        BASE_MODULE._expect("delta_review_safety_claim_false", decision.get("safety_benefit_claim_authorized"), False),
        BASE_MODULE._expect("delta_review_camp_claim_false", decision.get("camp_over_dp_top1_claim_authorized"), False),
    ]


def _readiness_result_review_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(report.get("final_decision"))
    source_execution = BASE_MODULE._dict(report.get("source_execution_summary"))
    source_static = BASE_MODULE._dict(report.get("source_static_review_summary"))
    return [
        BASE_MODULE._expect("readiness_result_review_status", decision.get("status"), READINESS_RESULT_REVIEW_STATUS),
        BASE_MODULE._expect("readiness_result_review_passed", decision.get("passed"), True),
        BASE_MODULE._expect("readiness_result_review_direct_promotion_false", decision.get("direct_promotion_recommendation"), False),
        BASE_MODULE._expect("readiness_result_review_requires_followup_decision", decision.get("followup_requires_explicit_user_decision"), True),
        BASE_MODULE._expect("readiness_result_review_execution_authorized_false", decision.get("evaluation_runbook_execution_authorized"), False),
        BASE_MODULE._expect("readiness_result_review_source_execution_passed", source_execution.get("passed"), True),
        BASE_MODULE._expect("readiness_result_review_metrics_manifest_count", source_execution.get("metrics_manifest_count"), 6),
        BASE_MODULE._expect("readiness_result_review_no_go_summary_count", source_execution.get("no_go_summary_count"), EXPECTED_SOURCE_NO_GO_COUNT),
        BASE_MODULE._expect("readiness_result_review_evidence_matrix_count", source_execution.get("evidence_matrix_count"), 6),
        BASE_MODULE._expect("readiness_result_review_source_static_passed", source_static.get("passed"), True),
        BASE_MODULE._expect("readiness_result_review_selector_promotion_false", decision.get("selector_promotion_authorized"), False),
        BASE_MODULE._expect("readiness_result_review_deployment_false", decision.get("deployment_authorized"), False),
        BASE_MODULE._expect("readiness_result_review_safety_claim_false", decision.get("safety_benefit_claim_authorized"), False),
        BASE_MODULE._expect("readiness_result_review_camp_claim_false", decision.get("camp_over_dp_top1_claim_authorized"), False),
    ]


def _safety_score_doc_checks(text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._check("safety_score_doc_has_safetycost", "SafetyCost_v1" in text, "SafetyCost_v1", "present"),
        BASE_MODULE._check("safety_score_doc_has_claim_rule", "ci95_high(DeltaSafetyCost_v1) < 0" in text, "ci95_high(DeltaSafetyCost_v1) < 0", "present"),
        BASE_MODULE._check("safety_score_doc_has_hard_gate", "hard_gate_passed == true" in text, "hard_gate_passed == true", "present"),
        BASE_MODULE._check("safety_score_doc_forbids_formal_seeds", "no paired run uses seeds `11`, `12`, or `13`" in text, "no paired run uses seeds `11`, `12`, or `13`", "present"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("audit_latest_status_is_execution_plan_static_review_passed", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("audit_latest_eof_authorizes_execution_preflight", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("audit_execution_plan_static_review_passed", BASE_MODULE._latest_value(v14_text, "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_static_review_passed"), "True"),
        BASE_MODULE._expect("audit_execution_preflight_authorized", BASE_MODULE._latest_value(v14_text, "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_authorized"), "True"),
        BASE_MODULE._expect("audit_paired_evaluation_not_executed", BASE_MODULE._latest_value(v14_text, "paired_evaluation_executed_by_current_gate"), "False"),
        BASE_MODULE._expect("audit_selector_promotion_false", BASE_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        BASE_MODULE._expect("audit_deployment_false", BASE_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        BASE_MODULE._expect("audit_safety_claim_false", BASE_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        BASE_MODULE._expect("audit_camp_over_dp_claim_false", BASE_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        BASE_MODULE._expect("status_doc_latest_status_is_execution_plan_static_review_passed", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("status_doc_latest_eof_authorizes_execution_preflight", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
    ]


def _evidence_locks(
    *,
    label: str | None,
    source_review: dict[str, Any],
    runtime_result_review: dict[str, Any],
    delta_review: dict[str, Any],
    readiness_result_review: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {"name": "passed_execution_plan_static_review_artifact", "requirement": "source static review must pass with immutable root and nested SHA256SUMS", "status": BASE_MODULE._dict(source_review.get("final_decision")).get("status"), "label": label},
        {"name": "source_execution_plan_artifact", "requirement": "source plan must remain no-execution and authorize only execution preflight"},
        {"name": "runtime_result_review_json", "requirement": "locks fixed DP candidate tensor, shadow selection logs, DP Top-1 comparator, and default-off evidence", "records": BASE_MODULE._dict(runtime_result_review.get("records")).get("record_count")},
        {"name": "shadow_vs_top1_delta_review_json", "requirement": "locks static objective delta support as non-claim evidence only", "static_objective_delta_supported": BASE_MODULE._dict(delta_review.get("final_decision")).get("static_objective_delta_supported")},
        {"name": "readiness_result_review_json", "requirement": "locks prior no-promotion/no-deployment/no-claim boundary", "direct_promotion_recommendation": BASE_MODULE._dict(readiness_result_review.get("final_decision")).get("direct_promotion_recommendation")},
        {"name": "safetycost_v1_contract", "requirement": "SafetyCost v1 hard-gate claim rule must be frozen before future execution"},
        {"name": "v14_eof_contract", "requirement": "EOF must authorize only this preflight gate"},
        {"name": "artifact_hash_and_heads_contract", "requirement": "future execution artifacts must include JSON/MD/SHA256SUMS/HEADS/COMMAND/stdout/stderr/run.exit"},
    ]


def _required_input_manifests(
    runtime_result_review: dict[str, Any],
    delta_review: dict[str, Any],
) -> list[dict[str, Any]]:
    records = BASE_MODULE._dict(runtime_result_review.get("records"))
    delta_records = BASE_MODULE._dict(delta_review.get("records"))
    return [
        {"name": "fixed_dp_candidate_tensor_manifest", "requirement": "same fixed DP candidate tensor identity for CAMP shadow-selected and DP Top-1", "record_count": records.get("record_count")},
        {"name": "camp_shadow_selection_log_manifest", "requirement": "CAMP shadow_selected_index rows are logged default-off with no executed-output effect", "selection_log_count": delta_records.get("selection_log_count")},
        {"name": "dp_top1_candidate_index_manifest", "requirement": "DP Top-1 comparator remains candidate index 0 on the same records", "executed_top1_records": records.get("executed_top1_records")},
        {"name": "strict_paired_run_key_manifest", "requirement": "future execution must pair only identical run keys and record identities"},
        {"name": "safetycost_v1_hard_gate_config", "requirement": "future execution must compute SafetyCost v1 deltas without claim unless hard gates pass"},
        {"name": "coverage_uncertainty_bucket_manifest", "requirement": "future execution must report coverage, fallback, uncertainty, buckets, and confidence intervals"},
        {"name": "no_go_condition_manifest", "requirement": "future execution must fail closed on any fixed-DP, affine, convexity, seed, or claim boundary violation"},
        {"name": "source_artifact_sha256_manifest", "requirement": "future execution must preserve source JSON, MD, nested SHA256SUMS, root SHA256SUMS, HEADS, COMMAND, stdout, stderr, and run.exit"},
    ]


def _preflight_plan() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "preflight_check_only", "executes_paired_evaluation": False}
        for name in EXPECTED_PREFLIGHT_ITEMS
    ]


def _future_outputs() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "future_execution_output_not_materialized_by_preflight"}
        for name in EXPECTED_FUTURE_OUTPUTS
    ]


def _no_go_register() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "predeclared_reject_condition"}
        for name in EXPECTED_NO_GO
    ]


def _preflight_contract_checks(
    evidence_locks: list[dict[str, Any]],
    required_input_manifests: list[dict[str, Any]],
    preflight_plan: list[dict[str, Any]],
    future_outputs: list[dict[str, Any]],
    no_go: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("evidence_lock_names", [item.get("name") for item in evidence_locks], list(EXPECTED_EVIDENCE_LOCKS)),
        BASE_MODULE._expect("required_input_manifest_names", [item.get("name") for item in required_input_manifests], list(EXPECTED_REQUIRED_INPUT_MANIFESTS)),
        BASE_MODULE._expect("preflight_item_names", [item.get("name") for item in preflight_plan], list(EXPECTED_PREFLIGHT_ITEMS)),
        BASE_MODULE._expect("preflight_items_do_not_execute", sorted({item.get("executes_paired_evaluation") for item in preflight_plan}), [False]),
        BASE_MODULE._expect("future_output_names", [item.get("name") for item in future_outputs], list(EXPECTED_FUTURE_OUTPUTS)),
        BASE_MODULE._expect("no_go_names", [item.get("name") for item in no_go], list(EXPECTED_NO_GO)),
    ]


def _source_static_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_review.get("final_decision"))
    source_plan = BASE_MODULE._dict(source_review.get("source_plan_summary"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(BASE_MODULE._list(source_review.get("review_checks"))),
        "failed_check_count": len(BASE_MODULE._list(decision.get("failed_checks"))),
        "source_plan_check_count": source_plan.get("plan_check_count"),
    }


def _runtime_result_summary(report: dict[str, Any]) -> dict[str, Any]:
    records = BASE_MODULE._dict(report.get("records"))
    execution = BASE_MODULE._dict(report.get("execution"))
    return {
        "record_count": records.get("record_count"),
        "selection_log_count": execution.get("selection_log_count"),
        "executed_top1_records": records.get("executed_top1_records"),
        "shadow_selected_index_differs_from_executed_index_records": records.get("shadow_selected_index_differs_from_executed_index_records"),
    }


def _delta_review_summary(report: dict[str, Any]) -> dict[str, Any]:
    records = BASE_MODULE._dict(report.get("records"))
    decision = BASE_MODULE._dict(report.get("final_decision"))
    return {
        "record_count": records.get("record_count"),
        "static_objective_delta_supported": decision.get("static_objective_delta_supported"),
        "shadow_selected_index_differs_from_executed_index_records": records.get("shadow_selected_index_differs_from_executed_index_records"),
    }


def _readiness_result_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(report.get("final_decision"))
    source_execution = BASE_MODULE._dict(report.get("source_execution_summary"))
    return {
        "passed": decision.get("passed"),
        "direct_promotion_recommendation": decision.get("direct_promotion_recommendation"),
        "metrics_manifest_count": source_execution.get("metrics_manifest_count"),
        "no_go_summary_count": source_execution.get("no_go_summary_count"),
        "evidence_matrix_count": source_execution.get("evidence_matrix_count"),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "execution_preflight_enabled" in failed:
        failure_class = "explicit_paired_evaluation_execution_preflight_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith("source_") for name in failed):
        failure_class = "source_execution_plan_static_review_contract_failure"
    elif any(name.startswith(("runtime_", "delta_", "readiness_", "safety_score_doc_")) for name in failed):
        failure_class = "paired_execution_evidence_source_contract_failure"
    elif any(name.startswith(("evidence_", "required_", "preflight_", "future_", "no_go_")) for name in failed):
        failure_class = "paired_execution_preflight_contract_failure"
    elif any("dp_head" in name or "dp_fixed" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    else:
        failure_class = "artifact_contract_failure"
    decision: dict[str, Any] = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_ready": passed,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_authorized": passed,
        "paired_evaluation_executed_by_this_gate": False,
        "paired_evaluation_execution_authorized": False,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "static_review_paired_evaluation_execution_preflight_only" if passed else "repair_contract_before_rerun",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
