#!/usr/bin/env python3
"""Plan-only claim authorization boundary after objective-3200 SafetyCost review."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_delta_materialization_execution_result.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_delta_materialization_execution_result_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.CLAIM_AUTHORIZATION_BOUNDARY_PLAN_WORK
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review_only"
)

PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan.md"
)
EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 102
OBJECTIVE_RECORD_COUNT = 3200
EXPECTED_BOUNDARY_ITEMS = (
    "source_claim_support_evidence_record",
    "fixed_dp_candidate_tensor_scope_boundary",
    "claim_wording_scope_preregistration",
    "claim_execution_gate_hold",
    "promotion_deployment_online_selector_gate_hold",
)
ANALYSIS_FALSE_FLAGS = (
    "actual_safetycost_delta_materialization_executed_by_review",
    "candidate_index_replay_executed_by_review",
    "outcome_acquisition_executed_by_review",
    "training_executed_by_review",
    "candidate_generation_executed_by_review",
    "dp_modified_by_review",
    "promotion_executed_by_review",
    "deployment_executed_by_review",
    "online_selector_change_by_review",
    "safety_or_camp_over_dp_claim_by_review",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_md", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_md=args.source_result_review_md,
        source_result_review_sha256s=args.source_result_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(SOURCE_REVIEW_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_result_review_artifact_dir.resolve()
    paths = {
        "source_result_review_json": source_result_review_json.resolve(),
        "source_result_review_md": source_result_review_md.resolve(),
        "source_result_review_sha256s": source_result_review_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    files = _artifact_files(artifact_dir)
    source_review = SOURCE_REVIEW_MODULE._read_json_dict(paths["source_result_review_json"])
    v14_text = SOURCE_REVIEW_MODULE._read_text(paths["v14_audit_md"])
    status_text = SOURCE_REVIEW_MODULE._read_text(paths["current_status_md"])
    heads = SOURCE_REVIEW_MODULE._parse_key_values(SOURCE_REVIEW_MODULE._read_text(files["heads"]))
    root_sha256s = SOURCE_REVIEW_MODULE._read_sha256sums(files["root_sha256s"])
    nested_sha256s = SOURCE_REVIEW_MODULE._read_sha256sums(paths["source_result_review_sha256s"])

    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        files=files,
        source_review=source_review,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    boundary_plan = _boundary_plan(source_review)
    checks.extend(_boundary_plan_checks(boundary_plan))
    passed = all(check["passed"] for check in checks)
    decision = _decision(passed=passed, checks=checks, source_review=source_review)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "source_result_review_artifact_dir": str(artifact_dir),
            "source_result_review_json": str(paths["source_result_review_json"]),
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
            name: SOURCE_REVIEW_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **files}.items()
        },
        "source_result_review_summary": _source_result_review_summary(source_review),
        "source_claim_rule_summary": _source_claim_rule_summary(source_review),
        "claim_authorization_boundary_plan": boundary_plan,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": decision,
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(json.dumps(SOURCE_REVIEW_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{SOURCE_REVIEW_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_result_review_summary"]
    claim = report["source_claim_rule_summary"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Objective-3200 Candidate-Index Actual-SafetyCost Claim Authorization Boundary Plan",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failure class: `{decision['failure_class']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{', '.join(failed)}`",
        "",
        "## Source Evidence",
        "",
        f"- Paired rows: `{source['paired_safetycost_v1_row_count']}`",
        f"- Better / tie / worse: `{source['delta_better_records']} / {source['delta_tie_records']} / {source['delta_worse_records']}`",
        f"- Mean delta: `{claim['delta_mean']}`",
        f"- CI95 high: `{claim['delta_ci95_high']}`",
        f"- Claim rule passed: `{claim['claim_rule_passed']}`",
        "",
        "## Boundary",
        "",
    ]
    for item in report["claim_authorization_boundary_plan"]:
        lines.append(f"- `{item['item_name']}`: `{item['purpose']}`")
    lines.extend(
        [
            "",
            "This plan does not execute a claim, selector promotion, deployment, online selector change, training, candidate generation, or Diffusion Planner modification.",
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "review_json": artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": artifact_dir / "review" / "SHA256SUMS",
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    files: dict[str, Path],
    source_review: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    decision = SOURCE_REVIEW_MODULE._dict(source_review.get("final_decision"))
    analysis = SOURCE_REVIEW_MODULE._dict(source_review.get("analysis"))
    source_summary = SOURCE_REVIEW_MODULE._dict(source_review.get("source_execution_summary"))
    claim = SOURCE_REVIEW_MODULE._dict(source_review.get("actual_safetycost_claim_rule_summary"))
    checks = [
        SOURCE_REVIEW_MODULE._expect("claim_authorization_boundary_plan_enabled", enabled, True),
        SOURCE_REVIEW_MODULE._check("source_result_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        SOURCE_REVIEW_MODULE._expect("source_result_review_json_path_matches_artifact", paths["source_result_review_json"], files["review_json"]),
        SOURCE_REVIEW_MODULE._expect("source_result_review_md_path_matches_artifact", paths["source_result_review_md"], files["review_md"]),
        SOURCE_REVIEW_MODULE._expect("source_result_review_sha256s_path_matches_artifact", paths["source_result_review_sha256s"], files["review_sha256s"]),
        SOURCE_REVIEW_MODULE._expect("audit_latest_status", SOURCE_REVIEW_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        SOURCE_REVIEW_MODULE._expect("audit_latest_next_work", SOURCE_REVIEW_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        SOURCE_REVIEW_MODULE._expect("status_doc_latest_status", SOURCE_REVIEW_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        SOURCE_REVIEW_MODULE._expect("status_doc_latest_next_work", SOURCE_REVIEW_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        SOURCE_REVIEW_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        SOURCE_REVIEW_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        SOURCE_REVIEW_MODULE._expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        SOURCE_REVIEW_MODULE._expect("source_artifact_dp_head_fixed", SOURCE_REVIEW_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        SOURCE_REVIEW_MODULE._expect("source_artifact_camp_head_matches_origin", SOURCE_REVIEW_MODULE._kv(heads, "CAMP_HEAD", "camp_head"), SOURCE_REVIEW_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main")),
        SOURCE_REVIEW_MODULE._expect("source_review_run_exit", SOURCE_REVIEW_MODULE._read_text(files["run_exit"]).strip(), "0"),
        SOURCE_REVIEW_MODULE._expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        SOURCE_REVIEW_MODULE._expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        SOURCE_REVIEW_MODULE._expect("source_review_passed", decision.get("passed"), True),
        SOURCE_REVIEW_MODULE._expect("source_review_failure_class", decision.get("failure_class"), None),
        SOURCE_REVIEW_MODULE._expect("source_review_failed_checks", decision.get("failed_checks"), []),
        SOURCE_REVIEW_MODULE._expect("source_review_check_count", decision.get("check_count"), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        SOURCE_REVIEW_MODULE._expect("source_review_failed_check_count", decision.get("failed_check_count"), 0),
        SOURCE_REVIEW_MODULE._expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        SOURCE_REVIEW_MODULE._expect("source_review_result_review_passed_flag", decision.get("objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_result_review_passed"), True),
        SOURCE_REVIEW_MODULE._expect("source_claim_rule_passed", decision.get("claim_rule_passed"), True),
        SOURCE_REVIEW_MODULE._expect("source_safety_benefit_supported", decision.get("safety_benefit_claim_supported"), True),
        SOURCE_REVIEW_MODULE._expect("source_camp_over_dp_supported", decision.get("camp_over_dp_top1_claim_supported"), True),
        SOURCE_REVIEW_MODULE._expect("source_claim_boundary_plan_authorized", decision.get("claim_authorization_boundary_plan_authorized"), True),
        SOURCE_REVIEW_MODULE._expect("source_safety_claim_not_authorized", decision.get("safety_benefit_claim_authorized"), False),
        SOURCE_REVIEW_MODULE._expect("source_camp_over_dp_claim_not_authorized", decision.get("camp_over_dp_top1_claim_authorized"), False),
        SOURCE_REVIEW_MODULE._expect("source_selector_promotion_not_authorized", decision.get("selector_promotion_authorized"), False),
        SOURCE_REVIEW_MODULE._expect("source_deployment_not_authorized", decision.get("deployment_authorized"), False),
        SOURCE_REVIEW_MODULE._expect("source_online_selector_not_authorized", decision.get("online_selector_change_authorized"), False),
        SOURCE_REVIEW_MODULE._expect("source_paired_rows", source_summary.get("paired_safetycost_v1_row_count"), OBJECTIVE_RECORD_COUNT),
        SOURCE_REVIEW_MODULE._expect("source_same_plus_non_top1", source_summary.get("same_as_top1_records", 0) + source_summary.get("non_top1_shadow_selected_records", 0), OBJECTIVE_RECORD_COUNT),
        SOURCE_REVIEW_MODULE._expect("source_better_tie_worse_sum", source_summary.get("delta_better_records", 0) + source_summary.get("delta_tie_records", 0) + source_summary.get("delta_worse_records", 0), OBJECTIVE_RECORD_COUNT),
        SOURCE_REVIEW_MODULE._expect("claim_rule_actual_safetycost_available", claim.get("actual_safetycost_v1_available"), True),
        SOURCE_REVIEW_MODULE._expect("claim_rule_evaluable", claim.get("claim_rule_evaluable"), True),
        SOURCE_REVIEW_MODULE._expect("claim_rule_passed", claim.get("claim_rule_passed"), True),
        SOURCE_REVIEW_MODULE._check("claim_rule_delta_mean_negative", claim.get("delta_mean") < 0.0 if isinstance(claim.get("delta_mean"), (int, float)) else False, claim.get("delta_mean"), "<0"),
        SOURCE_REVIEW_MODULE._check("claim_rule_delta_ci95_high_negative", claim.get("delta_ci95_high") < 0.0 if isinstance(claim.get("delta_ci95_high"), (int, float)) else False, claim.get("delta_ci95_high"), "<0"),
        SOURCE_REVIEW_MODULE._expect("claim_rule_safety_claim_not_authorized", claim.get("safety_benefit_claim_authorized"), False),
        SOURCE_REVIEW_MODULE._expect("claim_rule_camp_over_dp_claim_not_authorized", claim.get("camp_over_dp_top1_claim_authorized"), False),
        SOURCE_REVIEW_MODULE._expect("analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
        SOURCE_REVIEW_MODULE._expect("audit_result_review_passed", SOURCE_REVIEW_MODULE._latest_value(v14_text, "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_result_review_passed"), "True"),
        SOURCE_REVIEW_MODULE._expect("audit_claim_boundary_plan_authorized", SOURCE_REVIEW_MODULE._latest_value(v14_text, "objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_authorized"), "True"),
        SOURCE_REVIEW_MODULE._expect("audit_safety_supported", SOURCE_REVIEW_MODULE._latest_value(v14_text, "safety_benefit_claim_supported"), "True"),
        SOURCE_REVIEW_MODULE._expect("audit_camp_over_dp_supported", SOURCE_REVIEW_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_supported"), "True"),
        SOURCE_REVIEW_MODULE._expect("audit_safety_claim_false", SOURCE_REVIEW_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        SOURCE_REVIEW_MODULE._expect("audit_camp_over_dp_claim_false", SOURCE_REVIEW_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]
    for name, path in paths.items():
        checks.extend(SOURCE_REVIEW_MODULE._path_checks(name, path, allow_empty=False))
    for name, path in files.items():
        checks.extend(SOURCE_REVIEW_MODULE._path_checks(f"source_artifact_{name}", path, allow_empty=name == "stderr"))
    checks.extend(_sha_checks(root_sha256s=root_sha256s, nested_sha256s=nested_sha256s, files=files))
    for action in BLOCKED_ACTIONS:
        checks.append(SOURCE_REVIEW_MODULE._expect(f"source_review_decision_{action}", decision.get(action), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(SOURCE_REVIEW_MODULE._expect(f"source_review_analysis_{flag}", analysis.get(flag), False))
    return checks


def _sha_checks(
    *,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    files: dict[str, Path],
) -> list[dict[str, Any]]:
    return [
        SOURCE_REVIEW_MODULE._expect("root_heads_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(root_sha256s, "HEADS"), SOURCE_REVIEW_MODULE._sha256(files["heads"])),
        SOURCE_REVIEW_MODULE._expect("root_command_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(root_sha256s, "COMMAND"), SOURCE_REVIEW_MODULE._sha256(files["command"])),
        SOURCE_REVIEW_MODULE._expect("root_stdout_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(root_sha256s, "stdout"), SOURCE_REVIEW_MODULE._sha256(files["stdout"])),
        SOURCE_REVIEW_MODULE._expect("root_stderr_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(root_sha256s, "stderr"), SOURCE_REVIEW_MODULE._sha256(files["stderr"])),
        SOURCE_REVIEW_MODULE._expect("root_run_exit_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(root_sha256s, "run.exit"), SOURCE_REVIEW_MODULE._sha256(files["run_exit"])),
        SOURCE_REVIEW_MODULE._expect("root_review_json_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(root_sha256s, f"review/{SOURCE_REVIEW_JSON_NAME}"), SOURCE_REVIEW_MODULE._sha256(files["review_json"])),
        SOURCE_REVIEW_MODULE._expect("root_review_md_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(root_sha256s, f"review/{SOURCE_REVIEW_MD_NAME}"), SOURCE_REVIEW_MODULE._sha256(files["review_md"])),
        _expect_optional_root_sha("root_review_sha256s_sha", root_sha256s, "review/SHA256SUMS", files["review_sha256s"]),
        SOURCE_REVIEW_MODULE._expect("nested_review_json_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(nested_sha256s, SOURCE_REVIEW_JSON_NAME), SOURCE_REVIEW_MODULE._sha256(files["review_json"])),
        SOURCE_REVIEW_MODULE._expect("nested_review_md_sha", SOURCE_REVIEW_MODULE._sha_for_suffix(nested_sha256s, SOURCE_REVIEW_MD_NAME), SOURCE_REVIEW_MODULE._sha256(files["review_md"])),
    ]


def _expect_optional_root_sha(name: str, sums: dict[str, str], suffix: str, path: Path) -> dict[str, Any]:
    actual = SOURCE_REVIEW_MODULE._sha_for_suffix(sums, suffix)
    expected = SOURCE_REVIEW_MODULE._sha256(path)
    return SOURCE_REVIEW_MODULE._check(name, actual in (None, expected), actual, f"absent or {expected}")


def _boundary_plan(source_review: dict[str, Any]) -> list[dict[str, Any]]:
    source = _source_result_review_summary(source_review)
    claim = _source_claim_rule_summary(source_review)
    return [
        {
            "item_name": "source_claim_support_evidence_record",
            "purpose": "bind any later claim decision to the audited objective-3200 paired SafetyCost source review",
            "paired_safetycost_v1_row_count": source["paired_safetycost_v1_row_count"],
            "delta_ci95_high": claim["delta_ci95_high"],
            "executes_claim": False,
            "executes_promotion": False,
            "executes_deployment": False,
            "enables_online_selector": False,
        },
        {
            "item_name": "fixed_dp_candidate_tensor_scope_boundary",
            "purpose": "scope future claim language to CAMP shadow selection over fixed DP candidate tensors only",
            "required_dp_head": FIXED_DP_HEAD,
            "camp_generates_or_modifies_trajectories": False,
            "executes_claim": False,
            "executes_promotion": False,
            "executes_deployment": False,
            "enables_online_selector": False,
        },
        {
            "item_name": "claim_wording_scope_preregistration",
            "purpose": "require later wording to state SafetyCost_v1 paired public-simulator evidence and avoid deployment or online-safety generalization",
            "allows_safety_benefit_claim_planning": True,
            "allows_camp_over_dp_top1_claim_planning": True,
            "executes_claim": False,
            "executes_promotion": False,
            "executes_deployment": False,
            "enables_online_selector": False,
        },
        {
            "item_name": "claim_execution_gate_hold",
            "purpose": "hold actual safety-benefit and CAMP-over-DP Top-1 claims until a dedicated audited claim decision gate passes",
            "future_static_review_required": True,
            "executes_claim": False,
            "executes_promotion": False,
            "executes_deployment": False,
            "enables_online_selector": False,
        },
        {
            "item_name": "promotion_deployment_online_selector_gate_hold",
            "purpose": "keep selector promotion deployment and online selector activation outside this claim-boundary plan",
            "future_promotion_gate_required": True,
            "future_deployment_gate_required": True,
            "executes_claim": False,
            "executes_promotion": False,
            "executes_deployment": False,
            "enables_online_selector": False,
        },
    ]


def _boundary_plan_checks(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        SOURCE_REVIEW_MODULE._expect("boundary_item_names", [item.get("item_name") for item in plan], list(EXPECTED_BOUNDARY_ITEMS)),
        SOURCE_REVIEW_MODULE._expect("boundary_items_no_claim_execution", sorted({item.get("executes_claim") for item in plan}), [False]),
        SOURCE_REVIEW_MODULE._expect("boundary_items_no_promotion_execution", sorted({item.get("executes_promotion") for item in plan}), [False]),
        SOURCE_REVIEW_MODULE._expect("boundary_items_no_deployment_execution", sorted({item.get("executes_deployment") for item in plan}), [False]),
        SOURCE_REVIEW_MODULE._expect("boundary_items_no_online_selector", sorted({item.get("enables_online_selector") for item in plan}), [False]),
    ]


def _source_result_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = SOURCE_REVIEW_MODULE._dict(source_review.get("final_decision"))
    source = SOURCE_REVIEW_MODULE._dict(source_review.get("source_execution_summary"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "check_count": decision.get("check_count"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "paired_safetycost_v1_row_count": source.get("paired_safetycost_v1_row_count"),
        "same_as_top1_records": source.get("same_as_top1_records"),
        "non_top1_shadow_selected_records": source.get("non_top1_shadow_selected_records"),
        "delta_better_records": source.get("delta_better_records"),
        "delta_tie_records": source.get("delta_tie_records"),
        "delta_worse_records": source.get("delta_worse_records"),
    }


def _source_claim_rule_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    claim = SOURCE_REVIEW_MODULE._dict(source_review.get("actual_safetycost_claim_rule_summary"))
    return {
        "actual_safetycost_v1_available": claim.get("actual_safetycost_v1_available"),
        "claim_rule_evaluable": claim.get("claim_rule_evaluable"),
        "claim_rule_passed": claim.get("claim_rule_passed"),
        "delta_mean": claim.get("delta_mean"),
        "delta_ci95_low": claim.get("delta_ci95_low"),
        "delta_ci95_high": claim.get("delta_ci95_high"),
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_review: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    source_decision = SOURCE_REVIEW_MODULE._dict(source_review.get("final_decision"))
    if passed:
        failure_class = None
    elif "claim_authorization_boundary_plan_enabled" in failed:
        failure_class = "explicit_candidate_index_actual_safetycost_claim_authorization_boundary_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif any("sha" in name for name in failed):
        failure_class = "source_artifact_hash_mismatch"
    elif any(name.startswith("source_") for name in failed):
        failure_class = "source_result_review_contract_failure"
    else:
        failure_class = "claim_authorization_boundary_plan_contract_failure"
    return {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_ready": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_claim_authorization_boundary_plan_static_review_authorized": bool(passed),
        "source_result_review_passed": source_decision.get("passed"),
        "source_safety_benefit_claim_supported": source_decision.get("safety_benefit_claim_supported"),
        "source_camp_over_dp_top1_claim_supported": source_decision.get("camp_over_dp_top1_claim_supported"),
        "claim_plan_only": True,
        "claim_executed_by_this_gate": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
