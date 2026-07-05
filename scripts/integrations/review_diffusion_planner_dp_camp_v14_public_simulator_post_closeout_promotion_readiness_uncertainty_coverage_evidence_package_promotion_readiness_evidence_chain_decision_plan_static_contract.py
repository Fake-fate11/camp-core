#!/usr/bin/env python3
"""Static review for the v14 promotion-readiness evidence-chain decision plan."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_plan_module():
    plan_path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
        "uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_plan",
        plan_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
BASE_MODULE = PLAN_MODULE.BASE_MODULE

FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PLAN_MODULE.SCORE_EXPRESSION
SOURCE_PLAN_SCHEMA = PLAN_MODULE.SCHEMA_VERSION
SOURCE_PLAN_STATUS = PLAN_MODULE.READY_STATUS
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_plan_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_plan_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_plan_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_only"
)
SOURCE_PLAN_JSON_NAME = PLAN_MODULE.PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = PLAN_MODULE.PLAN_MD_NAME
REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_plan_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_plan_static_review.md"
)

EXPECTED_PLAN_CHECK_COUNT = 125
EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 132
EXPECTED_SOURCE_BOUNDARY_PLAN_CHECK_COUNT = 124
EXPECTED_SOURCE_BOUNDARY_ITEM_COUNT = 5
EXPECTED_DECISION_ITEM_COUNT = 6
BLOCKED_ACTIONS = PLAN_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = PLAN_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = PLAN_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--decision_plan_json", type=Path, required=True)
    parser.add_argument("--decision_plan_md", type=Path, required=True)
    parser.add_argument("--decision_plan_sha256s", type=Path, required=True)
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
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_plan_static_review",
        action="store_true",
        help="Explicit opt-in for static review of the promotion-readiness evidence-chain decision plan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        decision_plan_artifact_dir=args.decision_plan_artifact_dir,
        decision_plan_json=args.decision_plan_json,
        decision_plan_md=args.decision_plan_md,
        decision_plan_sha256s=args.decision_plan_sha256s,
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
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_plan_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    decision_plan_artifact_dir: Path,
    decision_plan_json: Path,
    decision_plan_md: Path,
    decision_plan_sha256s: Path,
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
    artifact_dir = decision_plan_artifact_dir.resolve()
    paths = {
        "decision_plan_json": decision_plan_json.resolve(),
        "decision_plan_md": decision_plan_md.resolve(),
        "decision_plan_sha256s": decision_plan_sha256s.resolve(),
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
    source_plan = BASE_MODULE._read_json_dict(paths["decision_plan_json"])
    root_sha256s = BASE_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    plan_sha256s = BASE_MODULE._read_sha256sums(paths["decision_plan_sha256s"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(artifact_files["heads"]))
    script_text = BASE_MODULE._read_text(paths["plan_script_py"])
    test_text = BASE_MODULE._read_text(paths["plan_test_py"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        BASE_MODULE._expect("static_review_enabled", enabled, True),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        BASE_MODULE._check("current_camp_head_is_sha", BASE_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        BASE_MODULE._check("decision_plan_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(BASE_MODULE._path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(BASE_MODULE._path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            BASE_MODULE._expect("plan_json_matches_artifact_layout", paths["decision_plan_json"], artifact_files["plan_json"]),
            BASE_MODULE._expect("plan_md_matches_artifact_layout", paths["decision_plan_md"], artifact_files["plan_md"]),
            BASE_MODULE._expect("plan_sha256s_matches_artifact_layout", paths["decision_plan_sha256s"], artifact_files["plan_sha256s"]),
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
            "user_authorized_future_promotion_deployment_online_selector_and_claim_gates": True,
            "source_decision_plan_artifact_dir": str(artifact_dir),
            "source_decision_plan_json": str(paths["decision_plan_json"]),
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
        "source_plan_summary": _source_plan_summary(source_plan),
        "evidence_chain_decision_plan_summary": _evidence_chain_decision_plan_summary(source_plan),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    BASE_MODULE._write_json(output_dir / REVIEW_JSON_NAME, report)
    (output_dir / REVIEW_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    BASE_MODULE._write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Evidence-Chain Decision Plan Static Review",
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
        lines.append(f"- {key}: `{BASE_MODULE._compact(value)}`")
    lines.extend(["", "## Review Checks"])
    for check in report["review_checks"]:
        lines.append(
            f"- [{'x' if check['passed'] else ' '}] {check['name']}: "
            f"observed=`{BASE_MODULE._compact(check['observed'])}` expected=`{BASE_MODULE._compact(check['expected'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    plan_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        BASE_MODULE._sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        BASE_MODULE._sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        BASE_MODULE._sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        BASE_MODULE._sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        BASE_MODULE._sha256sums_expect("artifact_plan_json_root_sha", artifact_files["plan_json"], root_sha256s, (f"plan/{SOURCE_PLAN_JSON_NAME}", f"./plan/{SOURCE_PLAN_JSON_NAME}", SOURCE_PLAN_JSON_NAME)),
        BASE_MODULE._sha256sums_expect("artifact_plan_md_root_sha", artifact_files["plan_md"], root_sha256s, (f"plan/{SOURCE_PLAN_MD_NAME}", f"./plan/{SOURCE_PLAN_MD_NAME}", SOURCE_PLAN_MD_NAME)),
        BASE_MODULE._sha256sums_expect("source_plan_json_plan_sha", artifact_files["plan_json"], plan_sha256s, (SOURCE_PLAN_JSON_NAME, f"./{SOURCE_PLAN_JSON_NAME}")),
        BASE_MODULE._sha256sums_expect("source_plan_md_plan_sha", artifact_files["plan_md"], plan_sha256s, (SOURCE_PLAN_MD_NAME, f"./{SOURCE_PLAN_MD_NAME}")),
        BASE_MODULE._expect("artifact_run_exit_zero", BASE_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = BASE_MODULE._dict(source_plan.get("analysis"))
    return [
        BASE_MODULE._expect("artifact_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("artifact_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        BASE_MODULE._expect("artifact_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        BASE_MODULE._expect("artifact_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_plan_contract_checks(source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_plan.get("final_decision"))
    analysis = BASE_MODULE._dict(source_plan.get("analysis"))
    source_review = BASE_MODULE._dict(source_plan.get("source_static_review_summary"))
    boundary_summary = BASE_MODULE._dict(source_plan.get("boundary_plan_summary"))
    evidence_plan = BASE_MODULE._list(source_plan.get("evidence_chain_decision_plan"))
    checks = [
        BASE_MODULE._expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        BASE_MODULE._expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        BASE_MODULE._expect("source_plan_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_plan_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_plan_ready", decision.get("promotion_readiness_evidence_chain_decision_plan_ready"), True),
        BASE_MODULE._expect("source_plan_static_review_authorized", decision.get("promotion_readiness_evidence_chain_decision_static_review_authorized"), True),
        BASE_MODULE._expect("source_plan_user_authorization_recorded", decision.get("user_authorized_future_promotion_deployment_online_selector_and_claim_gates"), True),
        BASE_MODULE._expect("source_plan_check_count", len(BASE_MODULE._list(source_plan.get("plan_checks"))), EXPECTED_PLAN_CHECK_COUNT),
        BASE_MODULE._expect("source_plan_failed_check_count", len(BASE_MODULE._list(decision.get("failed_checks"))), 0),
        BASE_MODULE._expect("source_static_review_check_count", source_review.get("review_check_count"), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        BASE_MODULE._expect("source_static_review_failed_check_count", source_review.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_boundary_plan_check_count", boundary_summary.get("plan_check_count"), EXPECTED_SOURCE_BOUNDARY_PLAN_CHECK_COUNT),
        BASE_MODULE._expect("source_boundary_plan_failed_check_count", boundary_summary.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_boundary_item_count", boundary_summary.get("boundary_item_count"), EXPECTED_SOURCE_BOUNDARY_ITEM_COUNT),
        BASE_MODULE._expect("source_decision_item_count", len(evidence_plan), EXPECTED_DECISION_ITEM_COUNT),
        BASE_MODULE._expect("source_decision_item_names", [item.get("item_name") for item in evidence_plan], list(PLAN_MODULE.EXPECTED_DECISION_ITEMS)),
        BASE_MODULE._expect("source_decision_items_gate_required", sorted({item.get("decision_gate_required") for item in evidence_plan}), [True]),
        BASE_MODULE._expect("source_decision_items_no_promotion_now", sorted({item.get("authorizes_promotion_now") for item in evidence_plan}), [False]),
        BASE_MODULE._expect("source_decision_items_no_deployment_now", sorted({item.get("authorizes_deployment_now") for item in evidence_plan}), [False]),
        BASE_MODULE._expect("source_decision_items_no_claim_now", sorted({item.get("authorizes_claim_now") for item in evidence_plan}), [False]),
        BASE_MODULE._expect("source_plan_analysis_plan_only", analysis.get("plan_only"), True),
        BASE_MODULE._expect("source_plan_analysis_read_only", analysis.get("read_only"), True),
        BASE_MODULE._expect("source_plan_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(BASE_MODULE._expect(f"source_plan_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(BASE_MODULE._expect(f"source_plan_decision_{flag}", decision.get(flag), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(BASE_MODULE._expect(f"source_plan_analysis_{flag}", analysis.get(flag), False))
    return checks


def _source_surface_checks(script_text: str, test_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._check("plan_script_schema_token", "evidence_chain_decision_plan_v1" in script_text, "evidence_chain_decision_plan_v1", "present"),
        BASE_MODULE._check("plan_script_static_review_next", "evidence_chain_decision_plan_static_review_only" in script_text, "evidence_chain_decision_plan_static_review_only", "present"),
        BASE_MODULE._check("plan_script_fail_closed_item", "fail_closed_decision_outputs" in script_text, "fail_closed_decision_outputs", "present"),
        BASE_MODULE._check("plan_script_future_authorization_record", "user_authorized_future_promotion_deployment_online_selector_and_claim_gates" in script_text, "user_authorized_future_promotion_deployment_online_selector_and_claim_gates", "present"),
        BASE_MODULE._check("plan_test_rejects_source_review_leak", "rejects_source_review_leak" in test_text, "rejects_source_review_leak", "present"),
        BASE_MODULE._check("plan_test_rejects_hash_drift", "rejects_hash_drift" in test_text, "rejects_hash_drift", "present"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("audit_latest_status_is_decision_plan", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        BASE_MODULE._expect("audit_latest_eof_authorizes_decision_plan_static_review", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("audit_decision_plan_ready", BASE_MODULE._latest_value(v14_text, "promotion_readiness_evidence_chain_decision_plan_ready"), "True"),
        BASE_MODULE._expect("audit_decision_plan_static_review_authorized", BASE_MODULE._latest_value(v14_text, "promotion_readiness_evidence_chain_decision_static_review_authorized"), "True"),
        BASE_MODULE._expect("audit_user_future_authorization_recorded", BASE_MODULE._latest_value(v14_text, "user_authorized_future_promotion_deployment_online_selector_and_claim_gates"), "True"),
        BASE_MODULE._expect("audit_selector_promotion_false", BASE_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        BASE_MODULE._expect("audit_deployment_false", BASE_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        BASE_MODULE._expect("audit_safety_claim_false", BASE_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        BASE_MODULE._expect("audit_camp_over_dp_claim_false", BASE_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        BASE_MODULE._expect("status_doc_latest_status_is_decision_plan", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        BASE_MODULE._expect("status_doc_latest_eof_authorizes_decision_plan_static_review", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
    ]


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_plan.get("final_decision"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_check_count": len(BASE_MODULE._list(source_plan.get("plan_checks"))),
        "failed_check_count": len(BASE_MODULE._list(decision.get("failed_checks"))),
    }


def _evidence_chain_decision_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    source_review = BASE_MODULE._dict(source_plan.get("source_static_review_summary"))
    boundary_summary = BASE_MODULE._dict(source_plan.get("boundary_plan_summary"))
    evidence_plan = BASE_MODULE._list(source_plan.get("evidence_chain_decision_plan"))
    return {
        "source_static_review_check_count": source_review.get("review_check_count"),
        "source_static_review_failed_check_count": source_review.get("failed_check_count"),
        "source_boundary_plan_check_count": boundary_summary.get("plan_check_count"),
        "source_boundary_plan_failed_check_count": boundary_summary.get("failed_check_count"),
        "source_boundary_item_count": boundary_summary.get("boundary_item_count"),
        "decision_item_count": len(evidence_plan),
        "decision_item_names": [item.get("item_name") for item in evidence_plan],
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_evidence_chain_decision_plan_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "plan_")) for name in failed):
        failure_class = "source_evidence_chain_decision_plan_contract_failure"
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
        "promotion_readiness_evidence_chain_decision_plan_static_review_passed": passed,
        "promotion_readiness_evidence_chain_decision_authorized": passed,
        "user_authorized_future_promotion_deployment_online_selector_and_claim_gates": True,
        "direct_promotion_recommendation": False,
        "selector_promotion_decision_executed": False,
        "deployment_decision_executed": False,
        "claim_decision_executed": False,
        "score_expression": SCORE_EXPRESSION,
        "recommendation": "run_evidence_chain_decision_before_any_promotion_or_claim" if passed else "repair_contract_before_rerun",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
