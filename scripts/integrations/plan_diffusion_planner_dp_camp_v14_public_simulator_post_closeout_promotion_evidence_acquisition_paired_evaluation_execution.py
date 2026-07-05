#!/usr/bin/env python3
"""Plan a future paired-evaluation execution gate without executing it."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_paired_evaluation_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_preflight_static_review",
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
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_evidence_acquisition_paired_evaluation_execution_plan_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_static_review_only"
)
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
PLAN_JSON_NAME = "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan.json"
PLAN_MD_NAME = "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan.md"

EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 154
EXPECTED_SOURCE_PREFLIGHT_CHECK_COUNT = SOURCE_REVIEW_MODULE.EXPECTED_PREFLIGHT_CHECK_COUNT
EXPECTED_INPUT_REQUIREMENT_COUNT = len(SOURCE_REVIEW_MODULE.EXPECTED_INPUT_REQUIREMENTS)
EXPECTED_PREFLIGHT_PLAN_COUNT = len(SOURCE_REVIEW_MODULE.EXPECTED_PREFLIGHT_ITEMS)
EXPECTED_EXECUTION_PLAN_ITEMS = (
    "lock_static_review_and_source_preflight_artifacts",
    "verify_fixed_dp_candidate_tensor_and_shadow_selection_identity",
    "materialize_strict_paired_run_key_index_plan",
    "plan_read_only_metric_extraction_without_training_inputs",
    "plan_safetycost_v1_delta_and_hard_gate_computation",
    "plan_coverage_uncertainty_and_bucket_reporting",
    "plan_fail_closed_no_go_evaluation",
    "emit_execution_preflight_ready_artifact_contract",
)
EXPECTED_REQUIRED_INPUTS = (
    "passed_paired_evaluation_preflight_static_review_artifact",
    "fixed_dp_candidate_tensor_manifest",
    "camp_shadow_selection_log_manifest",
    "dp_top1_candidate_index_manifest",
    "strict_paired_run_key_manifest",
    "safetycost_v1_and_hard_gate_config",
    "coverage_uncertainty_bucket_manifest",
    "artifact_hash_and_heads_manifest",
)
EXPECTED_PLANNED_OUTPUTS = (
    "paired_run_key_index",
    "paired_metric_delta_plan",
    "safetycost_v1_ci_plan",
    "coverage_uncertainty_bucket_plan",
    "no_go_evaluation_plan",
    "execution_preflight_artifact_contract",
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
    parser.add_argument("--safety_score_doc", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan",
        action="store_true",
        help="Explicit opt-in for read-only paired-evaluation execution planning.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        safety_score_doc=args.safety_score_doc,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan,
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
    safety_score_doc: Path,
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
        "safety_score_doc": safety_score_doc.resolve(),
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
    safety_score_text = BASE_MODULE._read_text(paths["safety_score_doc"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        BASE_MODULE._expect("execution_plan_enabled", enabled, True),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        BASE_MODULE._check("current_camp_head_is_sha", BASE_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        BASE_MODULE._check("source_static_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(BASE_MODULE._path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(
            BASE_MODULE._path_checks(
                f"artifact_{name}",
                path,
                require_file=True,
                allow_empty=(name == "stderr"),
            )
        )
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
    checks.extend(_safety_score_doc_checks(safety_score_text))
    checks.extend(_audit_checks(v14_text, status_text))

    required_inputs = _required_inputs(label=label, source_review=source_review)
    execution_plan = _execution_plan()
    planned_outputs = _planned_outputs()
    no_go = _no_go_register()
    checks.extend(_execution_plan_contract_checks(required_inputs, execution_plan, planned_outputs, no_go))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "plan_only": True,
            "read_only": True,
            "paired_evaluation_execution": False,
            "source_static_review_artifact_dir": str(artifact_dir),
            "source_static_review_json": str(paths["source_static_review_json"]),
            "safety_score_doc": str(paths["safety_score_doc"]),
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
        "required_inputs": required_inputs,
        "execution_plan": execution_plan,
        "planned_outputs": planned_outputs,
        "no_go_register": no_go,
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
        "# Post-Closeout Promotion Evidence Acquisition Paired Evaluation Execution Plan",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Required Inputs",
    ]
    for item in report["required_inputs"]:
        lines.append(f"- `{item['name']}`: `{item['requirement']}`")
    lines.extend(["", "## Execution Plan"])
    for item in report["execution_plan"]:
        lines.append(f"- `{item['name']}`: executes_paired_evaluation=`{item['executes_paired_evaluation']}`")
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
        BASE_MODULE._sha256sums_expect("artifact_review_sha256s_root_sha", artifact_files["review_sha256s"], root_sha256s, ("review/SHA256SUMS", "./review/SHA256SUMS", "SHA256SUMS")),
        BASE_MODULE._sha256sums_expect("source_review_json_nested_sha", artifact_files["review_json"], review_sha256s, (SOURCE_REVIEW_JSON_NAME, f"./{SOURCE_REVIEW_JSON_NAME}")),
        BASE_MODULE._sha256sums_expect("source_review_md_nested_sha", artifact_files["review_md"], review_sha256s, (SOURCE_REVIEW_MD_NAME, f"./{SOURCE_REVIEW_MD_NAME}")),
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
    analysis = BASE_MODULE._dict(source_review.get("analysis"))
    source_preflight = BASE_MODULE._dict(source_review.get("source_preflight_summary"))
    input_summary = BASE_MODULE._dict(source_review.get("input_requirement_summary"))
    plan_summary = BASE_MODULE._dict(source_review.get("preflight_plan_summary"))
    checks = [
        BASE_MODULE._expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        BASE_MODULE._expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("source_review_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_review_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_review_static_review_passed", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_preflight_static_review_passed"), True),
        BASE_MODULE._expect("source_review_execution_plan_authorized", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_authorized"), True),
        BASE_MODULE._expect("source_review_no_paired_execution", decision.get("paired_evaluation_executed_by_this_gate"), False),
        BASE_MODULE._expect("source_review_check_count", len(BASE_MODULE._list(source_review.get("review_checks"))), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        BASE_MODULE._expect("source_review_failed_check_count", len(BASE_MODULE._list(decision.get("failed_checks"))), 0),
        BASE_MODULE._expect("source_preflight_status", source_preflight.get("status"), SOURCE_REVIEW_MODULE.SOURCE_PREFLIGHT_STATUS),
        BASE_MODULE._expect("source_preflight_check_count", source_preflight.get("preflight_check_count"), EXPECTED_SOURCE_PREFLIGHT_CHECK_COUNT),
        BASE_MODULE._expect("source_preflight_failed_count", source_preflight.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_preflight_no_execution", source_preflight.get("paired_evaluation_executed_by_this_gate"), False),
        BASE_MODULE._expect("source_input_requirement_count", input_summary.get("count"), EXPECTED_INPUT_REQUIREMENT_COUNT),
        BASE_MODULE._expect("source_input_requirement_names", input_summary.get("names"), list(SOURCE_REVIEW_MODULE.EXPECTED_INPUT_REQUIREMENTS)),
        BASE_MODULE._expect("source_preflight_plan_count", plan_summary.get("count"), EXPECTED_PREFLIGHT_PLAN_COUNT),
        BASE_MODULE._expect("source_preflight_plan_names", plan_summary.get("names"), list(SOURCE_REVIEW_MODULE.EXPECTED_PREFLIGHT_ITEMS)),
        BASE_MODULE._expect("source_preflight_plan_no_execution", plan_summary.get("executes_paired_evaluation_values"), [False]),
        BASE_MODULE._expect("source_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("source_analysis_no_paired_execution", analysis.get("paired_evaluation_execution"), False),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(BASE_MODULE._expect(f"source_review_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(BASE_MODULE._expect(f"source_review_decision_{flag}", decision.get(flag), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(BASE_MODULE._expect(f"source_review_analysis_{flag}", analysis.get(flag), False))
    for flag in [
        "training_execution",
        "replay_execution",
        "candidate_generation",
        "dp_modification",
        "online_selector_change",
        "promotion_executed",
        "deployment_executed",
        "safety_or_camp_over_dp_claim",
    ]:
        checks.append(BASE_MODULE._expect(f"source_review_analysis_{flag}", analysis.get(flag), False))
    return checks


def _safety_score_doc_checks(text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._check("safety_score_doc_has_safetycost", "SafetyCost_v1" in text, "SafetyCost_v1", "present"),
        BASE_MODULE._check("safety_score_doc_has_claim_rule", "ci95_high(DeltaSafetyCost_v1) < 0" in text, "ci95_high(DeltaSafetyCost_v1) < 0", "present"),
        BASE_MODULE._check("safety_score_doc_has_hard_gate", "hard_gate_passed == true" in text, "hard_gate_passed == true", "present"),
        BASE_MODULE._check("safety_score_doc_forbids_formal_seeds", "no paired run uses seeds `11`, `12`, or `13`" in text, "no paired run uses seeds `11`, `12`, or `13`", "present"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("audit_latest_status_is_static_review_passed", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("audit_latest_eof_authorizes_execution_plan", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("audit_static_review_passed", BASE_MODULE._latest_value(v14_text, "post_closeout_promotion_evidence_acquisition_paired_evaluation_preflight_static_review_passed"), "True"),
        BASE_MODULE._expect("audit_execution_plan_authorized", BASE_MODULE._latest_value(v14_text, "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_authorized"), "True"),
        BASE_MODULE._expect("audit_paired_evaluation_not_executed", BASE_MODULE._latest_value(v14_text, "paired_evaluation_executed_by_current_gate"), "False"),
        BASE_MODULE._expect("audit_selector_promotion_false", BASE_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        BASE_MODULE._expect("audit_deployment_false", BASE_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        BASE_MODULE._expect("audit_safety_claim_false", BASE_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        BASE_MODULE._expect("audit_camp_over_dp_claim_false", BASE_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        BASE_MODULE._expect("status_doc_latest_status_is_static_review_passed", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("status_doc_latest_eof_authorizes_execution_plan", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
    ]


def _required_inputs(label: str | None, source_review: dict[str, Any]) -> list[dict[str, Any]]:
    source_summary = _source_static_review_summary(source_review)
    return [
        {"name": "passed_paired_evaluation_preflight_static_review_artifact", "requirement": "consume the passed static-review artifact and root SHA256SUMS as immutable source evidence", "source_status": source_summary["status"], "label": label},
        {"name": "fixed_dp_candidate_tensor_manifest", "requirement": "candidate tensor hashes, provenance, candidate count, and DP head must be locked before execution"},
        {"name": "camp_shadow_selection_log_manifest", "requirement": "CAMP shadow_selected_index rows must be default-off and have no executed-output effect"},
        {"name": "dp_top1_candidate_index_manifest", "requirement": "DP Top-1 comparator is candidate index 0 on the same fixed tensor records"},
        {"name": "strict_paired_run_key_manifest", "requirement": "paired rows must share route, scenario, seed, record id, and candidate tensor identity"},
        {"name": "safetycost_v1_and_hard_gate_config", "requirement": "SafetyCost v1 and hard gates are frozen before any execution plan is promoted"},
        {"name": "coverage_uncertainty_bucket_manifest", "requirement": "coverage, fallback, eligibility, bucket, and CI reporting must be predefined"},
        {"name": "artifact_hash_and_heads_manifest", "requirement": "execution artifacts must include JSON, MD, nested SHA256SUMS, root SHA256SUMS, HEADS, COMMAND, stdout, stderr, and run.exit"},
    ]


def _execution_plan() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "plan_only", "executes_paired_evaluation": False}
        for name in EXPECTED_EXECUTION_PLAN_ITEMS
    ]


def _planned_outputs() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "planned_not_materialized"}
        for name in EXPECTED_PLANNED_OUTPUTS
    ]


def _no_go_register() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "predeclared_reject_condition"}
        for name in SOURCE_REVIEW_MODULE.EXPECTED_NO_GO
    ]


def _execution_plan_contract_checks(
    required_inputs: list[dict[str, Any]],
    execution_plan: list[dict[str, Any]],
    planned_outputs: list[dict[str, Any]],
    no_go: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("required_input_names", [item.get("name") for item in required_inputs], list(EXPECTED_REQUIRED_INPUTS)),
        BASE_MODULE._expect("execution_plan_item_names", [item.get("name") for item in execution_plan], list(EXPECTED_EXECUTION_PLAN_ITEMS)),
        BASE_MODULE._expect("execution_plan_does_not_execute", sorted({item.get("executes_paired_evaluation") for item in execution_plan}), [False]),
        BASE_MODULE._expect("planned_output_names", [item.get("name") for item in planned_outputs], list(EXPECTED_PLANNED_OUTPUTS)),
        BASE_MODULE._expect("no_go_names", [item.get("name") for item in no_go], list(SOURCE_REVIEW_MODULE.EXPECTED_NO_GO)),
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


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "execution_plan_enabled" in failed:
        failure_class = "explicit_paired_evaluation_execution_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "safety_score_doc_")) for name in failed):
        failure_class = "source_static_review_contract_failure"
    elif any(name.startswith(("required_", "execution_plan_", "planned_", "no_go_")) for name in failed):
        failure_class = "paired_evaluation_execution_plan_contract_failure"
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
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_ready": passed,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_static_review_authorized": passed,
        "paired_evaluation_executed_by_this_gate": False,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "static_review_paired_evaluation_execution_plan_only" if passed else "repair_contract_before_rerun",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
