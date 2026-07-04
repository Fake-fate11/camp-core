#!/usr/bin/env python3
"""Static review for the v14 uncertainty/coverage review plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_PLAN_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_review_plan_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_review_plan_static_review_v1"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_only"
)
PLAN_JSON_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_plan.json"
PLAN_MD_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_plan.md"
REVIEW_JSON_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review.json"
REVIEW_MD_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review.md"

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
EXPECTED_PLAN_ITEMS = (
    "score_margin_uncertainty_surface",
    "coverage_slice_matrix",
    "candidate_tensor_support_coverage",
    "atom_contribution_stability",
    "default_off_fail_closed_uncertainty_boundary",
    "claim_boundary",
    "promotion_thresholds_tbd",
)
EXPECTED_SOURCE = {
    "plan_check_count": 124,
    "plan_item_count": 7,
    "source_static_review_check_count": 134,
    "source_plan_check_count": 128,
    "source_followup_item_count": 7,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uncertainty_coverage_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--uncertainty_coverage_plan_json", type=Path, required=True)
    parser.add_argument("--uncertainty_coverage_plan_md", type=Path, required=True)
    parser.add_argument("--uncertainty_coverage_plan_sha256s", type=Path, required=True)
    parser.add_argument("--uncertainty_coverage_plan_script_py", type=Path, required=True)
    parser.add_argument("--uncertainty_coverage_plan_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review",
        action="store_true",
        help="Explicit opt-in for static review of the uncertainty/coverage review plan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        uncertainty_coverage_plan_artifact_dir=args.uncertainty_coverage_plan_artifact_dir,
        uncertainty_coverage_plan_json=args.uncertainty_coverage_plan_json,
        uncertainty_coverage_plan_md=args.uncertainty_coverage_plan_md,
        uncertainty_coverage_plan_sha256s=args.uncertainty_coverage_plan_sha256s,
        uncertainty_coverage_plan_script_py=args.uncertainty_coverage_plan_script_py,
        uncertainty_coverage_plan_test_py=args.uncertainty_coverage_plan_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    uncertainty_coverage_plan_artifact_dir: Path,
    uncertainty_coverage_plan_json: Path,
    uncertainty_coverage_plan_md: Path,
    uncertainty_coverage_plan_sha256s: Path,
    uncertainty_coverage_plan_script_py: Path,
    uncertainty_coverage_plan_test_py: Path,
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
    artifact_dir = uncertainty_coverage_plan_artifact_dir.resolve()
    paths = {
        "uncertainty_coverage_plan_json": uncertainty_coverage_plan_json.resolve(),
        "uncertainty_coverage_plan_md": uncertainty_coverage_plan_md.resolve(),
        "uncertainty_coverage_plan_sha256s": uncertainty_coverage_plan_sha256s.resolve(),
        "uncertainty_coverage_plan_script_py": uncertainty_coverage_plan_script_py.resolve(),
        "uncertainty_coverage_plan_test_py": uncertainty_coverage_plan_test_py.resolve(),
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
        "plan_json": artifact_dir / "plan" / PLAN_JSON_NAME,
        "plan_md": artifact_dir / "plan" / PLAN_MD_NAME,
        "plan_sha256s": artifact_dir / "plan" / "SHA256SUMS",
    }
    source_plan = _read_json_dict(paths["uncertainty_coverage_plan_json"])
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    plan_sha256s = _read_sha256sums(paths["uncertainty_coverage_plan_sha256s"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    script_text = _read_text(paths["uncertainty_coverage_plan_script_py"])
    test_text = _read_text(paths["uncertainty_coverage_plan_test_py"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("static_review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("uncertainty_coverage_plan_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(_path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("uncertainty_coverage_plan_json_matches_artifact_layout", paths["uncertainty_coverage_plan_json"], artifact_files["plan_json"]),
            _expect("uncertainty_coverage_plan_md_matches_artifact_layout", paths["uncertainty_coverage_plan_md"], artifact_files["plan_md"]),
            _expect("uncertainty_coverage_plan_sha256s_matches_artifact_layout", paths["uncertainty_coverage_plan_sha256s"], artifact_files["plan_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, plan_sha256s))
    checks.extend(_heads_checks(heads, source_plan))
    checks.extend(_source_plan_contract_checks(source_plan))
    checks.extend(_source_surface_checks(script_text, test_text))
    checks.extend(_audit_checks(v14_text, status_text, artifact_dir))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "read_only": True,
            "uncertainty_coverage_review_plan_static_review_only": True,
            "uncertainty_coverage_plan_artifact_dir": str(artifact_dir),
            "uncertainty_coverage_plan_json": str(paths["uncertainty_coverage_plan_json"]),
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
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_plan_summary": _source_summary(source_plan),
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
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan Static Review",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Source Plan Summary",
    ]
    for key, value in report["source_plan_summary"].items():
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
    plan_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("artifact_plan_json_root_sha", artifact_files["plan_json"], root_sha256s, (f"plan/{PLAN_JSON_NAME}", f"./plan/{PLAN_JSON_NAME}", PLAN_JSON_NAME)),
        _sha256sums_expect("artifact_plan_md_root_sha", artifact_files["plan_md"], root_sha256s, (f"plan/{PLAN_MD_NAME}", f"./plan/{PLAN_MD_NAME}", PLAN_MD_NAME)),
        _sha256sums_expect("artifact_plan_sha256s_root_sha", artifact_files["plan_sha256s"], root_sha256s, ("plan/SHA256SUMS", "./plan/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("artifact_plan_json_plan_sha", artifact_files["plan_json"], plan_sha256s, (PLAN_JSON_NAME, f"./{PLAN_JSON_NAME}")),
        _sha256sums_expect("artifact_plan_md_plan_sha", artifact_files["plan_md"], plan_sha256s, (PLAN_MD_NAME, f"./{PLAN_MD_NAME}")),
        _expect("artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = _dict(source_plan.get("analysis"))
    return [
        _expect("artifact_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("artifact_heads_camp_matches_source_analysis", heads.get("camp_head"), analysis.get("current_camp_head")),
        _expect("artifact_heads_origin_matches_source_analysis", heads.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_plan_contract_checks(source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_plan.get("final_decision"))
    analysis = _dict(source_plan.get("analysis"))
    blocked = _dict(source_plan.get("blocked_actions"))
    summary = _dict(source_plan.get("source_review_summary"))
    plan_items = _list(source_plan.get("uncertainty_coverage_review_plan"))
    checks = [
        _expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        _expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks", decision.get("failed_checks"), []),
        _expect("source_plan_failure_class", decision.get("failure_class"), None),
        _expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_plan_static_review_authorized", decision.get("uncertainty_coverage_review_plan_static_review_authorized"), True),
        _expect("source_plan_no_direct_promotion", decision.get("direct_promotion_recommendation"), False),
        _expect("source_plan_no_promotion_plan_authorized", decision.get("promotion_decision_plan_authorized_next"), False),
        _expect("source_plan_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_plan_plan_only", analysis.get("plan_only"), True),
        _expect("source_plan_read_only", analysis.get("read_only"), True),
        _expect("source_plan_check_failures", _failed_source_checks(source_plan, "plan_checks"), []),
        _expect("source_plan_check_count", len(_list(source_plan.get("plan_checks"))), EXPECTED_SOURCE["plan_check_count"]),
        _expect("source_plan_item_names", [item.get("name") for item in plan_items], list(EXPECTED_PLAN_ITEMS)),
        _expect("source_plan_item_count", len(plan_items), EXPECTED_SOURCE["plan_item_count"]),
        _expect("source_plan_items_no_execution", [item.get("authorizes_execution") for item in plan_items], [False] * EXPECTED_SOURCE["plan_item_count"]),
        _expect("source_plan_items_no_claim", [item.get("authorizes_claim") for item in plan_items], [False] * EXPECTED_SOURCE["plan_item_count"]),
        _expect("source_plan_source_static_review_check_count", summary.get("review_check_count"), EXPECTED_SOURCE["source_static_review_check_count"]),
        _expect("source_plan_source_plan_check_count", summary.get("source_plan_check_count"), EXPECTED_SOURCE["source_plan_check_count"]),
        _expect("source_plan_source_followup_item_count", summary.get("source_followup_item_count"), EXPECTED_SOURCE["source_followup_item_count"]),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_plan_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_plan_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_plan_blocked_{action}", blocked.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_plan_decision_{flag}", decision.get(flag), False))
    return checks


def _source_surface_checks(script: str, test: str) -> list[dict[str, Any]]:
    return [
        _contains("source_surface_script_schema", script, "uncertainty_coverage_review_plan_v1"),
        _contains("source_surface_script_authorized_next", script, "uncertainty_coverage_review_plan_static_review_only"),
        _contains("source_surface_script_static_review_action", script, "static_review_uncertainty_coverage_review_plan_only"),
        _contains("source_surface_script_blocks_training", script, '"training_execution": False'),
        _contains("source_surface_script_blocks_replay", script, '"replay_execution": False'),
        _contains("source_surface_script_blocks_candidate_generation", script, '"candidate_generation": False'),
        _contains("source_surface_script_blocks_claim", script, '"safety_or_camp_over_dp_claim": False'),
        _contains("source_surface_script_score_margin_item", script, "score_margin_uncertainty_surface"),
        _contains("source_surface_test_pass_case", test, "test_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_passes"),
        _contains("source_surface_test_requires_enable", test, "test_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_requires_enable"),
        _contains("source_surface_test_rejects_wrong_eof", test, "test_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_rejects_wrong_eof"),
        _contains("source_surface_test_rejects_source_leak", test, "test_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_rejects_source_leak"),
    ]


def _audit_checks(v14_text: str, status_text: str, artifact_dir: Path) -> list[dict[str, Any]]:
    expected_pair = (SOURCE_PLAN_STATUS, AUTHORIZED_CURRENT_WORK)
    return [
        _expect("audit_latest_eof_authorizes_static_review", (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target")), expected_pair),
        _expect("status_doc_latest_eof_authorizes_static_review", (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target")), expected_pair),
        _expect("audit_uncertainty_coverage_plan_artifact_path", _latest_value(v14_text, "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_artifact"), str(artifact_dir)),
        _expect("audit_uncertainty_coverage_plan_ready", _latest_value(v14_text, "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_ready"), "True"),
        _expect("audit_static_review_authorized", _latest_value(v14_text, "uncertainty_coverage_review_plan_static_review_authorized"), "True"),
        _expect("audit_direct_promotion_recommendation", _latest_value(v14_text, "direct_promotion_recommendation"), "False"),
        _expect("audit_promotion_decision_plan_authorized_next", _latest_value(v14_text, "promotion_decision_plan_authorized_next"), "False"),
        _expect("audit_runtime_execution_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _source_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_check_count": len(_list(source_plan.get("plan_checks"))),
        "plan_item_count": len(_list(source_plan.get("uncertainty_coverage_review_plan"))),
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
        "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_passed": bool(passed),
        "uncertainty_coverage_review_preflight_plan_authorized": bool(passed),
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "recommendation": "plan_read_only_uncertainty_coverage_review_preflight_only",
        "immediate_action": "plan_uncertainty_coverage_review_preflight_only",
        "score_expression": SCORE_EXPRESSION,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "static_review_enabled" in failed_set:
        return "explicit_uncertainty_coverage_plan_static_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "artifact_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "uncertainty_coverage_plan_artifact_sha256_mismatch"
    if any(name.startswith("source_plan") for name in failed):
        return "source_uncertainty_coverage_plan_contract_failure"
    return "promotion_readiness_uncertainty_coverage_plan_static_review_failure"


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
