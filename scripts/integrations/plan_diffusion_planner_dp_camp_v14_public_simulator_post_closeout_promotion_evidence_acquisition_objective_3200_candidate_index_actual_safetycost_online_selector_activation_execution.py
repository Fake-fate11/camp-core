#!/usr/bin/env python3
"""Plan-only online selector activation execution after audited activation decision."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_decision_module():
    decision_path = Path(__file__).resolve().with_name(
        "decide_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_online_selector_activation.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_online_selector_activation_decision",
        decision_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_DECISION_MODULE = _load_source_decision_module()
BASE_MODULE = SOURCE_DECISION_MODULE.BASE_MODULE

FIXED_DP_HEAD = SOURCE_DECISION_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_DECISION_MODULE.SCORE_EXPRESSION
SOURCE_DECISION_SCHEMA = SOURCE_DECISION_MODULE.SCHEMA_VERSION
SOURCE_DECISION_STATUS = SOURCE_DECISION_MODULE.READY_STATUS
SOURCE_DECISION_JSON_NAME = SOURCE_DECISION_MODULE.DECISION_JSON_NAME
SOURCE_DECISION_MD_NAME = SOURCE_DECISION_MODULE.DECISION_MD_NAME
AUTHORIZED_CURRENT_WORK = SOURCE_DECISION_MODULE.AUTHORIZED_NEXT_WORK

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_online_selector_activation_"
    "execution_plan_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_plan_static_review_only"
)
PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_online_selector_activation_execution_plan.md"
)
EXPECTED_SOURCE_DECISION_CHECK_COUNT = 69
ONLINE_SELECTOR_ACTIVATION_EXECUTION_PLAN_ITEMS = (
    "source_activation_decision_scope_binding",
    "runtime_manifest_and_switch_preflight",
    "default_off_to_online_enable_sequence",
    "fail_closed_dp_top1_fallback_validation",
    "rollback_disable_and_observability",
    "next_static_review_contract",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_online_selector_activation_decision_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_online_selector_activation_decision_json", type=Path, required=True)
    parser.add_argument("--source_online_selector_activation_decision_md", type=Path, required=True)
    parser.add_argument("--source_online_selector_activation_decision_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_online_selector_activation_decision_artifact_dir=args.source_online_selector_activation_decision_artifact_dir,
        source_online_selector_activation_decision_json=args.source_online_selector_activation_decision_json,
        source_online_selector_activation_decision_md=args.source_online_selector_activation_decision_md,
        source_online_selector_activation_decision_sha256s=args.source_online_selector_activation_decision_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_online_selector_activation_decision_artifact_dir: Path,
    source_online_selector_activation_decision_json: Path,
    source_online_selector_activation_decision_md: Path,
    source_online_selector_activation_decision_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_online_selector_activation_decision_artifact_dir.resolve()
    paths = {
        "source_online_selector_activation_decision_json": source_online_selector_activation_decision_json.resolve(),
        "source_online_selector_activation_decision_md": source_online_selector_activation_decision_md.resolve(),
        "source_online_selector_activation_decision_sha256s": source_online_selector_activation_decision_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    files = _artifact_files(artifact_dir)
    source_decision_report = BASE_MODULE._read_json_dict(paths["source_online_selector_activation_decision_json"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(files["heads"]))
    root_sha256s = BASE_MODULE._read_sha256sums(files["root_sha256s"])
    nested_sha256s = BASE_MODULE._read_sha256sums(paths["source_online_selector_activation_decision_sha256s"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])
    execution_plan = _online_selector_activation_execution_plan(source_decision_report)
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        files=files,
        source_decision_report=source_decision_report,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        execution_plan=execution_plan,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "online_selector_activation_execution": False,
            "deployment_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_online_selector_activation_decision_artifact_dir": str(artifact_dir),
            **{name: str(path) for name, path in paths.items()},
            "output_dir": str(output_dir.resolve()),
        },
        "source_hashes": {
            name: BASE_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **files}.items()
        },
        "source_online_selector_activation_decision_summary": _source_decision_summary(source_decision_report),
        "online_selector_activation_execution_plan": execution_plan,
        "plan_checks": checks,
        "final_decision": _decision(
            passed=passed,
            checks=checks,
            source_decision_report=source_decision_report,
        ),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(json.dumps(BASE_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{BASE_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Objective-3200 Candidate-Index Actual-SafetyCost Online Selector Activation Execution Plan",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failure class: `{decision['failure_class']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{', '.join(failed)}`",
        "",
        "## Online Selector Activation Execution Plan Items",
        "",
    ]
    for item in report["online_selector_activation_execution_plan"]:
        lines.append(f"- `{item['item_name']}`: `{item['purpose']}`")
    lines.extend(["", "No online selector activation is executed by this plan-only gate.", ""])
    return "\n".join(lines)


def _artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "decision_json": artifact_dir / "decision" / SOURCE_DECISION_JSON_NAME,
        "decision_md": artifact_dir / "decision" / SOURCE_DECISION_MD_NAME,
        "decision_sha256s": artifact_dir / "decision" / "SHA256SUMS",
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    files: dict[str, Path],
    source_decision_report: dict[str, Any],
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    execution_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_decision_report.get("final_decision"))
    checks = [
        BASE_MODULE._expect("online_selector_activation_execution_plan_enabled", enabled, True),
        BASE_MODULE._check("source_online_selector_activation_decision_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        BASE_MODULE._expect("source_online_selector_activation_decision_json_path_matches_artifact", paths["source_online_selector_activation_decision_json"], files["decision_json"]),
        BASE_MODULE._expect("source_online_selector_activation_decision_md_path_matches_artifact", paths["source_online_selector_activation_decision_md"], files["decision_md"]),
        BASE_MODULE._expect("source_online_selector_activation_decision_sha256s_path_matches_artifact", paths["source_online_selector_activation_decision_sha256s"], files["decision_sha256s"]),
        BASE_MODULE._expect("audit_latest_status", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_DECISION_STATUS),
        BASE_MODULE._expect("audit_latest_next_work", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("status_doc_latest_status", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_DECISION_STATUS),
        BASE_MODULE._expect("status_doc_latest_next_work", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect(
            "audit_online_selector_activation_execution_plan_authorized",
            BASE_MODULE._latest_value(
                v14_text,
                "objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_plan_authorized",
            ),
            "True",
        ),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        BASE_MODULE._expect("source_artifact_dp_head_fixed", BASE_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        BASE_MODULE._expect("source_artifact_camp_head_matches_origin", BASE_MODULE._kv(heads, "CAMP_HEAD", "camp_head"), BASE_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main")),
        BASE_MODULE._expect("source_online_selector_activation_decision_run_exit", BASE_MODULE._read_text(files["run_exit"]).strip(), "0"),
        BASE_MODULE._expect("source_online_selector_activation_decision_schema", source_decision_report.get("schema_version"), SOURCE_DECISION_SCHEMA),
        BASE_MODULE._expect("source_online_selector_activation_decision_status", decision.get("status"), SOURCE_DECISION_STATUS),
        BASE_MODULE._expect("source_online_selector_activation_decision_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_online_selector_activation_decision_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_online_selector_activation_decision_failed_checks", decision.get("failed_checks"), []),
        BASE_MODULE._expect("source_online_selector_activation_decision_check_count", decision.get("check_count"), EXPECTED_SOURCE_DECISION_CHECK_COUNT),
        BASE_MODULE._expect("source_online_selector_activation_decision_failed_check_count", decision.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_online_selector_activation_decision_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_online_selector_activation_execution_plan_authorized", decision.get("objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_plan_authorized"), True),
        BASE_MODULE._expect("source_selector_promotion_true", decision.get("selector_promotion_authorized"), True),
        BASE_MODULE._expect("source_deployment_true", decision.get("deployment_authorized"), True),
        BASE_MODULE._expect("source_online_selector_true", decision.get("online_selector_change_authorized"), True),
        BASE_MODULE._expect("source_safety_claim_true", decision.get("safety_benefit_claim_authorized"), True),
        BASE_MODULE._expect("source_camp_claim_true", decision.get("camp_over_dp_top1_claim_authorized"), True),
        BASE_MODULE._expect("execution_plan_item_names", [item.get("item_name") for item in execution_plan], list(ONLINE_SELECTOR_ACTIVATION_EXECUTION_PLAN_ITEMS)),
        BASE_MODULE._expect("execution_items_no_execution_now", sorted({item.get("executes_online_selector_now") for item in execution_plan}), [False]),
        BASE_MODULE._expect("execution_items_no_dp_modification", sorted({item.get("authorizes_dp_modification") for item in execution_plan}), [False]),
        BASE_MODULE._expect("execution_items_no_candidate_mutation", sorted({item.get("authorizes_candidate_mutation") for item in execution_plan}), [False]),
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
        BASE_MODULE._expect("root_decision_json_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"decision/{SOURCE_DECISION_JSON_NAME}"), BASE_MODULE._sha256(files["decision_json"])),
        BASE_MODULE._expect("root_decision_md_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"decision/{SOURCE_DECISION_MD_NAME}"), BASE_MODULE._sha256(files["decision_md"])),
        BASE_MODULE._expect("root_decision_sha256s_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "decision/SHA256SUMS"), BASE_MODULE._sha256(files["decision_sha256s"])),
        BASE_MODULE._expect("nested_decision_json_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_DECISION_JSON_NAME), BASE_MODULE._sha256(files["decision_json"])),
        BASE_MODULE._expect("nested_decision_md_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_DECISION_MD_NAME), BASE_MODULE._sha256(files["decision_md"])),
    ]


def _online_selector_activation_execution_plan(source_decision_report: dict[str, Any]) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_decision_report.get("final_decision"))
    return [
        {
            "item_name": "source_activation_decision_scope_binding",
            "purpose": "bind any later online selector activation execution to the audited decision and fixed-DP candidate tensor scope",
            "source_online_selector_change_authorized": decision.get("online_selector_change_authorized"),
            "executes_online_selector_now": False,
            "authorizes_dp_modification": False,
            "authorizes_candidate_mutation": False,
        },
        {
            "item_name": "runtime_manifest_and_switch_preflight",
            "purpose": "require a static manifest of runtime selector assets, switch state, and fail-closed DP Top-1 fallback before execution",
            "executes_online_selector_now": False,
            "authorizes_dp_modification": False,
            "authorizes_candidate_mutation": False,
        },
        {
            "item_name": "default_off_to_online_enable_sequence",
            "purpose": "pre-register the reversible sequence for moving the audited selector from default-off to online enabled",
            "executes_online_selector_now": False,
            "authorizes_dp_modification": False,
            "authorizes_candidate_mutation": False,
        },
        {
            "item_name": "fail_closed_dp_top1_fallback_validation",
            "purpose": "require evidence that missing, malformed, or disabled CAMP inputs fall back to DP Top-1",
            "executes_online_selector_now": False,
            "authorizes_dp_modification": False,
            "authorizes_candidate_mutation": False,
        },
        {
            "item_name": "rollback_disable_and_observability",
            "purpose": "require rollback, disable controls, and observability records before any later execution gate",
            "executes_online_selector_now": False,
            "authorizes_dp_modification": False,
            "authorizes_candidate_mutation": False,
        },
        {
            "item_name": "next_static_review_contract",
            "purpose": "require a read-only static review before any online selector activation execution can run",
            "next_work": AUTHORIZED_NEXT_WORK,
            "executes_online_selector_now": False,
            "authorizes_dp_modification": False,
            "authorizes_candidate_mutation": False,
        },
    ]


def _source_decision_summary(source_decision_report: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_decision_report.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "check_count": decision.get("check_count"),
        "failed_check_count": decision.get("failed_check_count"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "online_selector_change_authorized": decision.get("online_selector_change_authorized"),
    }


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    source_decision_report: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    source_decision = BASE_MODULE._dict(source_decision_report.get("final_decision"))
    if passed:
        failure_class = None
    elif "online_selector_activation_execution_plan_enabled" in failed:
        failure_class = "explicit_candidate_index_actual_safetycost_online_selector_activation_execution_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif any("sha" in name for name in failed):
        failure_class = "source_artifact_hash_mismatch"
    elif any(name.startswith("source_") for name in failed):
        failure_class = "source_online_selector_activation_decision_contract_failure"
    else:
        failure_class = "online_selector_activation_execution_plan_contract_failure"
    return {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_plan_ready": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_plan_static_review_authorized": bool(passed),
        "source_online_selector_activation_decision_passed": source_decision.get("passed"),
        "selector_promotion_authorized": source_decision.get("selector_promotion_authorized"),
        "deployment_authorized": source_decision.get("deployment_authorized"),
        "online_selector_change_authorized": source_decision.get("online_selector_change_authorized"),
        "online_selector_activation_execution": False,
        "safety_benefit_claim_authorized": source_decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": source_decision.get("camp_over_dp_top1_claim_authorized"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
