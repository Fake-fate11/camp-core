#!/usr/bin/env python3
"""Static review for v14 uncertainty/coverage evidence package construction plan."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_plan_module():
    plan_path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
        "uncertainty_coverage_evidence_package_construction.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan",
        plan_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_PLAN_MODULE = _load_plan_module()
PLAN_MODULE = SOURCE_PLAN_MODULE.PLAN_MODULE

FIXED_DP_HEAD = SOURCE_PLAN_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_PLAN_MODULE.SCORE_EXPRESSION
SOURCE_PLAN_SCHEMA = SOURCE_PLAN_MODULE.SCHEMA_VERSION
SOURCE_PLAN_STATUS = SOURCE_PLAN_MODULE.READY_STATUS
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_package_construction_plan_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_only"
)
SOURCE_PLAN_JSON_NAME = SOURCE_PLAN_MODULE.PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = SOURCE_PLAN_MODULE.PLAN_MD_NAME
REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review.md"
)
PACKAGE_PLAN_ITEMS = SOURCE_PLAN_MODULE.PACKAGE_PLAN_ITEMS
EXPECTED_PLAN_CHECK_COUNT = 186
EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 234
EXPECTED_SOURCE_MATERIALIZATION_CHECK_COUNT = 200
EXPECTED_MANIFEST_COUNT = 5
BLOCKED_ACTIONS = SOURCE_PLAN_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_PLAN_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = SOURCE_PLAN_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence_package_construction_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--evidence_package_construction_plan_json", type=Path, required=True)
    parser.add_argument("--evidence_package_construction_plan_md", type=Path, required=True)
    parser.add_argument("--evidence_package_construction_plan_sha256s", type=Path, required=True)
    parser.add_argument("--plan_script_py", type=Path, required=True)
    parser.add_argument("--plan_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review",
        action="store_true",
        help="Explicit opt-in for static review of the evidence package construction plan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        evidence_package_construction_plan_artifact_dir=args.evidence_package_construction_plan_artifact_dir,
        evidence_package_construction_plan_json=args.evidence_package_construction_plan_json,
        evidence_package_construction_plan_md=args.evidence_package_construction_plan_md,
        evidence_package_construction_plan_sha256s=args.evidence_package_construction_plan_sha256s,
        plan_script_py=args.plan_script_py,
        plan_test_py=args.plan_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    evidence_package_construction_plan_artifact_dir: Path,
    evidence_package_construction_plan_json: Path,
    evidence_package_construction_plan_md: Path,
    evidence_package_construction_plan_sha256s: Path,
    plan_script_py: Path,
    plan_test_py: Path,
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
    artifact_dir = evidence_package_construction_plan_artifact_dir.resolve()
    paths = {
        "evidence_package_construction_plan_json": evidence_package_construction_plan_json.resolve(),
        "evidence_package_construction_plan_md": evidence_package_construction_plan_md.resolve(),
        "evidence_package_construction_plan_sha256s": evidence_package_construction_plan_sha256s.resolve(),
        "plan_script_py": plan_script_py.resolve(),
        "plan_test_py": plan_test_py.resolve(),
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
        "plan_json": artifact_dir / "plan" / SOURCE_PLAN_JSON_NAME,
        "plan_md": artifact_dir / "plan" / SOURCE_PLAN_MD_NAME,
        "plan_sha256s": artifact_dir / "plan" / "SHA256SUMS",
    }

    source_plan = PLAN_MODULE._read_json_dict(paths["evidence_package_construction_plan_json"])
    root_sha256s = PLAN_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    plan_sha256s = PLAN_MODULE._read_sha256sums(paths["evidence_package_construction_plan_sha256s"])
    heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(artifact_files["heads"]))
    script_text = PLAN_MODULE._read_text(paths["plan_script_py"])
    test_text = PLAN_MODULE._read_text(paths["plan_test_py"])
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        PLAN_MODULE._expect("static_review_enabled", enabled, True),
        PLAN_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PLAN_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PLAN_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PLAN_MODULE._check("current_camp_head_is_sha", PLAN_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PLAN_MODULE._check("plan_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(PLAN_MODULE._path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            PLAN_MODULE._expect("plan_json_matches_artifact_layout", paths["evidence_package_construction_plan_json"], artifact_files["plan_json"]),
            PLAN_MODULE._expect("plan_md_matches_artifact_layout", paths["evidence_package_construction_plan_md"], artifact_files["plan_md"]),
            PLAN_MODULE._expect("plan_sha256s_matches_artifact_layout", paths["evidence_package_construction_plan_sha256s"], artifact_files["plan_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, plan_sha256s))
    checks.extend(_heads_checks(heads, source_plan))
    checks.extend(_source_plan_contract_checks(source_plan))
    checks.extend(_source_surface_checks(script_text, test_text))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "read_only": True,
            "source_plan_artifact_dir": str(artifact_dir),
            "source_plan_json": str(paths["evidence_package_construction_plan_json"]),
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
            name: PLAN_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_plan_summary": _source_plan_summary(source_plan),
        "package_plan_summary": _package_plan_summary(source_plan),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    PLAN_MODULE._write_json(output_dir / REVIEW_JSON_NAME, report)
    (output_dir / REVIEW_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    PLAN_MODULE._write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Plan Static Review",
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
        lines.append(f"- {key}: `{PLAN_MODULE._compact(value)}`")
    lines.extend(["", "## Review Checks"])
    for check in report["review_checks"]:
        lines.append(
            f"- [{'x' if check['passed'] else ' '}] {check['name']}: "
            f"observed=`{PLAN_MODULE._compact(check['observed'])}` expected=`{PLAN_MODULE._compact(check['expected'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    plan_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        PLAN_MODULE._sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        PLAN_MODULE._sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        PLAN_MODULE._sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        PLAN_MODULE._sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        PLAN_MODULE._sha256sums_expect("artifact_plan_json_root_sha", artifact_files["plan_json"], root_sha256s, (f"plan/{SOURCE_PLAN_JSON_NAME}", f"./plan/{SOURCE_PLAN_JSON_NAME}", SOURCE_PLAN_JSON_NAME)),
        PLAN_MODULE._sha256sums_expect("artifact_plan_md_root_sha", artifact_files["plan_md"], root_sha256s, (f"plan/{SOURCE_PLAN_MD_NAME}", f"./plan/{SOURCE_PLAN_MD_NAME}", SOURCE_PLAN_MD_NAME)),
        PLAN_MODULE._sha256sums_expect("source_plan_json_plan_sha", artifact_files["plan_json"], plan_sha256s, (SOURCE_PLAN_JSON_NAME, f"./{SOURCE_PLAN_JSON_NAME}")),
        PLAN_MODULE._sha256sums_expect("source_plan_md_plan_sha", artifact_files["plan_md"], plan_sha256s, (SOURCE_PLAN_MD_NAME, f"./{SOURCE_PLAN_MD_NAME}")),
        PLAN_MODULE._expect("artifact_run_exit_zero", PLAN_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = PLAN_MODULE._dict(source_plan.get("analysis"))
    return [
        PLAN_MODULE._expect("artifact_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        PLAN_MODULE._expect("artifact_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        PLAN_MODULE._expect("artifact_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        PLAN_MODULE._expect("artifact_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_plan_contract_checks(source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    source_review = PLAN_MODULE._dict(source_plan.get("source_review_summary"))
    source_materialization = PLAN_MODULE._dict(source_plan.get("source_materialization_summary"))
    manifest_summary = PLAN_MODULE._dict(source_plan.get("manifest_summary"))
    package_plan = [PLAN_MODULE._dict(item) for item in PLAN_MODULE._list(source_plan.get("evidence_package_construction_plan"))]
    checks = [
        PLAN_MODULE._expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        PLAN_MODULE._expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        PLAN_MODULE._expect("source_plan_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_plan_failure_class", decision.get("failure_class"), None),
        PLAN_MODULE._expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("source_plan_ready_flag", decision.get("uncertainty_coverage_evidence_package_construction_plan_ready"), True),
        PLAN_MODULE._expect("source_plan_static_review_authorized", decision.get("uncertainty_coverage_evidence_package_construction_plan_static_review_authorized"), True),
        PLAN_MODULE._expect("source_plan_no_package_constructed", decision.get("evidence_package_constructed_by_this_gate"), False),
        PLAN_MODULE._expect("source_plan_check_count", len(PLAN_MODULE._list(source_plan.get("plan_checks"))), EXPECTED_PLAN_CHECK_COUNT),
        PLAN_MODULE._expect("source_plan_failed_check_count", len(PLAN_MODULE._list(decision.get("failed_checks"))), 0),
        PLAN_MODULE._expect("source_review_check_count", source_review.get("review_check_count"), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        PLAN_MODULE._expect("source_materialization_check_count", source_materialization.get("materialization_check_count"), EXPECTED_SOURCE_MATERIALIZATION_CHECK_COUNT),
        PLAN_MODULE._expect("source_manifest_count", manifest_summary.get("manifest_count"), EXPECTED_MANIFEST_COUNT),
        PLAN_MODULE._expect("source_manifest_all_no_execution", manifest_summary.get("all_no_execution"), True),
        PLAN_MODULE._expect("source_manifest_all_no_claim", manifest_summary.get("all_no_claim"), True),
        PLAN_MODULE._expect("source_package_plan_item_names", [item.get("item_name") for item in package_plan], list(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_item_count", len(package_plan), len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_no_construction", [item.get("package_constructed_by_this_gate") for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_no_execution", [item.get("authorizes_execution") for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_no_claim", [item.get("authorizes_claim") for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
        PLAN_MODULE._expect("source_package_plan_no_promotion", [item.get("authorizes_promotion") for item in package_plan], [False] * len(PACKAGE_PLAN_ITEMS)),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(PLAN_MODULE._expect(f"source_plan_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(PLAN_MODULE._expect(f"source_plan_decision_{flag}", decision.get(flag), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(PLAN_MODULE._expect(f"source_plan_analysis_{flag}", PLAN_MODULE._dict(source_plan.get("analysis")).get(flag), False))
    return checks


def _source_surface_checks(script_text: str, test_text: str) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._check("plan_script_schema_token", "evidence_package_construction_plan_v1" in script_text, "evidence_package_construction_plan_v1", "present"),
        PLAN_MODULE._check("plan_script_static_review_next", "evidence_package_construction_plan_static_review_only" in script_text, "evidence_package_construction_plan_static_review_only", "present"),
        PLAN_MODULE._check("plan_script_no_construction_check", "package_plan_no_construction" in script_text, "package_plan_no_construction", "present"),
        PLAN_MODULE._check("plan_script_no_execution_check", "package_plan_no_execution" in script_text, "package_plan_no_execution", "present"),
        PLAN_MODULE._check("plan_script_no_claim_check", "package_plan_no_claim" in script_text, "package_plan_no_claim", "present"),
        PLAN_MODULE._check("plan_script_source_materialization_leak_check", "source_materialization_decision_" in script_text, "source_materialization_decision_", "present"),
        PLAN_MODULE._check("plan_test_rejects_source_review_leak", "rejects_source_review_leak" in test_text, "rejects_source_review_leak", "present"),
        PLAN_MODULE._check("plan_test_rejects_materialization_leak", "rejects_materialization_leak" in test_text, "rejects_materialization_leak", "present"),
        PLAN_MODULE._check("plan_test_rejects_manifest_drift", "rejects_manifest_drift" in test_text, "rejects_manifest_drift", "present"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._expect("audit_latest_status_is_plan_ready", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        PLAN_MODULE._expect("audit_latest_eof_authorizes_static_review", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("audit_plan_ready_flag", PLAN_MODULE._latest_value(v14_text, "uncertainty_coverage_evidence_package_construction_plan_ready"), "True"),
        PLAN_MODULE._expect("audit_static_review_authorized_flag", PLAN_MODULE._latest_value(v14_text, "uncertainty_coverage_evidence_package_construction_plan_static_review_authorized"), "True"),
        PLAN_MODULE._expect("audit_no_package_constructed", PLAN_MODULE._latest_value(v14_text, "evidence_package_constructed_by_this_gate"), "False"),
        PLAN_MODULE._expect("audit_selector_promotion_false", PLAN_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        PLAN_MODULE._expect("audit_deployment_false", PLAN_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        PLAN_MODULE._expect("audit_safety_claim_false", PLAN_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        PLAN_MODULE._expect("audit_camp_over_dp_claim_false", PLAN_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        PLAN_MODULE._expect("status_doc_latest_status_is_plan_ready", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        PLAN_MODULE._expect("status_doc_latest_eof_authorizes_static_review", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._check("status_doc_mentions_static_review_next", AUTHORIZED_CURRENT_WORK in status_text, AUTHORIZED_CURRENT_WORK, "present"),
    ]


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_check_count": len(PLAN_MODULE._list(source_plan.get("plan_checks"))),
    }


def _package_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    package_plan = [PLAN_MODULE._dict(item) for item in PLAN_MODULE._list(source_plan.get("evidence_package_construction_plan"))]
    return {
        "package_plan_item_count": len(package_plan),
        "package_plan_items": [item.get("item_name") for item in package_plan],
        "all_no_construction": all(item.get("package_constructed_by_this_gate") is False for item in package_plan),
        "all_no_execution": all(item.get("authorizes_execution") is False for item in package_plan),
        "all_no_claim": all(item.get("authorizes_claim") is False for item in package_plan),
        "all_no_promotion": all(item.get("authorizes_promotion") is False for item in package_plan),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_uncertainty_coverage_evidence_package_construction_plan_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "plan_")) for name in failed):
        failure_class = "source_evidence_package_construction_plan_static_review_contract_failure"
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
        "uncertainty_coverage_evidence_package_construction_plan_static_review_passed": passed,
        "uncertainty_coverage_evidence_package_construction_authorized": passed,
        "evidence_package_construction_authorized": passed,
        "evidence_package_constructed_by_this_gate": False,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": SCORE_EXPRESSION,
        "recommendation": "construct_uncertainty_coverage_evidence_package_only" if passed else "repair_contract_before_rerun",
        "immediate_action": "evidence_package_construction_only" if passed else "inspect_failed_checks",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
