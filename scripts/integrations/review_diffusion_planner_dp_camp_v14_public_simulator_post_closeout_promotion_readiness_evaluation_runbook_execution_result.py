#!/usr/bin/env python3
"""Read-only result review for the v14 promotion-readiness runbook execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_STATIC_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_execution_static_review_v1"
)
SOURCE_EXECUTION_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_execution_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_execution_result_review_v1"
)
SOURCE_STATIC_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_passed"
)
SOURCE_EXECUTION_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "user_decision_required_before_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_followup_or_promotion_authorization"
)
STATIC_REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review.json"
)
STATIC_REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review.md"
)
EXECUTION_JSON_NAME = "post_closeout_promotion_readiness_evaluation_runbook_execution.json"
EXECUTION_MD_NAME = "post_closeout_promotion_readiness_evaluation_runbook_execution.md"
REVIEW_JSON_NAME = "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review.json"
REVIEW_MD_NAME = "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review.md"

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
    "replay_execution_authorized",
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
)
ANALYSIS_FALSE_FLAGS = (
    "training_execution",
    "replay_execution",
    "candidate_generation",
    "dp_modification",
    "online_selector_change",
    "promotion_executed",
    "deployment_executed",
    "safety_or_camp_over_dp_claim",
)
EXPECTED_METRICS = (
    "fixed_dp_candidate_tensor_provenance",
    "default_off_shadow_selection_distribution",
    "masked_affine_objective_delta",
    "feasibility_and_fail_closed_counts",
    "split_and_seed_zero_overlap",
    "uncertainty_or_confidence_interval",
)
EXPECTED_NO_GO = (
    "dp_head_drift",
    "camp_generates_or_modifies_trajectory",
    "candidate_tensor_not_from_fixed_dp",
    "closed_loop_outcome_input_present",
    "full36_or_formal_seed_11_12_13_present",
    "non_affine_score_or_nonconvex_master",
    "promotion_deployment_or_online_selector_change",
    "safety_or_camp_over_dp_claim_requested",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runbook_execution_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--runbook_execution_static_review_json", type=Path, required=True)
    parser.add_argument("--runbook_execution_static_review_md", type=Path, required=True)
    parser.add_argument("--runbook_execution_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_runbook_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_runbook_execution_json", type=Path, required=True)
    parser.add_argument("--source_runbook_execution_md", type=Path, required=True)
    parser.add_argument("--source_runbook_execution_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review",
        action="store_true",
        help="Explicit opt-in for read-only result review of the runbook execution artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runbook_execution_static_review_artifact_dir=args.runbook_execution_static_review_artifact_dir,
        runbook_execution_static_review_json=args.runbook_execution_static_review_json,
        runbook_execution_static_review_md=args.runbook_execution_static_review_md,
        runbook_execution_static_review_sha256s=args.runbook_execution_static_review_sha256s,
        source_runbook_execution_artifact_dir=args.source_runbook_execution_artifact_dir,
        source_runbook_execution_json=args.source_runbook_execution_json,
        source_runbook_execution_md=args.source_runbook_execution_md,
        source_runbook_execution_sha256s=args.source_runbook_execution_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runbook_execution_static_review_artifact_dir: Path,
    runbook_execution_static_review_json: Path,
    runbook_execution_static_review_md: Path,
    runbook_execution_static_review_sha256s: Path,
    source_runbook_execution_artifact_dir: Path,
    source_runbook_execution_json: Path,
    source_runbook_execution_md: Path,
    source_runbook_execution_sha256s: Path,
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
    static_artifact = runbook_execution_static_review_artifact_dir.resolve()
    execution_artifact = source_runbook_execution_artifact_dir.resolve()
    paths = {
        "static_review_json": runbook_execution_static_review_json.resolve(),
        "static_review_md": runbook_execution_static_review_md.resolve(),
        "static_review_sha256s": runbook_execution_static_review_sha256s.resolve(),
        "source_execution_json": source_runbook_execution_json.resolve(),
        "source_execution_md": source_runbook_execution_md.resolve(),
        "source_execution_sha256s": source_runbook_execution_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    static_files = {
        "command": static_artifact / "COMMAND",
        "heads": static_artifact / "HEADS",
        "stdout": static_artifact / "stdout.txt",
        "stderr": static_artifact / "stderr.txt",
        "run_exit": static_artifact / "run.exit",
        "root_sha256s": static_artifact / "SHA256SUMS",
        "review_json": static_artifact / "review" / STATIC_REVIEW_JSON_NAME,
        "review_md": static_artifact / "review" / STATIC_REVIEW_MD_NAME,
        "review_sha256s": static_artifact / "review" / "SHA256SUMS",
    }
    execution_files = {
        "command": execution_artifact / "COMMAND",
        "heads": execution_artifact / "HEADS",
        "stdout": execution_artifact / "stdout.txt",
        "stderr": execution_artifact / "stderr.txt",
        "run_exit": execution_artifact / "run.exit",
        "root_sha256s": execution_artifact / "SHA256SUMS",
        "execution_json": execution_artifact / "execution" / EXECUTION_JSON_NAME,
        "execution_md": execution_artifact / "execution" / EXECUTION_MD_NAME,
        "execution_sha256s": execution_artifact / "execution" / "SHA256SUMS",
    }
    source_static_review = _read_json_dict(paths["static_review_json"])
    source_execution = _read_json_dict(paths["source_execution_json"])
    static_root_sha256s = _read_sha256sums(static_files["root_sha256s"])
    static_review_sha256s = _read_sha256sums(paths["static_review_sha256s"])
    execution_root_sha256s = _read_sha256sums(execution_files["root_sha256s"])
    execution_sha256s = _read_sha256sums(paths["source_execution_sha256s"])
    static_heads = _parse_key_values(_read_text(static_files["heads"]))
    execution_heads = _parse_key_values(_read_text(execution_files["heads"]))
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("result_review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("static_review_artifact_dir_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _check("source_execution_artifact_dir_exists", execution_artifact.is_dir(), str(execution_artifact), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in static_files.items():
        checks.extend(_path_checks(f"static_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in execution_files.items():
        checks.extend(_path_checks(f"execution_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("static_review_json_matches_artifact_layout", paths["static_review_json"], static_files["review_json"]),
            _expect("static_review_md_matches_artifact_layout", paths["static_review_md"], static_files["review_md"]),
            _expect("static_review_sha256s_matches_artifact_layout", paths["static_review_sha256s"], static_files["review_sha256s"]),
            _expect("source_execution_json_matches_artifact_layout", paths["source_execution_json"], execution_files["execution_json"]),
            _expect("source_execution_md_matches_artifact_layout", paths["source_execution_md"], execution_files["execution_md"]),
            _expect("source_execution_sha256s_matches_artifact_layout", paths["source_execution_sha256s"], execution_files["execution_sha256s"]),
        ]
    )
    checks.extend(_static_artifact_hash_checks(static_files, static_root_sha256s, static_review_sha256s))
    checks.extend(_execution_artifact_hash_checks(execution_files, execution_root_sha256s, execution_sha256s))
    checks.extend(_heads_checks(static_heads, execution_heads, source_static_review, source_execution, execution_artifact))
    checks.extend(_source_static_review_contract_checks(source_static_review, execution_artifact))
    checks.extend(_source_execution_contract_checks(source_execution))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "result_review_only": True,
            "read_only": True,
            "runbook_execution_static_review_artifact_dir": str(static_artifact),
            "source_runbook_execution_artifact_dir": str(execution_artifact),
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
            "direct_promotion_recommendation": False,
            "requires_explicit_user_decision_for_followup": True,
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **static_files, **execution_files}.items()
        },
        "source_static_review_summary": _source_static_summary(source_static_review),
        "source_execution_summary": _source_execution_summary(source_execution),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "result_review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / REVIEW_JSON_NAME, report)
    (output_dir / REVIEW_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Evaluation Runbook Execution Result Review",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        f"- direct_promotion_recommendation: `{decision['direct_promotion_recommendation']}`",
        "",
        "## Source Static Review Summary",
    ]
    for key, value in report["source_static_review_summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Source Execution Summary")
    for key, value in report["source_execution_summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks"])
    for check in report["result_review_checks"]:
        status = "pass" if check["passed"] else "fail"
        lines.append(
            f"- {status} `{check['name']}` observed=`{_compact(check['observed'])}` expected=`{_compact(check['expected'])}`"
        )
    lines.extend(
        [
            "",
            "This is a read-only result review. It does not run replay, train CAMP, "
            "generate candidates, modify DP, promote, deploy, activate an online "
            "selector, or make safety/CAMP-over-DP claims.",
        ]
    )
    return "\n".join(lines) + "\n"


def _static_artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("static_artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("static_artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("static_artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("static_artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("static_artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("static_artifact_review_json_root_sha", artifact_files["review_json"], root_sha256s, (f"review/{STATIC_REVIEW_JSON_NAME}", f"./review/{STATIC_REVIEW_JSON_NAME}", STATIC_REVIEW_JSON_NAME)),
        _sha256sums_expect("static_artifact_review_md_root_sha", artifact_files["review_md"], root_sha256s, (f"review/{STATIC_REVIEW_MD_NAME}", f"./review/{STATIC_REVIEW_MD_NAME}", STATIC_REVIEW_MD_NAME)),
        _sha256sums_expect("static_artifact_review_sha256s_root_sha", artifact_files["review_sha256s"], root_sha256s, ("review/SHA256SUMS", "./review/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("static_artifact_review_json_review_sha", artifact_files["review_json"], review_sha256s, (STATIC_REVIEW_JSON_NAME, f"./{STATIC_REVIEW_JSON_NAME}")),
        _sha256sums_expect("static_artifact_review_md_review_sha", artifact_files["review_md"], review_sha256s, (STATIC_REVIEW_MD_NAME, f"./{STATIC_REVIEW_MD_NAME}")),
        _expect("static_artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _execution_artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    execution_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("execution_artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("execution_artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("execution_artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("execution_artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("execution_artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("execution_artifact_json_root_sha", artifact_files["execution_json"], root_sha256s, (f"execution/{EXECUTION_JSON_NAME}", f"./execution/{EXECUTION_JSON_NAME}", EXECUTION_JSON_NAME)),
        _sha256sums_expect("execution_artifact_md_root_sha", artifact_files["execution_md"], root_sha256s, (f"execution/{EXECUTION_MD_NAME}", f"./execution/{EXECUTION_MD_NAME}", EXECUTION_MD_NAME)),
        _sha256sums_expect("execution_artifact_sha256s_root_sha", artifact_files["execution_sha256s"], root_sha256s, ("execution/SHA256SUMS", "./execution/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("execution_artifact_json_execution_sha", artifact_files["execution_json"], execution_sha256s, (EXECUTION_JSON_NAME, f"./{EXECUTION_JSON_NAME}")),
        _sha256sums_expect("execution_artifact_md_execution_sha", artifact_files["execution_md"], execution_sha256s, (EXECUTION_MD_NAME, f"./{EXECUTION_MD_NAME}")),
        _expect("execution_artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(
    static_heads: dict[str, str],
    execution_heads: dict[str, str],
    source_static_review: dict[str, Any],
    source_execution: dict[str, Any],
    execution_artifact: Path,
) -> list[dict[str, Any]]:
    static_analysis = _dict(source_static_review.get("analysis"))
    execution_analysis = _dict(source_execution.get("analysis"))
    return [
        _expect("static_heads_dp_fixed", static_heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("execution_heads_dp_fixed", execution_heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("static_heads_camp_matches_source_analysis", static_heads.get("camp_head"), static_analysis.get("current_camp_head")),
        _expect("execution_heads_camp_matches_source_analysis", execution_heads.get("camp_head"), execution_analysis.get("current_camp_head")),
        _expect("static_heads_source_execution_artifact", static_heads.get("source_runbook_execution_artifact"), str(execution_artifact)),
        _expect("static_review_source_execution_artifact", static_analysis.get("runbook_execution_artifact_dir"), str(execution_artifact)),
    ]


def _source_static_review_contract_checks(source_static_review: dict[str, Any], execution_artifact: Path) -> list[dict[str, Any]]:
    decision = _dict(source_static_review.get("final_decision"))
    analysis = _dict(source_static_review.get("analysis"))
    blocked = _dict(source_static_review.get("blocked_actions"))
    summary = _dict(source_static_review.get("source_execution_summary"))
    checks = [
        _expect("source_static_review_schema", source_static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_static_review_failure_class", decision.get("failure_class"), None),
        _expect("source_static_review_authorized_current_work", decision.get("authorized_current_work"), SOURCE_STATIC_REVIEW_STATUS.replace("_passed", "_only")),
        _expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_result_review_authorized", decision.get("evaluation_runbook_execution_result_review_authorized"), True),
        _expect("source_static_review_no_reexecution_authorized", decision.get("evaluation_runbook_execution_authorized"), False),
        _expect("source_static_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_static_only", analysis.get("static_review_only"), True),
        _expect("source_static_review_read_only", analysis.get("read_only"), True),
        _expect("source_static_review_source_execution_path", analysis.get("runbook_execution_artifact_dir"), str(execution_artifact)),
        _expect("source_static_review_check_failures", _failed_source_checks(source_static_review, "review_checks"), []),
        _expect("source_static_review_check_count", len(_list(source_static_review.get("review_checks"))), 136),
        _expect("source_static_review_summary_status", summary.get("status"), SOURCE_EXECUTION_STATUS),
        _expect("source_static_review_summary_passed", summary.get("passed"), True),
        _expect("source_static_review_summary_check_count", summary.get("check_count"), 216),
        _expect("source_static_review_summary_metrics_count", summary.get("metrics_manifest_count"), 6),
        _expect("source_static_review_summary_no_go_count", summary.get("no_go_summary_count"), 8),
        _expect("source_static_review_summary_evidence_count", summary.get("evidence_matrix_count"), 6),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_static_review_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_static_review_blocked_{action}", blocked.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_static_review_decision_{flag}", decision.get(flag), False))
    return checks


def _source_execution_contract_checks(source_execution: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_execution.get("final_decision"))
    analysis = _dict(source_execution.get("analysis"))
    blocked = _dict(source_execution.get("blocked_actions"))
    checks = [
        _expect("source_execution_schema", source_execution.get("schema_version"), SOURCE_EXECUTION_SCHEMA),
        _expect("source_execution_status", decision.get("status"), SOURCE_EXECUTION_STATUS),
        _expect("source_execution_passed", decision.get("passed"), True),
        _expect("source_execution_failed_checks", decision.get("failed_checks"), []),
        _expect("source_execution_failure_class", decision.get("failure_class"), None),
        _expect("source_execution_static_review_authorized", decision.get("evaluation_runbook_execution_static_review_authorized"), True),
        _expect("source_execution_no_reexecution_authorized", decision.get("evaluation_runbook_execution_authorized"), False),
        _expect("source_execution_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_execution_read_only", analysis.get("read_only"), True),
        _expect("source_execution_materializes_nonclaim", analysis.get("materializes_nonclaim_evidence_matrix"), True),
        _expect("source_execution_metrics", _names(source_execution.get("metrics_manifest")), list(EXPECTED_METRICS)),
        _expect("source_execution_no_go", _names(source_execution.get("no_go_summary")), list(EXPECTED_NO_GO)),
        _expect("source_execution_no_go_triggered", [item.get("triggered") for item in _list(source_execution.get("no_go_summary"))], [False] * len(EXPECTED_NO_GO)),
        _expect("source_execution_evidence_matrix_count", len(_list(source_execution.get("evidence_matrix"))), len(EXPECTED_METRICS)),
        _expect("source_execution_check_failures", _failed_source_checks(source_execution, "execution_checks"), []),
        _expect("source_execution_executed", decision.get("evaluation_runbook_executed_by_this_gate"), True),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_execution_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_execution_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_execution_blocked_{action}", blocked.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_execution_decision_{flag}", decision.get(flag), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    expected_pair = (SOURCE_STATIC_REVIEW_STATUS, AUTHORIZED_CURRENT_WORK)
    return [
        _expect("audit_latest_eof_authorizes_result_review", (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target")), expected_pair),
        _expect("status_doc_latest_eof_authorizes_result_review", (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target")), expected_pair),
        _expect("audit_runbook_execution_static_review_passed", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_passed"), "True"),
        _expect("audit_runbook_execution_result_review_authorized", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_authorized"), "True"),
        _expect("audit_runbook_execution_authorized", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized"), "False"),
        _expect("audit_runtime_execution_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _source_static_summary(source_static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_static_review.get("final_decision"))
    return {
        "schema_version": source_static_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(_list(source_static_review.get("review_checks"))),
    }


def _source_execution_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_execution.get("final_decision"))
    return {
        "schema_version": source_execution.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "check_count": len(_list(source_execution.get("execution_checks"))),
        "metrics_manifest_count": len(_list(source_execution.get("metrics_manifest"))),
        "no_go_summary_count": len(_list(source_execution.get("no_go_summary"))),
        "evidence_matrix_count": len(_list(source_execution.get("evidence_matrix"))),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_passed": bool(passed),
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "followup_requires_explicit_user_decision": bool(passed),
        "recommendation": "do_not_promote_from_current_runbook_execution_result_alone",
        "immediate_action": "stop_for_user_decision_before_any_promotion_deployment_online_selector_or_claim",
        "score_expression": SCORE_EXPRESSION,
        "evaluation_runbook_executed_by_this_gate": False,
        "evaluation_runbook_execution_authorized": False,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "result_review_enabled" in failed_set:
        return "explicit_runbook_execution_result_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "static_heads_dp_fixed", "execution_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "source_artifact_sha256_mismatch"
    if any(name.startswith("source_static_review") for name in failed):
        return "source_runbook_execution_static_review_contract_failure"
    if any(name.startswith("source_execution") for name in failed):
        return "source_runbook_execution_contract_failure"
    return "promotion_readiness_evaluation_runbook_execution_result_review_failure"


def _path_checks(name: str, path: Path, *, require_file: bool, allow_empty: bool = False) -> list[dict[str, Any]]:
    exists = path.is_file() if require_file else path.is_dir()
    checks = [_check(f"{name}_exists", exists, str(path), "file" if require_file else "directory")]
    if require_file and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.is_file() and path.stat().st_size > 0, path.stat().st_size if path.is_file() else None, ">0 bytes"))
    return checks


def _sha256sums_expect(name: str, path: Path, sha256sums: dict[str, str], keys: tuple[str, ...]) -> dict[str, Any]:
    observed = _sha256(path) if path.is_file() else None
    listed = [sha256sums.get(key) for key in keys if key in sha256sums]
    return _check(name, observed is not None and observed in listed, {"observed": observed, "listed": listed, "keys": keys}, "matching sha256 listed in SHA256SUMS")


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "observed": _stable(observed), "expected": _stable(expected)}


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _read_sha256sums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            key = parts[1].strip()
            value = parts[0]
            values[key] = value
            values[key.removeprefix("./")] = value
            values[Path(key).name] = value
    return values


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
        values[key.strip().lower()] = value.strip()
    return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    matches = [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


def _names(value: Any) -> list[str]:
    return [
        str(item.get("name"))
        for item in _list(value)
        if isinstance(item, dict) and item.get("name")
    ]


def _failed_source_checks(payload: dict[str, Any], field: str) -> list[str]:
    return [
        str(check.get("name"))
        for check in _list(payload.get(field))
        if isinstance(check, dict) and not check.get("passed")
    ]


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    return value


def _compact(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= 160 else text[:157] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
