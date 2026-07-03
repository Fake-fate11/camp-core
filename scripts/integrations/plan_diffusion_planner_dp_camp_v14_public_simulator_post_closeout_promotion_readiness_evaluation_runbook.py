#!/usr/bin/env python3
"""Plan the v14 promotion-readiness evaluation runbook without executing it."""

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
    "promotion_readiness_evaluation_runbook_preflight_static_review_v1"
)
SOURCE_PREFLIGHT_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_preflight_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_plan_v1"
)
SOURCE_STATIC_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_passed"
)
SOURCE_PREFLIGHT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_preflight_ready"
)
SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_only"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_plan_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_only"
)

STATIC_REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review.json"
)
STATIC_REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review.md"
)
PREFLIGHT_JSON_NAME = "post_closeout_promotion_readiness_evaluation_runbook_preflight.json"
PREFLIGHT_MD_NAME = "post_closeout_promotion_readiness_evaluation_runbook_preflight.md"
PLAN_JSON_NAME = "post_closeout_promotion_readiness_evaluation_runbook_plan.json"
PLAN_MD_NAME = "post_closeout_promotion_readiness_evaluation_runbook_plan.md"

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
EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "replay_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
    "evaluation_runbook_executed_by_this_gate",
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
    "evaluation_runbook_execution",
)
EXPECTED_RUNBOOK_STEPS = (
    "lock_source_artifacts_and_heads",
    "load_fixed_dp_candidate_tensor_outputs_read_only",
    "apply_default_off_shadow_selector_without_output_effect",
    "compute_predeclared_metrics_and_uncertainty",
    "evaluate_fail_closed_and_no_go_conditions",
    "construct_nonclaim_evidence_matrix",
    "emit_static_review_ready_runbook_plan_artifact",
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
    parser.add_argument("--runbook_preflight_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--runbook_preflight_static_review_json", type=Path, required=True)
    parser.add_argument("--runbook_preflight_static_review_md", type=Path, required=True)
    parser.add_argument("--runbook_preflight_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_runbook_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_runbook_preflight_json", type=Path, required=True)
    parser.add_argument("--source_runbook_preflight_md", type=Path, required=True)
    parser.add_argument("--source_runbook_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_plan",
        action="store_true",
        help="Explicit opt-in for read-only promotion-readiness evaluation runbook planning.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runbook_preflight_static_review_artifact_dir=args.runbook_preflight_static_review_artifact_dir,
        runbook_preflight_static_review_json=args.runbook_preflight_static_review_json,
        runbook_preflight_static_review_md=args.runbook_preflight_static_review_md,
        runbook_preflight_static_review_sha256s=args.runbook_preflight_static_review_sha256s,
        source_runbook_preflight_artifact_dir=args.source_runbook_preflight_artifact_dir,
        source_runbook_preflight_json=args.source_runbook_preflight_json,
        source_runbook_preflight_md=args.source_runbook_preflight_md,
        source_runbook_preflight_sha256s=args.source_runbook_preflight_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_evaluation_runbook_plan,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runbook_preflight_static_review_artifact_dir: Path,
    runbook_preflight_static_review_json: Path,
    runbook_preflight_static_review_md: Path,
    runbook_preflight_static_review_sha256s: Path,
    source_runbook_preflight_artifact_dir: Path,
    source_runbook_preflight_json: Path,
    source_runbook_preflight_md: Path,
    source_runbook_preflight_sha256s: Path,
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
    static_artifact = runbook_preflight_static_review_artifact_dir.resolve()
    preflight_artifact = source_runbook_preflight_artifact_dir.resolve()
    paths = {
        "runbook_preflight_static_review_json": runbook_preflight_static_review_json.resolve(),
        "runbook_preflight_static_review_md": runbook_preflight_static_review_md.resolve(),
        "runbook_preflight_static_review_sha256s": runbook_preflight_static_review_sha256s.resolve(),
        "source_runbook_preflight_json": source_runbook_preflight_json.resolve(),
        "source_runbook_preflight_md": source_runbook_preflight_md.resolve(),
        "source_runbook_preflight_sha256s": source_runbook_preflight_sha256s.resolve(),
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
    preflight_files = {
        "command": preflight_artifact / "COMMAND",
        "heads": preflight_artifact / "HEADS",
        "stdout": preflight_artifact / "stdout.txt",
        "stderr": preflight_artifact / "stderr.txt",
        "run_exit": preflight_artifact / "run.exit",
        "root_sha256s": preflight_artifact / "SHA256SUMS",
        "preflight_json": preflight_artifact / "preflight" / PREFLIGHT_JSON_NAME,
        "preflight_md": preflight_artifact / "preflight" / PREFLIGHT_MD_NAME,
        "preflight_sha256s": preflight_artifact / "preflight" / "SHA256SUMS",
    }
    static_review = _read_json_dict(paths["runbook_preflight_static_review_json"])
    source_preflight = _read_json_dict(paths["source_runbook_preflight_json"])
    static_root_sha256s = _read_sha256sums(static_files["root_sha256s"])
    static_review_sha256s = _read_sha256sums(paths["runbook_preflight_static_review_sha256s"])
    preflight_root_sha256s = _read_sha256sums(preflight_files["root_sha256s"])
    source_preflight_sha256s = _read_sha256sums(paths["source_runbook_preflight_sha256s"])
    static_heads = _parse_key_values(_read_text(static_files["heads"]))
    preflight_heads = _parse_key_values(_read_text(preflight_files["heads"]))
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("runbook_plan_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("static_review_artifact_dir_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _check("source_preflight_artifact_dir_exists", preflight_artifact.is_dir(), str(preflight_artifact), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in static_files.items():
        checks.extend(_path_checks(f"static_review_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in preflight_files.items():
        checks.extend(_path_checks(f"source_preflight_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("static_review_json_matches_artifact_layout", paths["runbook_preflight_static_review_json"], static_files["review_json"]),
            _expect("static_review_md_matches_artifact_layout", paths["runbook_preflight_static_review_md"], static_files["review_md"]),
            _expect("static_review_sha256s_matches_artifact_layout", paths["runbook_preflight_static_review_sha256s"], static_files["review_sha256s"]),
            _expect("preflight_json_matches_artifact_layout", paths["source_runbook_preflight_json"], preflight_files["preflight_json"]),
            _expect("preflight_md_matches_artifact_layout", paths["source_runbook_preflight_md"], preflight_files["preflight_md"]),
            _expect("preflight_sha256s_matches_artifact_layout", paths["source_runbook_preflight_sha256s"], preflight_files["preflight_sha256s"]),
        ]
    )
    checks.extend(_static_artifact_hash_checks(static_files, static_root_sha256s, static_review_sha256s))
    checks.extend(_preflight_artifact_hash_checks(preflight_files, preflight_root_sha256s, source_preflight_sha256s))
    checks.extend(_heads_checks(static_heads, preflight_heads, static_review, source_preflight))
    checks.extend(_source_static_review_contract_checks(static_review))
    checks.extend(_source_preflight_contract_checks(source_preflight))
    checks.extend(_audit_checks(v14_text, status_text))
    checks.extend(_planned_content_checks())

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "plan_only": True,
            "read_only": True,
            "runbook_preflight_static_review_artifact_dir": str(static_artifact),
            "source_runbook_preflight_artifact_dir": str(preflight_artifact),
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
            "evaluation_runbook_execution": False,
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **static_files, **preflight_files}.items()
        },
        "source_static_review_summary": _source_static_review_summary(static_review),
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "runbook_plan": _runbook_plan(),
        "planned_artifacts": _planned_artifacts(),
        "metrics_plan": _metrics_plan(),
        "decision_criteria_plan": _decision_criteria_plan(),
        "no_go_conditions": _no_go_conditions(),
        "forbidden_actions": _forbidden_actions(),
        "future_review_requirements": _future_review_requirements(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / PLAN_JSON_NAME, report)
    (output_dir / PLAN_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Evaluation Runbook Plan",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- recommendation: `{decision['recommendation']}`",
        f"- immediate_action: `{decision['immediate_action']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Runbook Plan",
    ]
    for item in report["runbook_plan"]:
        lines.append(f"- `{item['name']}`: {item['status']}")
    lines.extend(["", "## No-Go Conditions"])
    for item in report["no_go_conditions"]:
        lines.append(f"- `{item['name']}`: {item['required_state']}")
    lines.extend(["", "## Checks"])
    for check in report["plan_checks"]:
        status = "pass" if check["passed"] else "fail"
        lines.append(
            f"- {status} `{check['name']}` observed=`{_compact(check['observed'])}` expected=`{_compact(check['expected'])}`"
        )
    return "\n".join(lines) + "\n"


def _static_artifact_hash_checks(
    files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("static_command_root_sha", files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("static_heads_root_sha", files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("static_stdout_root_sha", files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("static_stderr_root_sha", files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("static_run_exit_root_sha", files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("static_review_json_root_sha", files["review_json"], root_sha256s, (f"review/{STATIC_REVIEW_JSON_NAME}", STATIC_REVIEW_JSON_NAME)),
        _sha256sums_expect("static_review_md_root_sha", files["review_md"], root_sha256s, (f"review/{STATIC_REVIEW_MD_NAME}", STATIC_REVIEW_MD_NAME)),
        _sha256sums_expect("static_review_sha256s_root_sha", files["review_sha256s"], root_sha256s, ("review/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("static_review_json_review_sha", files["review_json"], review_sha256s, (STATIC_REVIEW_JSON_NAME, f"./{STATIC_REVIEW_JSON_NAME}")),
        _sha256sums_expect("static_review_md_review_sha", files["review_md"], review_sha256s, (STATIC_REVIEW_MD_NAME, f"./{STATIC_REVIEW_MD_NAME}")),
        _expect("static_run_exit_zero", _read_text(files["run_exit"]).strip(), "0"),
    ]


def _preflight_artifact_hash_checks(
    files: dict[str, Path],
    root_sha256s: dict[str, str],
    preflight_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("preflight_command_root_sha", files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("preflight_heads_root_sha", files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("preflight_stdout_root_sha", files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("preflight_stderr_root_sha", files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("preflight_run_exit_root_sha", files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("preflight_json_root_sha", files["preflight_json"], root_sha256s, (f"preflight/{PREFLIGHT_JSON_NAME}", PREFLIGHT_JSON_NAME)),
        _sha256sums_expect("preflight_md_root_sha", files["preflight_md"], root_sha256s, (f"preflight/{PREFLIGHT_MD_NAME}", PREFLIGHT_MD_NAME)),
        _sha256sums_expect("preflight_sha256s_root_sha", files["preflight_sha256s"], root_sha256s, ("preflight/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("preflight_json_preflight_sha", files["preflight_json"], preflight_sha256s, (PREFLIGHT_JSON_NAME, f"./{PREFLIGHT_JSON_NAME}")),
        _sha256sums_expect("preflight_md_preflight_sha", files["preflight_md"], preflight_sha256s, (PREFLIGHT_MD_NAME, f"./{PREFLIGHT_MD_NAME}")),
        _expect("preflight_run_exit_zero", _read_text(files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(
    static_heads: dict[str, str],
    preflight_heads: dict[str, str],
    static_review: dict[str, Any],
    source_preflight: dict[str, Any],
) -> list[dict[str, Any]]:
    static_analysis = _dict(static_review.get("analysis"))
    preflight_analysis = _dict(source_preflight.get("analysis"))
    return [
        _expect("static_heads_dp_fixed", static_heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("preflight_heads_dp_fixed", preflight_heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("static_heads_camp_matches_static_review_analysis", static_heads.get("camp_head"), static_analysis.get("current_camp_head")),
        _expect("preflight_heads_camp_matches_preflight_analysis", preflight_heads.get("camp_head"), preflight_analysis.get("current_camp_head")),
        _expect("static_heads_source_preflight_path", static_heads.get("source_runbook_preflight_artifact"), static_analysis.get("runbook_preflight_artifact_dir")),
    ]


def _source_static_review_contract_checks(static_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(static_review.get("final_decision"))
    summary = _dict(static_review.get("source_preflight_summary"))
    blocked = _dict(static_review.get("blocked_actions"))
    checks = [
        _expect("source_static_review_schema", static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_static_review_failure_class", decision.get("failure_class"), None),
        _expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_plan_authorized", decision.get("evaluation_runbook_plan_authorized"), True),
        _expect("source_static_review_execution_authorized", decision.get("evaluation_runbook_execution_authorized"), False),
        _expect("source_static_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_check_failures", _failed_source_checks(static_review, "review_checks"), []),
        _expect("source_static_review_preflight_check_count", summary.get("check_count"), 218),
        _expect("source_static_review_preflight_step_count", summary.get("runbook_preflight_step_count"), 6),
        _expect("source_static_review_preflight_manifest_count", summary.get("artifact_manifest_requirement_count"), 7),
        _expect("source_static_review_preflight_no_go_count", summary.get("no_go_status_count"), 8),
        _expect("source_static_review_preflight_future_review_count", summary.get("future_review_requirement_count"), 4),
    ]
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_static_review_blocked_{action}", blocked.get(action), False))
    for flag in EXECUTION_FLAGS[:-1]:
        checks.append(_expect(f"source_static_review_decision_{flag}", decision.get(flag), False))
    return checks


def _source_preflight_contract_checks(source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_preflight.get("final_decision"))
    checks = [
        _expect("source_preflight_schema", source_preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA),
        _expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_passed", decision.get("passed"), True),
        _expect("source_preflight_failed_checks", decision.get("failed_checks"), []),
        _expect("source_preflight_failure_class", decision.get("failure_class"), None),
        _expect("source_preflight_authorized_next_work", decision.get("authorized_next_work"), SOURCE_PREFLIGHT_AUTHORIZED_NEXT_WORK),
        _expect("source_preflight_static_review_authorized", decision.get("evaluation_runbook_preflight_static_review_authorized"), True),
        _expect("source_preflight_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_preflight_check_failures", _failed_source_checks(source_preflight, "preflight_checks"), []),
        _expect("source_preflight_step_count", len(_list(source_preflight.get("runbook_preflight"))), 6),
        _expect("source_preflight_manifest_count", len(_list(source_preflight.get("artifact_manifest_requirements"))), 7),
        _expect("source_preflight_no_go_count", len(_list(source_preflight.get("no_go_status"))), 8),
        _expect("source_preflight_future_review_count", len(_list(source_preflight.get("future_review_requirements"))), 4),
    ]
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_preflight_decision_{action}", decision.get(action), False))
    for flag in EXECUTION_FLAGS[:-1]:
        checks.append(_expect(f"source_preflight_decision_{flag}", decision.get(flag), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    expected_pair = (SOURCE_STATIC_REVIEW_STATUS, AUTHORIZED_CURRENT_WORK)
    return [
        _expect("audit_latest_eof_authorizes_runbook_plan", (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target")), expected_pair),
        _expect("status_doc_latest_eof_authorizes_runbook_plan", (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target")), expected_pair),
        _expect("audit_runbook_preflight_static_review_passed", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_passed"), "True"),
        _expect("audit_runbook_plan_authorized", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_plan_authorized"), "True"),
        _expect("audit_runbook_execution_authorized", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _planned_content_checks() -> list[dict[str, Any]]:
    return [
        _expect("runbook_step_names", _names(_runbook_plan()), list(EXPECTED_RUNBOOK_STEPS)),
        _expect("planned_artifact_count", len(_planned_artifacts()), 9),
        _expect("metrics_plan_count", len(_metrics_plan()), 6),
        _expect("decision_criteria_count", len(_decision_criteria_plan()), 6),
        _expect("no_go_names", _names(_no_go_conditions()), list(EXPECTED_NO_GO)),
        _expect("forbidden_action_count", len(_forbidden_actions()), 10),
        _expect("future_review_requirement_count", len(_future_review_requirements()), 4),
    ]


def _source_static_review_summary(static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(static_review.get("final_decision"))
    return {
        "schema_version": static_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(_list(static_review.get("review_checks"))),
    }


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_preflight.get("final_decision"))
    return {
        "schema_version": source_preflight.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "check_count": len(_list(source_preflight.get("preflight_checks"))),
        "runbook_preflight_step_count": len(_list(source_preflight.get("runbook_preflight"))),
        "artifact_manifest_requirement_count": len(_list(source_preflight.get("artifact_manifest_requirements"))),
        "no_go_status_count": len(_list(source_preflight.get("no_go_status"))),
        "future_review_requirement_count": len(_list(source_preflight.get("future_review_requirements"))),
    }


def _runbook_plan() -> list[dict[str, str]]:
    return [
        {"name": name, "status": "planned_read_only_no_execution"}
        for name in EXPECTED_RUNBOOK_STEPS
    ]


def _planned_artifacts() -> list[dict[str, str]]:
    return [
        {"name": "HEADS", "status": "required"},
        {"name": "COMMAND", "status": "required"},
        {"name": "stdout_stderr", "status": "required"},
        {"name": "run_exit", "status": "required"},
        {"name": "SHA256SUMS", "status": "required"},
        {"name": "runbook_plan_json_md_sha256s", "status": "required"},
        {"name": "metrics_manifest_plan", "status": "planned_not_materialized"},
        {"name": "no_go_summary_plan", "status": "planned_not_materialized"},
        {"name": "evidence_matrix_plan", "status": "planned_not_materialized"},
    ]


def _metrics_plan() -> list[dict[str, str]]:
    return [
        {"name": "fixed_dp_candidate_tensor_provenance", "status": "required"},
        {"name": "default_off_shadow_selection_distribution", "status": "planned_shadow_only"},
        {"name": "masked_affine_objective_delta", "status": "planned_nonclaim"},
        {"name": "feasibility_and_fail_closed_counts", "status": "required"},
        {"name": "split_and_seed_zero_overlap", "status": "required"},
        {"name": "uncertainty_or_confidence_interval", "status": "planned_before_any_claim"},
    ]


def _decision_criteria_plan() -> list[dict[str, str]]:
    return [
        {"name": "no_dp_candidate_source_drift", "status": "required"},
        {"name": "no_full36_or_formal_seed_11_12_13", "status": "required"},
        {"name": "no_closed_loop_outcome_input", "status": "required"},
        {"name": "affine_score_and_convex_simplex_master", "status": "required"},
        {"name": "default_off_no_output_effect", "status": "required"},
        {"name": "static_review_before_any_execution_or_claim", "status": "required"},
    ]


def _no_go_conditions() -> list[dict[str, str]]:
    return [
        {"name": name, "required_state": "not_triggered"}
        for name in EXPECTED_NO_GO
    ]


def _forbidden_actions() -> list[dict[str, str]]:
    return [
        {"name": "selector_promotion", "status": "forbidden"},
        {"name": "deployment", "status": "forbidden"},
        {"name": "online_selector_activation", "status": "forbidden"},
        {"name": "dp_code_config_weight_or_checkpoint_change", "status": "forbidden"},
        {"name": "camp_trajectory_generation_or_rewrite", "status": "forbidden"},
        {"name": "reference_blend_guidance_or_postselection", "status": "forbidden"},
        {"name": "closed_loop_outcome_training_input", "status": "forbidden"},
        {"name": "full36_or_formal_seed_11_12_13", "status": "forbidden"},
        {"name": "safety_benefit_or_deployable_checkpoint_claim", "status": "forbidden"},
        {"name": "camp_over_dp_top1_claim", "status": "forbidden"},
    ]


def _future_review_requirements() -> list[dict[str, str]]:
    return [
        {"name": "runbook_plan_static_review", "status": "required_before_execution_planning"},
        {"name": "source_artifact_hash_review", "status": "required"},
        {"name": "fixed_dp_math_boundary_review", "status": "required"},
        {"name": "no_promotion_deployment_or_claim_review", "status": "required"},
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_readiness_evaluation_runbook_plan_ready": bool(passed),
        "evaluation_runbook_plan_static_review_authorized": bool(passed),
        "evaluation_runbook_execution_authorized": False,
        "recommendation": "static_review_this_evaluation_runbook_plan_only",
        "immediate_action": "static_review_promotion_readiness_evaluation_runbook_plan_only",
        "score_expression": SCORE_EXPRESSION,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
        "evaluation_runbook_executed_by_this_gate": False,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "runbook_plan_enabled" in failed_set:
        return "explicit_runbook_plan_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "static_heads_dp_fixed", "preflight_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "source_artifact_sha256_mismatch"
    if any(name.startswith("source_static_review_") for name in failed):
        return "source_static_review_contract_failure"
    if any(name.startswith("source_preflight_") for name in failed):
        return "source_preflight_contract_failure"
    if any(name.startswith("static_heads_") or name.startswith("preflight_heads_") for name in failed):
        return "source_artifact_heads_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "promotion_readiness_evaluation_runbook_plan_failure"


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
        key = key.strip()
        value = value.strip()
        values[key] = value
        values[key.lower()] = value
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
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _compact(value: Any) -> str:
    text = json.dumps(_stable(value), ensure_ascii=True, sort_keys=True)
    return text if len(text) <= 140 else text[:137] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
