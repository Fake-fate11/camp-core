#!/usr/bin/env python3
"""Plan-only promotion authorization boundary gate after continuation review."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
        "uncertainty_coverage_evidence_package_continuation_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_static_review",
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
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_package_promotion_authorization_boundary_plan_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_authorization_boundary_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_authorization_boundary_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_authorization_boundary_plan_static_review_only"
)
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
PLAN_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_authorization_boundary_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_authorization_boundary_plan.md"
)

EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 131
EXPECTED_SOURCE_PLAN_CHECK_COUNT = 122
EXPECTED_BOUNDARY_ITEMS = (
    "user_authorization_scope_record",
    "evidence_chain_completeness_before_promotion",
    "selector_promotion_decision_gate_hold",
    "deployment_and_online_selector_gate_hold",
    "safety_and_camp_over_dp_claim_gate_hold",
)
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_REVIEW_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = SOURCE_REVIEW_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_authorization_boundary_plan",
        action="store_true",
        help="Explicit opt-in for plan-only promotion authorization boundary recording.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_promotion_authorization_boundary_plan,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
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
    artifact_dir = source_static_review_artifact_dir.resolve()
    paths = {
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_md": source_static_review_md.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
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
    source_review = BASE_MODULE._read_json_dict(paths["source_static_review_json"])
    root_sha256s = BASE_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    review_sha256s = BASE_MODULE._read_sha256sums(paths["source_static_review_sha256s"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(artifact_files["heads"]))
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        BASE_MODULE._expect("authorization_boundary_plan_enabled", enabled, True),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        BASE_MODULE._check("current_camp_head_is_sha", BASE_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        BASE_MODULE._check("source_static_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(BASE_MODULE._path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(BASE_MODULE._path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            BASE_MODULE._expect("source_review_json_matches_artifact_layout", paths["source_static_review_json"], artifact_files["review_json"]),
            BASE_MODULE._expect("source_review_md_matches_artifact_layout", paths["source_static_review_md"], artifact_files["review_md"]),
            BASE_MODULE._expect("source_review_sha256s_matches_artifact_layout", paths["source_static_review_sha256s"], artifact_files["review_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, review_sha256s))
    checks.extend(_heads_checks(heads, source_review))
    checks.extend(_source_review_contract_checks(source_review))
    checks.extend(_audit_checks(v14_text, status_text))
    boundary_plan = _boundary_plan(label=label, source_review=source_review)
    checks.extend(_boundary_plan_checks(boundary_plan))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "plan_only": True,
            "read_only": True,
            "user_authorized_future_promotion_deployment_online_selector_and_claim_gates": True,
            "source_static_review_artifact_dir": str(artifact_dir),
            "source_static_review_json": str(paths["source_static_review_json"]),
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
        "closeout_record_summary": _closeout_record_summary(source_review),
        "authorization_boundary_plan": boundary_plan,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    BASE_MODULE._write_json(output_dir / PLAN_JSON_NAME, report)
    (output_dir / PLAN_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    BASE_MODULE._write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Promotion Authorization Boundary Plan",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Authorization Boundary Plan",
    ]
    for item in report["authorization_boundary_plan"]:
        lines.append(f"- `{item['item_name']}`: `{item['purpose']}`")
    lines.extend(["", "## Checks"])
    for check in report["plan_checks"]:
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
        BASE_MODULE._sha256sums_expect("source_review_json_review_sha", artifact_files["review_json"], review_sha256s, (SOURCE_REVIEW_JSON_NAME, f"./{SOURCE_REVIEW_JSON_NAME}")),
        BASE_MODULE._sha256sums_expect("source_review_md_review_sha", artifact_files["review_md"], review_sha256s, (SOURCE_REVIEW_MD_NAME, f"./{SOURCE_REVIEW_MD_NAME}")),
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
    source_plan = BASE_MODULE._dict(source_review.get("source_plan_summary"))
    closeout_summary = BASE_MODULE._dict(source_review.get("closeout_record_summary"))
    checks = [
        BASE_MODULE._expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        BASE_MODULE._expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("source_review_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_review_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_review_static_review_passed", decision.get("post_closeout_continuation_plan_static_review_passed"), True),
        BASE_MODULE._expect("source_review_boundary_plan_authorized", decision.get("promotion_authorization_boundary_plan_authorized"), True),
        BASE_MODULE._expect("source_review_check_count", len(BASE_MODULE._list(source_review.get("review_checks"))), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        BASE_MODULE._expect("source_review_failed_check_count", len(BASE_MODULE._list(decision.get("failed_checks"))), 0),
        BASE_MODULE._expect("source_plan_check_count", source_plan.get("plan_check_count"), EXPECTED_SOURCE_PLAN_CHECK_COUNT),
        BASE_MODULE._expect("source_plan_failed_check_count", source_plan.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_continuation_item_count", source_plan.get("continuation_item_count"), 5),
        BASE_MODULE._expect("source_closeout_final_package_state", closeout_summary.get("final_package_state"), "audit_evidence_only_closed_no_promotion_no_deployment_no_claim"),
        BASE_MODULE._expect("source_closeout_promotion_recommended", closeout_summary.get("promotion_recommended"), False),
        BASE_MODULE._expect("source_closeout_selector_promotion", closeout_summary.get("selector_promotion_authorized"), False),
        BASE_MODULE._expect("source_closeout_deployment", closeout_summary.get("deployment_authorized"), False),
        BASE_MODULE._expect("source_closeout_safety_claim", closeout_summary.get("safety_benefit_claim_authorized"), False),
        BASE_MODULE._expect("source_closeout_camp_over_dp", closeout_summary.get("camp_over_dp_top1_claim_authorized"), False),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(BASE_MODULE._expect(f"source_review_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(BASE_MODULE._expect(f"source_review_decision_{flag}", decision.get(flag), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(BASE_MODULE._expect(f"source_review_analysis_{flag}", BASE_MODULE._dict(source_review.get("analysis")).get(flag), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("audit_latest_status_is_continuation_static_review", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("audit_latest_eof_authorizes_boundary_plan", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("audit_continuation_static_review_passed", BASE_MODULE._latest_value(v14_text, "post_closeout_continuation_plan_static_review_passed"), "True"),
        BASE_MODULE._expect("audit_boundary_plan_authorized", BASE_MODULE._latest_value(v14_text, "promotion_authorization_boundary_plan_authorized"), "True"),
        BASE_MODULE._expect("audit_selector_promotion_false", BASE_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        BASE_MODULE._expect("audit_deployment_false", BASE_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        BASE_MODULE._expect("audit_safety_claim_false", BASE_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        BASE_MODULE._expect("audit_camp_over_dp_claim_false", BASE_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        BASE_MODULE._expect("status_doc_latest_status_is_continuation_static_review", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("status_doc_latest_eof_authorizes_boundary_plan", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
    ]


def _boundary_plan(label: str | None, source_review: dict[str, Any]) -> list[dict[str, Any]]:
    source_summary = _source_static_review_summary(source_review)
    return [
        {
            "item_name": "user_authorization_scope_record",
            "purpose": "record that future promotion deployment online-selector and claim gates are user-authorized only if later EOF and evidence gates pass",
            "source_status": source_summary["status"],
            "future_gate_authorized_by_user": True,
            "executes_promotion": False,
            "executes_deployment": False,
            "makes_claim": False,
        },
        {
            "item_name": "evidence_chain_completeness_before_promotion",
            "purpose": "require a follow-on decision gate to prove evidence completeness before any selector promotion",
            "source_status": source_summary["status"],
            "future_gate_authorized_by_user": True,
            "executes_promotion": False,
            "executes_deployment": False,
            "makes_claim": False,
        },
        {
            "item_name": "selector_promotion_decision_gate_hold",
            "purpose": "hold selector promotion until a dedicated auditable decision gate recommends it",
            "source_status": source_summary["status"],
            "future_gate_authorized_by_user": True,
            "executes_promotion": False,
            "executes_deployment": False,
            "makes_claim": False,
        },
        {
            "item_name": "deployment_and_online_selector_gate_hold",
            "purpose": "hold deployment and online selector activation until separate deployment-readiness evidence exists",
            "source_status": source_summary["status"],
            "future_gate_authorized_by_user": True,
            "executes_promotion": False,
            "executes_deployment": False,
            "makes_claim": False,
        },
        {
            "item_name": "safety_and_camp_over_dp_claim_gate_hold",
            "purpose": "hold safety-benefit and CAMP-over-DP claims until a dedicated claim-evidence gate passes",
            "source_status": source_summary["status"],
            "future_gate_authorized_by_user": True,
            "executes_promotion": False,
            "executes_deployment": False,
            "makes_claim": False,
        },
    ]


def _boundary_plan_checks(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("boundary_item_names", [item.get("item_name") for item in plan], list(EXPECTED_BOUNDARY_ITEMS)),
        BASE_MODULE._expect("boundary_items_user_authorized", sorted({item.get("future_gate_authorized_by_user") for item in plan}), [True]),
        BASE_MODULE._expect("boundary_items_no_promotion_execution", sorted({item.get("executes_promotion") for item in plan}), [False]),
        BASE_MODULE._expect("boundary_items_no_deployment_execution", sorted({item.get("executes_deployment") for item in plan}), [False]),
        BASE_MODULE._expect("boundary_items_no_claim", sorted({item.get("makes_claim") for item in plan}), [False]),
    ]


def _source_static_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_review.get("final_decision"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(BASE_MODULE._list(source_review.get("review_checks"))),
        "failed_check_count": len(BASE_MODULE._list(decision.get("failed_checks"))),
    }


def _closeout_record_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    summary = BASE_MODULE._dict(source_review.get("closeout_record_summary"))
    return {
        "final_package_state": summary.get("final_package_state"),
        "promotion_recommended": summary.get("promotion_recommended"),
        "selector_promotion_authorized": summary.get("selector_promotion_authorized"),
        "deployment_authorized": summary.get("deployment_authorized"),
        "safety_benefit_claim_authorized": summary.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": summary.get("camp_over_dp_top1_claim_authorized"),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "authorization_boundary_plan_enabled" in failed:
        failure_class = "explicit_promotion_authorization_boundary_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "boundary_")) for name in failed):
        failure_class = "promotion_authorization_boundary_source_contract_failure"
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
        "promotion_authorization_boundary_plan_ready": passed,
        "promotion_authorization_boundary_static_review_authorized": passed,
        "user_authorized_future_promotion_deployment_online_selector_and_claim_gates": True,
        "uncertainty_coverage_evidence_package_closed": True,
        "evidence_package_reopened_by_this_gate": False,
        "direct_promotion_recommendation": False,
        "score_expression": SCORE_EXPRESSION,
        "recommendation": "static_review_authorization_boundary_before_any_promotion_decision" if passed else "repair_contract_before_rerun",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
