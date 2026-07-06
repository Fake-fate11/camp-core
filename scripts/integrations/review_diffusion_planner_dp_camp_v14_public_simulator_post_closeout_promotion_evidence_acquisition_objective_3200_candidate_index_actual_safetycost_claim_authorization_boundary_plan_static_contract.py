#!/usr/bin/env python3
"""Read-only static review for the objective-3200 claim boundary plan."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_plan_module():
    plan_path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_claim_authorization_boundary.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_claim_authorization_boundary_plan",
        plan_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
BASE_MODULE = PLAN_MODULE.SOURCE_REVIEW_MODULE

FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PLAN_MODULE.SCORE_EXPRESSION
PLAN_SCHEMA = PLAN_MODULE.SCHEMA_VERSION
PLAN_STATUS = PLAN_MODULE.READY_STATUS
PLAN_JSON_NAME = PLAN_MODULE.PLAN_JSON_NAME
PLAN_MD_NAME = PLAN_MODULE.PLAN_MD_NAME
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
EXPECTED_PLAN_CHECK_COUNT = 107
EXPECTED_BOUNDARY_ITEMS = PLAN_MODULE.EXPECTED_BOUNDARY_ITEMS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_decision_plan_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_boundary_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_boundary_plan_json", type=Path, required=True)
    parser.add_argument("--source_boundary_plan_md", type=Path, required=True)
    parser.add_argument("--source_boundary_plan_sha256s", type=Path, required=True)
    parser.add_argument("--plan_script", type=Path, required=True)
    parser.add_argument("--plan_test", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_boundary_plan_artifact_dir=args.source_boundary_plan_artifact_dir,
        source_boundary_plan_json=args.source_boundary_plan_json,
        source_boundary_plan_md=args.source_boundary_plan_md,
        source_boundary_plan_sha256s=args.source_boundary_plan_sha256s,
        plan_script=args.plan_script,
        plan_test=args.plan_test,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_boundary_plan_artifact_dir: Path,
    source_boundary_plan_json: Path,
    source_boundary_plan_md: Path,
    source_boundary_plan_sha256s: Path,
    plan_script: Path,
    plan_test: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_boundary_plan_artifact_dir.resolve()
    paths = {
        "source_boundary_plan_json": source_boundary_plan_json.resolve(),
        "source_boundary_plan_md": source_boundary_plan_md.resolve(),
        "source_boundary_plan_sha256s": source_boundary_plan_sha256s.resolve(),
        "plan_script": plan_script.resolve(),
        "plan_test": plan_test.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    files = _artifact_files(artifact_dir)
    source_plan = BASE_MODULE._read_json_dict(paths["source_boundary_plan_json"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(files["heads"]))
    root_sha256s = BASE_MODULE._read_sha256sums(files["root_sha256s"])
    nested_sha256s = BASE_MODULE._read_sha256sums(paths["source_boundary_plan_sha256s"])
    script_text = BASE_MODULE._read_text(paths["plan_script"])
    test_text = BASE_MODULE._read_text(paths["plan_test"])

    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        files=files,
        source_plan=source_plan,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        script_text=script_text,
        test_text=test_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "source_boundary_plan_artifact_dir": str(artifact_dir),
            "source_boundary_plan_json": str(paths["source_boundary_plan_json"]),
            "plan_script": str(paths["plan_script"]),
            "plan_test": str(paths["plan_test"]),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "claim_execution": False,
            "promotion_execution": False,
            "deployment_execution": False,
            "online_selector_change": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "source_hashes": {
            name: BASE_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **files}.items()
        },
        "source_boundary_plan_summary": _source_boundary_plan_summary(source_plan),
        "source_claim_rule_summary": _source_claim_rule_summary(source_plan),
        "review_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_plan=source_plan),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(BASE_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{BASE_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_boundary_plan_summary"]
    failed = decision["failed_checks"] or ["none"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Actual-SafetyCost Claim Boundary Plan Static Review",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Failed checks: `{', '.join(failed)}`",
            f"- Source rows: `{source['source_rows']}`",
            f"- Boundary items: `{source['boundary_item_count']}`",
            "",
            "This read-only static review authorizes only the next claim decision plan gate.",
            "",
        ]
    )


def _artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "plan_json": artifact_dir / "plan" / PLAN_JSON_NAME,
        "plan_md": artifact_dir / "plan" / PLAN_MD_NAME,
        "plan_sha256s": artifact_dir / "plan" / "SHA256SUMS",
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    files: dict[str, Path],
    source_plan: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    script_text: str,
    test_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_plan.get("final_decision"))
    source_summary = BASE_MODULE._dict(source_plan.get("source_result_review_summary"))
    claim = BASE_MODULE._dict(source_plan.get("source_claim_rule_summary"))
    boundary = _list(source_plan.get("claim_authorization_boundary_plan"))
    checks = [
        BASE_MODULE._expect("static_review_enabled", enabled, True),
        BASE_MODULE._check("source_boundary_plan_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        BASE_MODULE._expect("source_boundary_plan_json_path_matches_artifact", paths["source_boundary_plan_json"], files["plan_json"]),
        BASE_MODULE._expect("source_boundary_plan_md_path_matches_artifact", paths["source_boundary_plan_md"], files["plan_md"]),
        BASE_MODULE._expect("source_boundary_plan_sha256s_path_matches_artifact", paths["source_boundary_plan_sha256s"], files["plan_sha256s"]),
        BASE_MODULE._expect("audit_latest_status", BASE_MODULE._latest_value(v14_text, "current_v14_status"), PLAN_STATUS),
        BASE_MODULE._expect("audit_latest_next_work", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("status_doc_latest_status", BASE_MODULE._latest_value(status_text, "current_v14_status"), PLAN_STATUS),
        BASE_MODULE._expect("status_doc_latest_next_work", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("audit_plan_ready", BASE_MODULE._latest_value(v14_text, "objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_ready"), "True"),
        BASE_MODULE._expect("audit_static_review_authorized", BASE_MODULE._latest_value(v14_text, "objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review_authorized"), "True"),
        BASE_MODULE._expect("audit_safety_claim_false", BASE_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        BASE_MODULE._expect("audit_camp_over_dp_claim_false", BASE_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        BASE_MODULE._expect("source_artifact_dp_head_fixed", BASE_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        BASE_MODULE._expect("source_artifact_camp_head_matches_origin", BASE_MODULE._kv(heads, "CAMP_HEAD", "camp_head"), BASE_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main")),
        BASE_MODULE._expect("source_plan_run_exit", BASE_MODULE._read_text(files["run_exit"]).strip(), "0"),
        BASE_MODULE._expect("source_plan_schema", source_plan.get("schema_version"), PLAN_SCHEMA),
        BASE_MODULE._expect("source_plan_status", decision.get("status"), PLAN_STATUS),
        BASE_MODULE._expect("source_plan_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_plan_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_plan_failed_checks", decision.get("failed_checks"), []),
        BASE_MODULE._expect("source_plan_check_count", decision.get("check_count"), EXPECTED_PLAN_CHECK_COUNT),
        BASE_MODULE._expect("source_plan_failed_check_count", decision.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_plan_ready", decision.get("objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_ready"), True),
        BASE_MODULE._expect("source_plan_static_review_authorized", decision.get("objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review_authorized"), True),
        BASE_MODULE._expect("source_plan_claim_execution_false", decision.get("claim_executed_by_this_gate"), False),
        BASE_MODULE._expect("source_plan_safety_claim_false", decision.get("safety_benefit_claim_authorized"), False),
        BASE_MODULE._expect("source_plan_camp_claim_false", decision.get("camp_over_dp_top1_claim_authorized"), False),
        BASE_MODULE._expect("source_plan_selector_promotion_false", decision.get("selector_promotion_authorized"), False),
        BASE_MODULE._expect("source_plan_deployment_false", decision.get("deployment_authorized"), False),
        BASE_MODULE._expect("source_plan_online_selector_false", decision.get("online_selector_change_authorized"), False),
        BASE_MODULE._expect("source_rows", source_summary.get("paired_safetycost_v1_row_count"), PLAN_MODULE.OBJECTIVE_RECORD_COUNT),
        BASE_MODULE._expect("source_better_tie_worse_sum", source_summary.get("delta_better_records", 0) + source_summary.get("delta_tie_records", 0) + source_summary.get("delta_worse_records", 0), PLAN_MODULE.OBJECTIVE_RECORD_COUNT),
        BASE_MODULE._expect("source_claim_rule_passed", claim.get("claim_rule_passed"), True),
        BASE_MODULE._check("source_delta_ci95_high_negative", claim.get("delta_ci95_high") < 0.0 if isinstance(claim.get("delta_ci95_high"), (int, float)) else False, claim.get("delta_ci95_high"), "<0"),
        BASE_MODULE._expect("boundary_item_count", len(boundary), len(EXPECTED_BOUNDARY_ITEMS)),
        BASE_MODULE._expect("boundary_item_names", [item.get("item_name") for item in boundary], list(EXPECTED_BOUNDARY_ITEMS)),
        BASE_MODULE._expect("boundary_items_no_claim_execution", sorted({item.get("executes_claim") for item in boundary}), [False]),
        BASE_MODULE._expect("boundary_items_no_promotion_execution", sorted({item.get("executes_promotion") for item in boundary}), [False]),
        BASE_MODULE._expect("boundary_items_no_deployment_execution", sorted({item.get("executes_deployment") for item in boundary}), [False]),
        BASE_MODULE._expect("boundary_items_no_online_selector", sorted({item.get("enables_online_selector") for item in boundary}), [False]),
        BASE_MODULE._check("plan_script_schema_token", PLAN_SCHEMA in script_text, PLAN_SCHEMA, "present"),
        BASE_MODULE._check("plan_script_static_review_next_token", AUTHORIZED_CURRENT_WORK in script_text, AUTHORIZED_CURRENT_WORK, "present"),
        BASE_MODULE._check("plan_script_no_claim_token", "claim_executed_by_this_gate" in script_text, "claim_executed_by_this_gate", "present"),
        BASE_MODULE._check("plan_test_pass_test", "claim_authorization_boundary_plan_passes" in test_text, "claim_authorization_boundary_plan_passes", "present"),
        BASE_MODULE._check("plan_test_hash_drift_test", "rejects_hash_drift" in test_text, "rejects_hash_drift", "present"),
        BASE_MODULE._check("plan_test_claim_leak_test", "rejects_claim_leak" in test_text, "rejects_claim_leak", "present"),
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
        BASE_MODULE._expect("root_plan_json_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"plan/{PLAN_JSON_NAME}"), BASE_MODULE._sha256(files["plan_json"])),
        BASE_MODULE._expect("root_plan_md_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"plan/{PLAN_MD_NAME}"), BASE_MODULE._sha256(files["plan_md"])),
        BASE_MODULE._expect("root_plan_sha256s_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "plan/SHA256SUMS"), BASE_MODULE._sha256(files["plan_sha256s"])),
        BASE_MODULE._expect("nested_plan_json_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, PLAN_JSON_NAME), BASE_MODULE._sha256(files["plan_json"])),
        BASE_MODULE._expect("nested_plan_md_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, PLAN_MD_NAME), BASE_MODULE._sha256(files["plan_md"])),
    ]


def _source_boundary_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_plan.get("final_decision"))
    source = BASE_MODULE._dict(source_plan.get("source_result_review_summary"))
    boundary = _list(source_plan.get("claim_authorization_boundary_plan"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "check_count": decision.get("check_count"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "source_rows": source.get("paired_safetycost_v1_row_count"),
        "source_better_tie_worse": [
            source.get("delta_better_records"),
            source.get("delta_tie_records"),
            source.get("delta_worse_records"),
        ],
        "boundary_item_count": len(boundary),
    }


def _source_claim_rule_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    claim = BASE_MODULE._dict(source_plan.get("source_claim_rule_summary"))
    return {
        "claim_rule_passed": claim.get("claim_rule_passed"),
        "delta_mean": claim.get("delta_mean"),
        "delta_ci95_high": claim.get("delta_ci95_high"),
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_plan: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    source_decision = BASE_MODULE._dict(source_plan.get("final_decision"))
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_candidate_index_actual_safetycost_claim_authorization_boundary_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif any("sha" in name for name in failed):
        failure_class = "source_artifact_hash_mismatch"
    elif any(name.startswith("source_") for name in failed):
        failure_class = "source_claim_authorization_boundary_plan_contract_failure"
    else:
        failure_class = "claim_authorization_boundary_plan_static_review_contract_failure"
    return {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review_passed": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_claim_decision_plan_authorized": bool(passed),
        "source_plan_passed": source_decision.get("passed"),
        "source_plan_ready": source_decision.get("objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_ready"),
        "claim_executed_by_this_gate": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
