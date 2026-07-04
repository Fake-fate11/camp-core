#!/usr/bin/env python3
"""Static review for the v14 promotion-readiness runbook execution preflight artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_PREFLIGHT_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_execution_preflight_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_execution_preflight_static_review_v1"
)
SOURCE_PREFLIGHT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_only"
)
RERUN_DECISION_NEXT_WORK = (
    "user_decision_required_before_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_execution_preflight_static_review_contract_fix_or_rerun"
)

PREFLIGHT_JSON_NAME = "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.json"
PREFLIGHT_MD_NAME = "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.md"
REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review.md"
)

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
EXPECTED_PREFLIGHT_STEPS = (
    "source_artifact_inventory",
    "fixed_dp_candidate_tensor_boundary",
    "split_seed_zero_overlap_boundary",
    "default_off_shadow_selector_no_output_effect_boundary",
    "metric_uncertainty_and_no_claim_boundary",
    "execution_command_dry_run_boundary",
    "claim_promotion_deployment_stop_boundary",
)
EXPECTED_MANIFEST_REQUIREMENTS = (
    "HEADS",
    "COMMAND",
    "stdout_stderr",
    "run_exit",
    "SHA256SUMS",
    "source_static_review_json_md_sha256s",
    "source_plan_json_md_sha256s",
)
EXPECTED_NO_GO = (
    "dp_head_drift",
    "camp_trajectory_generation_or_modification",
    "closed_loop_outcome_input",
    "full36_or_formal_seed_11_12_13",
    "non_affine_score",
    "non_simplex_or_nonconvex_master",
    "promotion_deployment_online_selector_or_claim_bundled",
    "safety_or_camp_over_dp_claim_bundled",
)
EXPECTED_FUTURE_REQUIREMENTS = (
    "runbook_execution_preflight_static_review",
    "source_artifact_hash_review",
    "authorization_boundary_review",
    "fixed_dp_math_boundary_review",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runbook_execution_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--runbook_execution_preflight_json", type=Path, required=True)
    parser.add_argument("--runbook_execution_preflight_md", type=Path, required=True)
    parser.add_argument("--runbook_execution_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--preflight_script_py", type=Path, required=True)
    parser.add_argument("--preflight_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review",
        action="store_true",
        help="Explicit opt-in for static review of the runbook execution preflight artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runbook_execution_preflight_artifact_dir=args.runbook_execution_preflight_artifact_dir,
        runbook_execution_preflight_json=args.runbook_execution_preflight_json,
        runbook_execution_preflight_md=args.runbook_execution_preflight_md,
        runbook_execution_preflight_sha256s=args.runbook_execution_preflight_sha256s,
        preflight_script_py=args.preflight_script_py,
        preflight_test_py=args.preflight_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runbook_execution_preflight_artifact_dir: Path,
    runbook_execution_preflight_json: Path,
    runbook_execution_preflight_md: Path,
    runbook_execution_preflight_sha256s: Path,
    preflight_script_py: Path,
    preflight_test_py: Path,
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
    artifact_dir = runbook_execution_preflight_artifact_dir.resolve()
    paths = {
        "runbook_execution_preflight_json": runbook_execution_preflight_json.resolve(),
        "runbook_execution_preflight_md": runbook_execution_preflight_md.resolve(),
        "runbook_execution_preflight_sha256s": runbook_execution_preflight_sha256s.resolve(),
        "preflight_script_py": preflight_script_py.resolve(),
        "preflight_test_py": preflight_test_py.resolve(),
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
        "preflight_json": artifact_dir / "preflight" / PREFLIGHT_JSON_NAME,
        "preflight_md": artifact_dir / "preflight" / PREFLIGHT_MD_NAME,
        "preflight_sha256s": artifact_dir / "preflight" / "SHA256SUMS",
    }
    source_preflight = _read_json_dict(paths["runbook_execution_preflight_json"])
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    preflight_sha256s = _read_sha256sums(paths["runbook_execution_preflight_sha256s"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    script_text = _read_text(paths["preflight_script_py"])
    test_text = _read_text(paths["preflight_test_py"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("static_review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("runbook_execution_preflight_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(_path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("preflight_json_matches_artifact_layout", paths["runbook_execution_preflight_json"], artifact_files["preflight_json"]),
            _expect("preflight_md_matches_artifact_layout", paths["runbook_execution_preflight_md"], artifact_files["preflight_md"]),
            _expect("preflight_sha256s_matches_artifact_layout", paths["runbook_execution_preflight_sha256s"], artifact_files["preflight_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, preflight_sha256s))
    checks.extend(_heads_checks(heads, source_preflight))
    checks.extend(_source_preflight_contract_checks(source_preflight))
    checks.extend(_source_surface_checks(script_text, test_text))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "read_only": True,
            "runbook_execution_preflight_artifact_dir": str(artifact_dir),
            "runbook_execution_preflight_json": str(paths["runbook_execution_preflight_json"]),
            "runbook_execution_preflight_md": str(paths["runbook_execution_preflight_md"]),
            "runbook_execution_preflight_sha256s": str(paths["runbook_execution_preflight_sha256s"]),
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
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
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
        "# Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review",
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
        "## Source Preflight Summary",
    ]
    for key, value in report["source_preflight_summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks"])
    for check in report["review_checks"]:
        status = "pass" if check["passed"] else "fail"
        lines.append(
            f"- {status} `{check['name']}` observed=`{_compact(check['observed'])}` expected=`{_compact(check['expected'])}`"
        )
    return "\n".join(lines) + "\n"


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    preflight_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("artifact_preflight_json_root_sha", artifact_files["preflight_json"], root_sha256s, (f"preflight/{PREFLIGHT_JSON_NAME}", f"./preflight/{PREFLIGHT_JSON_NAME}", PREFLIGHT_JSON_NAME)),
        _sha256sums_expect("artifact_preflight_md_root_sha", artifact_files["preflight_md"], root_sha256s, (f"preflight/{PREFLIGHT_MD_NAME}", f"./preflight/{PREFLIGHT_MD_NAME}", PREFLIGHT_MD_NAME)),
        _sha256sums_expect("artifact_preflight_sha256s_root_sha", artifact_files["preflight_sha256s"], root_sha256s, ("preflight/SHA256SUMS", "./preflight/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("artifact_preflight_json_preflight_sha", artifact_files["preflight_json"], preflight_sha256s, (PREFLIGHT_JSON_NAME, f"./{PREFLIGHT_JSON_NAME}")),
        _sha256sums_expect("artifact_preflight_md_preflight_sha", artifact_files["preflight_md"], preflight_sha256s, (PREFLIGHT_MD_NAME, f"./{PREFLIGHT_MD_NAME}")),
        _expect("artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = _dict(source_preflight.get("analysis"))
    return [
        _expect("artifact_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("artifact_heads_camp_matches_source_analysis", heads.get("camp_head"), analysis.get("current_camp_head")),
        _expect("artifact_heads_origin_matches_source_analysis", heads.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
        _expect("artifact_heads_source_static_review_path", heads.get("source_runbook_plan_static_review_artifact"), analysis.get("runbook_plan_static_review_artifact_dir")),
        _expect("artifact_heads_source_plan_path", heads.get("source_runbook_plan_artifact"), analysis.get("source_runbook_plan_artifact_dir")),
    ]


def _source_preflight_contract_checks(source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_preflight.get("final_decision"))
    analysis = _dict(source_preflight.get("analysis"))
    blocked = _dict(source_preflight.get("blocked_actions"))
    checks = [
        _expect("source_preflight_schema", source_preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA),
        _expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_passed", decision.get("passed"), True),
        _expect("source_preflight_failed_checks", decision.get("failed_checks"), []),
        _expect("source_preflight_failure_class", decision.get("failure_class"), None),
        _expect("source_preflight_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_preflight_static_review_authorized", decision.get("evaluation_runbook_execution_preflight_static_review_authorized"), True),
        _expect("source_preflight_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_preflight_preflight_only", analysis.get("preflight_only"), True),
        _expect("source_preflight_read_only", analysis.get("read_only"), True),
        _expect("source_preflight_steps", _names(source_preflight.get("runbook_execution_preflight")), list(EXPECTED_PREFLIGHT_STEPS)),
        _expect("source_preflight_manifest_requirements", _names(source_preflight.get("artifact_manifest_requirements")), list(EXPECTED_MANIFEST_REQUIREMENTS)),
        _expect("source_preflight_no_go_names", _names(source_preflight.get("no_go_status")), list(EXPECTED_NO_GO)),
        _expect("source_preflight_no_go_triggered", [item.get("triggered") for item in _list(source_preflight.get("no_go_status"))], [False] * len(EXPECTED_NO_GO)),
        _expect("source_preflight_future_review_requirements", _names(source_preflight.get("future_review_requirements")), list(EXPECTED_FUTURE_REQUIREMENTS)),
        _expect("source_preflight_check_failures", _failed_source_checks(source_preflight, "preflight_checks"), []),
        _expect("source_static_review_check_count", _dict(source_preflight.get("source_static_review_summary")).get("review_check_count"), 145),
        _expect("source_plan_check_count", _dict(source_preflight.get("source_runbook_plan_summary")).get("plan_check_count"), 186),
        _expect("source_plan_runbook_step_count", _dict(source_preflight.get("source_runbook_plan_summary")).get("runbook_step_count"), 7),
        _expect("source_plan_artifact_count", _dict(source_preflight.get("source_runbook_plan_summary")).get("artifact_count"), 9),
        _expect("source_plan_metrics_count", _dict(source_preflight.get("source_runbook_plan_summary")).get("metrics_count"), 6),
        _expect("source_plan_decision_criteria_count", _dict(source_preflight.get("source_runbook_plan_summary")).get("decision_criteria_count"), 6),
        _expect("source_plan_no_go_condition_count", _dict(source_preflight.get("source_runbook_plan_summary")).get("no_go_condition_count"), 8),
        _expect("source_plan_forbidden_action_count", _dict(source_preflight.get("source_runbook_plan_summary")).get("forbidden_action_count"), 10),
        _expect("source_plan_future_review_count", _dict(source_preflight.get("source_runbook_plan_summary")).get("future_review_count"), 4),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        observed = analysis.get(flag)
        if flag == "evaluation_runbook_execution" and flag not in analysis:
            observed = False
        checks.append(_expect(f"source_preflight_analysis_{flag}", observed, False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_preflight_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_preflight_blocked_{action}", blocked.get(action), False))
    for flag in EXECUTION_FLAGS:
        checks.append(_expect(f"source_preflight_decision_{flag}", decision.get(flag), False))
    return checks


def _source_surface_checks(script: str, test: str) -> list[dict[str, Any]]:
    return [
        _contains("source_surface_script_schema", script, "promotion_readiness_evaluation_runbook_execution_preflight_v1"),
        _contains("source_surface_script_static_review_next", script, "runbook_execution_preflight_static_review_only"),
        _contains("source_surface_script_future_static_review_requirement", script, "runbook_execution_preflight_static_review"),
        _contains("source_surface_script_optional_review_sha256s_root", script, "_sha256sums_expect_optional"),
        _contains("source_surface_script_rerun_eof_boundary", script, "RERUN_DECISION_NEXT_WORK"),
        _contains("source_surface_script_case_insensitive_heads", script, "key.lower()"),
        _contains("source_surface_script_affine_score", script, SCORE_EXPRESSION),
        _contains("source_surface_script_blocks_promotion", script, '"promotion_executed": False'),
        _contains("source_surface_script_blocks_deployment", script, '"deployment_executed": False'),
        _contains("source_surface_script_blocks_training", script, '"training_execution": False'),
        _contains("source_surface_script_blocks_replay", script, '"replay_execution": False'),
        _contains("source_surface_script_blocks_candidate_generation", script, '"candidate_generation": False'),
        _contains("source_surface_script_blocks_dp_modification", script, '"dp_modification": False'),
        _contains("source_surface_script_blocks_evaluation_execution", script, '"evaluation_runbook_execution_authorized": False'),
        _contains("source_surface_test_pass_case", test, "test_promotion_readiness_evaluation_runbook_execution_preflight_passes"),
        _contains("source_surface_test_requires_enable", test, "test_promotion_readiness_evaluation_runbook_execution_preflight_requires_enable"),
        _contains("source_surface_test_rejects_wrong_eof", test, "test_promotion_readiness_evaluation_runbook_execution_preflight_rejects_wrong_eof"),
        _contains("source_surface_test_accepts_uppercase_dp_head", test, "test_promotion_readiness_evaluation_runbook_execution_preflight_accepts_uppercase_dp_head"),
        _contains("source_surface_test_accepts_omitted_nested_sha256s", test, "accepts_static_review_root_without_nested_sha256s"),
        _contains("source_surface_test_accepts_missing_execution_analysis", test, "accepts_missing_static_review_execution_analysis_key"),
        _contains("source_surface_test_rejects_execution_analysis_true", test, "rejects_static_review_execution_analysis_true"),
        _contains("source_surface_test_accepts_audited_rerun_eof", test, "accepts_audited_rerun_eof_state"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    expected_pairs = (
        (SOURCE_PREFLIGHT_STATUS, AUTHORIZED_CURRENT_WORK),
        (REJECT_STATUS, RERUN_DECISION_NEXT_WORK),
    )
    preflight_completion_markers = {
        "ready": _latest_value(
            v14_text,
            "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_ready",
        ),
        "passed": _latest_value(
            v14_text,
            "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_passed",
        ),
    }
    return [
        _expect_in("audit_latest_eof_authorizes_static_review", (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target")), expected_pairs),
        _expect_in("status_doc_latest_eof_authorizes_static_review", (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target")), expected_pairs),
        _check(
            "audit_runbook_execution_preflight_ready_or_passed",
            any(value == "True" for value in preflight_completion_markers.values()),
            preflight_completion_markers,
            "preflight_ready=True or preflight_passed=True",
        ),
        _expect("audit_runbook_execution_preflight_static_review_authorized", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_authorized"), "True"),
        _expect("audit_runtime_execution_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_preflight.get("final_decision"))
    return {
        "schema_version": source_preflight.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "check_count": len(_list(source_preflight.get("preflight_checks"))),
        "runbook_execution_preflight_step_count": len(_list(source_preflight.get("runbook_execution_preflight"))),
        "artifact_manifest_requirement_count": len(_list(source_preflight.get("artifact_manifest_requirements"))),
        "no_go_status_count": len(_list(source_preflight.get("no_go_status"))),
        "future_review_requirement_count": len(_list(source_preflight.get("future_review_requirements"))),
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
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_passed": bool(passed),
        "evaluation_runbook_execution_authorized": bool(passed),
        "recommendation": "execute_read_only_promotion_readiness_evaluation_runbook_only",
        "immediate_action": "execute_promotion_readiness_evaluation_runbook_only",
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
    if "static_review_enabled" in failed_set:
        return "explicit_runbook_execution_preflight_static_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "artifact_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "runbook_execution_preflight_artifact_sha256_mismatch"
    if any(name.startswith("source_surface_") for name in failed):
        return "source_surface_contract_failure"
    if any(name.startswith("source_preflight_") or name.startswith("source_plan_") or name.startswith("source_static_review_") for name in failed):
        return "source_preflight_contract_failure"
    if any(name.startswith("artifact_heads_") for name in failed):
        return "artifact_heads_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "promotion_readiness_evaluation_runbook_execution_preflight_static_review_failure"


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


def _expect_in(name: str, observed: Any, expected_options: tuple[Any, ...]) -> dict[str, Any]:
    return _check(name, observed in expected_options, observed, expected_options)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "observed": _stable(observed), "expected": _stable(expected)}


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


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
