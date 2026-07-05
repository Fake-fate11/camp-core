#!/usr/bin/env python3
"""Static review for the v14 promotion-readiness evidence-chain decision."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_decision_module():
    decision_path = Path(__file__).resolve().with_name(
        "decide_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
        "uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision",
        decision_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


DECISION_MODULE = _load_decision_module()
BASE_MODULE = DECISION_MODULE.BASE_MODULE

FIXED_DP_HEAD = DECISION_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = DECISION_MODULE.SCORE_EXPRESSION
SOURCE_DECISION_SCHEMA = DECISION_MODULE.SCHEMA_VERSION
SOURCE_DECISION_STATUS = DECISION_MODULE.READY_STATUS
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = DECISION_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_no_promotion_closeout_record_only"
)
SOURCE_DECISION_JSON_NAME = DECISION_MODULE.DECISION_JSON_NAME
SOURCE_DECISION_MD_NAME = DECISION_MODULE.DECISION_MD_NAME
REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review.md"
)

EXPECTED_DECISION_CHECK_COUNT = 123
EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 138
EXPECTED_SOURCE_PLAN_CHECK_COUNT = 125
EXPECTED_DECISION_ITEM_COUNT = 6
BLOCKED_ACTIONS = DECISION_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = DECISION_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = DECISION_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision_artifact_dir", type=Path, required=True)
    parser.add_argument("--decision_json", type=Path, required=True)
    parser.add_argument("--decision_md", type=Path, required=True)
    parser.add_argument("--decision_sha256s", type=Path, required=True)
    parser.add_argument("--decision_script_py", type=Path, required=True)
    parser.add_argument("--decision_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review",
        action="store_true",
        help="Explicit opt-in for static review of the evidence-chain decision record.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        decision_artifact_dir=args.decision_artifact_dir,
        decision_json=args.decision_json,
        decision_md=args.decision_md,
        decision_sha256s=args.decision_sha256s,
        decision_script_py=args.decision_script_py,
        decision_test_py=args.decision_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_readiness_evidence_chain_decision_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    decision_artifact_dir: Path,
    decision_json: Path,
    decision_md: Path,
    decision_sha256s: Path,
    decision_script_py: Path,
    decision_test_py: Path,
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
    artifact_dir = decision_artifact_dir.resolve()
    paths = {
        "decision_json": decision_json.resolve(),
        "decision_md": decision_md.resolve(),
        "decision_sha256s": decision_sha256s.resolve(),
        "decision_script_py": decision_script_py.resolve(),
        "decision_test_py": decision_test_py.resolve(),
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
        "decision_json": artifact_dir / "decision" / SOURCE_DECISION_JSON_NAME,
        "decision_md": artifact_dir / "decision" / SOURCE_DECISION_MD_NAME,
        "decision_sha256s": artifact_dir / "decision" / "SHA256SUMS",
    }
    source_decision = BASE_MODULE._read_json_dict(paths["decision_json"])
    root_sha256s = BASE_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    decision_sha256s_map = BASE_MODULE._read_sha256sums(paths["decision_sha256s"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(artifact_files["heads"]))
    script_text = BASE_MODULE._read_text(paths["decision_script_py"])
    test_text = BASE_MODULE._read_text(paths["decision_test_py"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        BASE_MODULE._expect("static_review_enabled", enabled, True),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        BASE_MODULE._check("current_camp_head_is_sha", BASE_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        BASE_MODULE._check("decision_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(BASE_MODULE._path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(BASE_MODULE._path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            BASE_MODULE._expect("decision_json_matches_artifact_layout", paths["decision_json"], artifact_files["decision_json"]),
            BASE_MODULE._expect("decision_md_matches_artifact_layout", paths["decision_md"], artifact_files["decision_md"]),
            BASE_MODULE._expect("decision_sha256s_matches_artifact_layout", paths["decision_sha256s"], artifact_files["decision_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, decision_sha256s_map))
    checks.extend(_heads_checks(heads, source_decision))
    checks.extend(_source_decision_contract_checks(source_decision))
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
            "source_decision_artifact_dir": str(artifact_dir),
            "source_decision_json": str(paths["decision_json"]),
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
        "source_decision_summary": _source_decision_summary(source_decision),
        "source_chain_summary": _source_chain_summary(source_decision),
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
        "# Post-Closeout Promotion-Readiness Evidence-Chain Decision Static Review",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Source Decision Summary",
    ]
    for key, value in report["source_decision_summary"].items():
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
    decision_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        BASE_MODULE._sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        BASE_MODULE._sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        BASE_MODULE._sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        BASE_MODULE._sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        BASE_MODULE._sha256sums_expect("artifact_decision_json_root_sha", artifact_files["decision_json"], root_sha256s, (f"decision/{SOURCE_DECISION_JSON_NAME}", f"./decision/{SOURCE_DECISION_JSON_NAME}", SOURCE_DECISION_JSON_NAME)),
        BASE_MODULE._sha256sums_expect("artifact_decision_md_root_sha", artifact_files["decision_md"], root_sha256s, (f"decision/{SOURCE_DECISION_MD_NAME}", f"./decision/{SOURCE_DECISION_MD_NAME}", SOURCE_DECISION_MD_NAME)),
        BASE_MODULE._sha256sums_expect("artifact_decision_sha256s_root_sha", artifact_files["decision_sha256s"], root_sha256s, ("decision/SHA256SUMS", "./decision/SHA256SUMS", "SHA256SUMS")),
        BASE_MODULE._sha256sums_expect("source_decision_json_decision_sha", artifact_files["decision_json"], decision_sha256s, (SOURCE_DECISION_JSON_NAME, f"./{SOURCE_DECISION_JSON_NAME}")),
        BASE_MODULE._sha256sums_expect("source_decision_md_decision_sha", artifact_files["decision_md"], decision_sha256s, (SOURCE_DECISION_MD_NAME, f"./{SOURCE_DECISION_MD_NAME}")),
        BASE_MODULE._expect("artifact_run_exit_zero", BASE_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_decision: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = BASE_MODULE._dict(source_decision.get("analysis"))
    return [
        BASE_MODULE._expect("artifact_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("artifact_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        BASE_MODULE._expect("artifact_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        BASE_MODULE._expect("artifact_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_decision_contract_checks(source_decision: dict[str, Any]) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_decision.get("final_decision"))
    analysis = BASE_MODULE._dict(source_decision.get("analysis"))
    source_review = BASE_MODULE._dict(source_decision.get("source_static_review_summary"))
    source_plan = BASE_MODULE._dict(source_decision.get("source_decision_plan_summary"))
    evidence_decision = BASE_MODULE._list(source_decision.get("evidence_chain_decision"))
    checks = [
        BASE_MODULE._expect("source_decision_schema", source_decision.get("schema_version"), SOURCE_DECISION_SCHEMA),
        BASE_MODULE._expect("source_decision_status", decision.get("status"), SOURCE_DECISION_STATUS),
        BASE_MODULE._expect("source_decision_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_decision_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_decision_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_decision_recorded", decision.get("promotion_readiness_evidence_chain_decision_recorded"), True),
        BASE_MODULE._expect("source_decision_static_review_authorized", decision.get("promotion_readiness_evidence_chain_decision_static_review_authorized"), True),
        BASE_MODULE._expect("source_decision_recommendation", decision.get("recommendation"), "do_not_promote_deploy_or_claim_from_current_evidence_chain"),
        BASE_MODULE._expect("source_decision_check_count", len(BASE_MODULE._list(source_decision.get("decision_checks"))), EXPECTED_DECISION_CHECK_COUNT),
        BASE_MODULE._expect("source_decision_failed_check_count", len(BASE_MODULE._list(decision.get("failed_checks"))), 0),
        BASE_MODULE._expect("source_review_check_count", source_review.get("review_check_count"), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        BASE_MODULE._expect("source_review_failed_check_count", source_review.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_plan_check_count", source_plan.get("source_plan_check_count"), EXPECTED_SOURCE_PLAN_CHECK_COUNT),
        BASE_MODULE._expect("source_plan_failed_check_count", source_plan.get("source_plan_failed_check_count"), 0),
        BASE_MODULE._expect("source_decision_item_count", len(evidence_decision), EXPECTED_DECISION_ITEM_COUNT),
        BASE_MODULE._expect("source_decision_items_no_selector_promotion", sorted({item.get("promote_selector_now") for item in evidence_decision}), [False]),
        BASE_MODULE._expect("source_decision_items_no_deployment", sorted({item.get("deploy_now") for item in evidence_decision}), [False]),
        BASE_MODULE._expect("source_decision_items_no_claim", sorted({item.get("claim_now") for item in evidence_decision}), [False]),
        BASE_MODULE._expect("source_decision_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("source_decision_analysis_record_only", analysis.get("record_only"), True),
        BASE_MODULE._expect("source_decision_analysis_read_only", analysis.get("read_only"), True),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(BASE_MODULE._expect(f"source_decision_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(BASE_MODULE._expect(f"source_decision_decision_{flag}", decision.get(flag), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(BASE_MODULE._expect(f"source_decision_analysis_{flag}", analysis.get(flag), False))
    return checks


def _source_surface_checks(script_text: str, test_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._check("decision_script_schema_token", "evidence_chain_decision_v1" in script_text, "evidence_chain_decision_v1", "present"),
        BASE_MODULE._check("decision_script_static_review_next", "evidence_chain_decision_static_review_only" in script_text, "evidence_chain_decision_static_review_only", "present"),
        BASE_MODULE._check("decision_script_no_promotion_recommendation", "do_not_promote_deploy_or_claim_from_current_evidence_chain" in script_text, "do_not_promote_deploy_or_claim_from_current_evidence_chain", "present"),
        BASE_MODULE._check("decision_test_rejects_source_review_leak", "rejects_source_review_leak" in test_text, "rejects_source_review_leak", "present"),
        BASE_MODULE._check("decision_test_rejects_hash_drift", "rejects_hash_drift" in test_text, "rejects_hash_drift", "present"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("audit_latest_status_is_decision_recorded", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_DECISION_STATUS),
        BASE_MODULE._expect("audit_latest_eof_authorizes_decision_static_review", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("audit_decision_recorded", BASE_MODULE._latest_value(v14_text, "promotion_readiness_evidence_chain_decision_recorded"), "True"),
        BASE_MODULE._expect("audit_decision_static_review_authorized", BASE_MODULE._latest_value(v14_text, "promotion_readiness_evidence_chain_decision_static_review_authorized"), "True"),
        BASE_MODULE._expect("audit_selector_promotion_false", BASE_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        BASE_MODULE._expect("audit_deployment_false", BASE_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        BASE_MODULE._expect("audit_safety_claim_false", BASE_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        BASE_MODULE._expect("audit_camp_over_dp_claim_false", BASE_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        BASE_MODULE._expect("status_doc_latest_status_is_decision_recorded", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_DECISION_STATUS),
        BASE_MODULE._expect("status_doc_latest_eof_authorizes_decision_static_review", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
    ]


def _source_decision_summary(source_decision: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_decision.get("final_decision"))
    return {
        "schema_version": source_decision.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "recommendation": decision.get("recommendation"),
        "decision_check_count": len(BASE_MODULE._list(source_decision.get("decision_checks"))),
        "failed_check_count": len(BASE_MODULE._list(decision.get("failed_checks"))),
    }


def _source_chain_summary(source_decision: dict[str, Any]) -> dict[str, Any]:
    source_review = BASE_MODULE._dict(source_decision.get("source_static_review_summary"))
    source_plan = BASE_MODULE._dict(source_decision.get("source_decision_plan_summary"))
    return {
        "source_review_check_count": source_review.get("review_check_count"),
        "source_review_failed_check_count": source_review.get("failed_check_count"),
        "source_plan_check_count": source_plan.get("source_plan_check_count"),
        "source_plan_failed_check_count": source_plan.get("source_plan_failed_check_count"),
        "decision_item_count": len(BASE_MODULE._list(source_decision.get("evidence_chain_decision"))),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_evidence_chain_decision_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "decision_")) for name in failed):
        failure_class = "source_evidence_chain_decision_contract_failure"
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
        "promotion_readiness_evidence_chain_decision_static_review_passed": passed,
        "promotion_readiness_evidence_chain_no_promotion_closeout_authorized": passed,
        "user_authorized_future_promotion_deployment_online_selector_and_claim_gates": True,
        "recommendation": "record_no_promotion_closeout_for_current_evidence_chain" if passed else "repair_contract_before_rerun",
        "direct_promotion_recommendation": False,
        "selector_promotion_decision_executed": False,
        "deployment_decision_executed": False,
        "claim_decision_executed": False,
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
