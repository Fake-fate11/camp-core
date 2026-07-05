#!/usr/bin/env python3
"""Static review for the post-closeout paired-evaluation execution preflight."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_preflight_module():
    preflight_path = Path(__file__).resolve().with_name(
        "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_paired_evaluation_execution.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight",
        preflight_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PREFLIGHT_MODULE = _load_preflight_module()
BASE_MODULE = PREFLIGHT_MODULE.BASE_MODULE

FIXED_DP_HEAD = PREFLIGHT_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PREFLIGHT_MODULE.SCORE_EXPRESSION
SOURCE_PREFLIGHT_SCHEMA = PREFLIGHT_MODULE.SCHEMA_VERSION
SOURCE_PREFLIGHT_STATUS = PREFLIGHT_MODULE.READY_STATUS
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PREFLIGHT_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_only"
)

SOURCE_PREFLIGHT_JSON_NAME = PREFLIGHT_MODULE.PREFLIGHT_JSON_NAME
SOURCE_PREFLIGHT_MD_NAME = PREFLIGHT_MODULE.PREFLIGHT_MD_NAME
REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review.md"
)

EXPECTED_PREFLIGHT_CHECK_COUNT = 198
EXPECTED_SOURCE_STATIC_REVIEW_CHECK_COUNT = PREFLIGHT_MODULE.EXPECTED_SOURCE_REVIEW_CHECK_COUNT
EXPECTED_SOURCE_PLAN_CHECK_COUNT = PREFLIGHT_MODULE.EXPECTED_SOURCE_PLAN_CHECK_COUNT
EXPECTED_SOURCE_REQUIRED_INPUT_COUNT = PREFLIGHT_MODULE.EXPECTED_SOURCE_REQUIRED_INPUT_COUNT
EXPECTED_SOURCE_EXECUTION_PLAN_COUNT = PREFLIGHT_MODULE.EXPECTED_SOURCE_EXECUTION_PLAN_COUNT
EXPECTED_SOURCE_PLANNED_OUTPUT_COUNT = PREFLIGHT_MODULE.EXPECTED_SOURCE_PLANNED_OUTPUT_COUNT
EXPECTED_SOURCE_NO_GO_COUNT = PREFLIGHT_MODULE.EXPECTED_SOURCE_NO_GO_COUNT
EXPECTED_RECORD_COUNT = PREFLIGHT_MODULE.EXPECTED_RECORD_COUNT
EXPECTED_SHADOW_DIFF_RECORDS = PREFLIGHT_MODULE.EXPECTED_SHADOW_DIFF_RECORDS
EXPECTED_EVIDENCE_LOCKS = PREFLIGHT_MODULE.EXPECTED_EVIDENCE_LOCKS
EXPECTED_REQUIRED_INPUT_MANIFESTS = PREFLIGHT_MODULE.EXPECTED_REQUIRED_INPUT_MANIFESTS
EXPECTED_PREFLIGHT_ITEMS = PREFLIGHT_MODULE.EXPECTED_PREFLIGHT_ITEMS
EXPECTED_FUTURE_OUTPUTS = PREFLIGHT_MODULE.EXPECTED_FUTURE_OUTPUTS
EXPECTED_NO_GO = PREFLIGHT_MODULE.EXPECTED_NO_GO
BLOCKED_ACTIONS = PREFLIGHT_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = PREFLIGHT_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = PREFLIGHT_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired_evaluation_execution_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--paired_evaluation_execution_preflight_json", type=Path, required=True)
    parser.add_argument("--paired_evaluation_execution_preflight_md", type=Path, required=True)
    parser.add_argument("--paired_evaluation_execution_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--preflight_script_py", type=Path, required=True)
    parser.add_argument("--preflight_test_py", type=Path, required=True)
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
        "--enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review",
        action="store_true",
        help="Explicit opt-in for static review of the paired-evaluation execution preflight.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        paired_evaluation_execution_preflight_artifact_dir=args.paired_evaluation_execution_preflight_artifact_dir,
        paired_evaluation_execution_preflight_json=args.paired_evaluation_execution_preflight_json,
        paired_evaluation_execution_preflight_md=args.paired_evaluation_execution_preflight_md,
        paired_evaluation_execution_preflight_sha256s=args.paired_evaluation_execution_preflight_sha256s,
        preflight_script_py=args.preflight_script_py,
        preflight_test_py=args.preflight_test_py,
        safety_score_doc=args.safety_score_doc,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    paired_evaluation_execution_preflight_artifact_dir: Path,
    paired_evaluation_execution_preflight_json: Path,
    paired_evaluation_execution_preflight_md: Path,
    paired_evaluation_execution_preflight_sha256s: Path,
    preflight_script_py: Path,
    preflight_test_py: Path,
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
    artifact_dir = paired_evaluation_execution_preflight_artifact_dir.resolve()
    paths = {
        "paired_evaluation_execution_preflight_json": paired_evaluation_execution_preflight_json.resolve(),
        "paired_evaluation_execution_preflight_md": paired_evaluation_execution_preflight_md.resolve(),
        "paired_evaluation_execution_preflight_sha256s": paired_evaluation_execution_preflight_sha256s.resolve(),
        "preflight_script_py": preflight_script_py.resolve(),
        "preflight_test_py": preflight_test_py.resolve(),
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
        "preflight_json": artifact_dir / "preflight" / SOURCE_PREFLIGHT_JSON_NAME,
        "preflight_md": artifact_dir / "preflight" / SOURCE_PREFLIGHT_MD_NAME,
        "preflight_sha256s": artifact_dir / "preflight" / "SHA256SUMS",
    }
    source_preflight = BASE_MODULE._read_json_dict(paths["paired_evaluation_execution_preflight_json"])
    root_sha256s = BASE_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    preflight_sha256s = BASE_MODULE._read_sha256sums(
        paths["paired_evaluation_execution_preflight_sha256s"]
    )
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(artifact_files["heads"]))
    script_text = BASE_MODULE._read_text(paths["preflight_script_py"])
    test_text = BASE_MODULE._read_text(paths["preflight_test_py"])
    safety_score_text = BASE_MODULE._read_text(paths["safety_score_doc"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        BASE_MODULE._expect("static_review_enabled", enabled, True),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        BASE_MODULE._check("current_camp_head_is_sha", BASE_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        BASE_MODULE._check("paired_evaluation_execution_preflight_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
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
            BASE_MODULE._expect(
                "preflight_json_matches_artifact_layout",
                paths["paired_evaluation_execution_preflight_json"],
                artifact_files["preflight_json"],
            ),
            BASE_MODULE._expect(
                "preflight_md_matches_artifact_layout",
                paths["paired_evaluation_execution_preflight_md"],
                artifact_files["preflight_md"],
            ),
            BASE_MODULE._expect(
                "preflight_sha256s_matches_artifact_layout",
                paths["paired_evaluation_execution_preflight_sha256s"],
                artifact_files["preflight_sha256s"],
            ),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, preflight_sha256s))
    checks.extend(_heads_checks(heads, source_preflight))
    checks.extend(_source_preflight_contract_checks(source_preflight))
    checks.extend(_source_surface_checks(script_text, test_text, safety_score_text))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "read_only": True,
            "paired_evaluation_execution": False,
            "source_paired_evaluation_execution_preflight_artifact_dir": str(artifact_dir),
            "source_paired_evaluation_execution_preflight_json": str(paths["paired_evaluation_execution_preflight_json"]),
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
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "source_static_review_summary": _source_static_review_summary(source_preflight),
        "runtime_result_summary": BASE_MODULE._dict(source_preflight.get("runtime_result_summary")),
        "delta_review_summary": BASE_MODULE._dict(source_preflight.get("delta_review_summary")),
        "readiness_result_summary": BASE_MODULE._dict(source_preflight.get("readiness_result_summary")),
        "preflight_contract_summary": _preflight_contract_summary(source_preflight),
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
        "# Post-Closeout Promotion Evidence Acquisition Paired Evaluation Execution Preflight Static Review",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Source Preflight Summary",
    ]
    for key, value in report["source_preflight_summary"].items():
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
    preflight_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        BASE_MODULE._sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        BASE_MODULE._sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        BASE_MODULE._sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        BASE_MODULE._sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        BASE_MODULE._sha256sums_expect("artifact_preflight_json_root_sha", artifact_files["preflight_json"], root_sha256s, (f"preflight/{SOURCE_PREFLIGHT_JSON_NAME}", f"./preflight/{SOURCE_PREFLIGHT_JSON_NAME}", SOURCE_PREFLIGHT_JSON_NAME)),
        BASE_MODULE._sha256sums_expect("artifact_preflight_md_root_sha", artifact_files["preflight_md"], root_sha256s, (f"preflight/{SOURCE_PREFLIGHT_MD_NAME}", f"./preflight/{SOURCE_PREFLIGHT_MD_NAME}", SOURCE_PREFLIGHT_MD_NAME)),
        BASE_MODULE._sha256sums_expect("artifact_preflight_sha256s_root_sha", artifact_files["preflight_sha256s"], root_sha256s, ("preflight/SHA256SUMS", "./preflight/SHA256SUMS", "SHA256SUMS")),
        BASE_MODULE._sha256sums_expect("source_preflight_json_nested_sha", artifact_files["preflight_json"], preflight_sha256s, (SOURCE_PREFLIGHT_JSON_NAME, f"./{SOURCE_PREFLIGHT_JSON_NAME}")),
        BASE_MODULE._sha256sums_expect("source_preflight_md_nested_sha", artifact_files["preflight_md"], preflight_sha256s, (SOURCE_PREFLIGHT_MD_NAME, f"./{SOURCE_PREFLIGHT_MD_NAME}")),
        BASE_MODULE._expect("artifact_run_exit_zero", BASE_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = BASE_MODULE._dict(source_preflight.get("analysis"))
    return [
        BASE_MODULE._expect("artifact_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        BASE_MODULE._expect("artifact_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        BASE_MODULE._expect("artifact_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        BASE_MODULE._expect("artifact_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_preflight_contract_checks(source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_preflight.get("final_decision"))
    analysis = BASE_MODULE._dict(source_preflight.get("analysis"))
    source_static_review = BASE_MODULE._dict(source_preflight.get("source_static_review_summary"))
    runtime_summary = BASE_MODULE._dict(source_preflight.get("runtime_result_summary"))
    delta_summary = BASE_MODULE._dict(source_preflight.get("delta_review_summary"))
    readiness_summary = BASE_MODULE._dict(source_preflight.get("readiness_result_summary"))
    evidence_locks = BASE_MODULE._list(source_preflight.get("evidence_locks"))
    input_manifests = BASE_MODULE._list(source_preflight.get("required_input_manifests"))
    preflight_plan = BASE_MODULE._list(source_preflight.get("preflight_plan"))
    future_outputs = BASE_MODULE._list(source_preflight.get("future_outputs"))
    no_go = BASE_MODULE._list(source_preflight.get("no_go_register"))
    checks = [
        BASE_MODULE._expect("source_preflight_schema", source_preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA),
        BASE_MODULE._expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
        BASE_MODULE._expect("source_preflight_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_preflight_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_preflight_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_preflight_ready", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_ready"), True),
        BASE_MODULE._expect("source_preflight_static_review_authorized", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_authorized"), True),
        BASE_MODULE._expect("source_preflight_no_paired_execution", decision.get("paired_evaluation_executed_by_this_gate"), False),
        BASE_MODULE._expect("source_preflight_execution_not_authorized_by_source", decision.get("paired_evaluation_execution_authorized"), False),
        BASE_MODULE._expect("source_preflight_check_count", len(BASE_MODULE._list(source_preflight.get("preflight_checks"))), EXPECTED_PREFLIGHT_CHECK_COUNT),
        BASE_MODULE._expect("source_preflight_failed_check_count", len(BASE_MODULE._list(decision.get("failed_checks"))), 0),
        BASE_MODULE._expect("source_static_review_status", source_static_review.get("status"), PREFLIGHT_MODULE.SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("source_static_review_check_count", source_static_review.get("review_check_count"), EXPECTED_SOURCE_STATIC_REVIEW_CHECK_COUNT),
        BASE_MODULE._expect("source_static_review_failed_count", source_static_review.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_static_review_authorized_next", source_static_review.get("authorized_next_work"), PREFLIGHT_MODULE.AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_execution_plan_check_count", source_static_review.get("source_plan_check_count"), EXPECTED_SOURCE_PLAN_CHECK_COUNT),
        BASE_MODULE._expect("runtime_record_count", runtime_summary.get("record_count"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("runtime_executed_top1_records", runtime_summary.get("executed_top1_records"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("runtime_shadow_diff_records", runtime_summary.get("shadow_selected_index_differs_from_executed_index_records"), EXPECTED_SHADOW_DIFF_RECORDS),
        BASE_MODULE._expect("delta_record_count", delta_summary.get("record_count"), EXPECTED_RECORD_COUNT),
        BASE_MODULE._expect("delta_static_objective_supported", delta_summary.get("static_objective_delta_supported"), True),
        BASE_MODULE._expect("delta_shadow_diff_records", delta_summary.get("shadow_selected_index_differs_from_executed_index_records"), EXPECTED_SHADOW_DIFF_RECORDS),
        BASE_MODULE._expect("readiness_result_passed", readiness_summary.get("passed"), True),
        BASE_MODULE._expect("readiness_direct_promotion_false", readiness_summary.get("direct_promotion_recommendation"), False),
        BASE_MODULE._expect("readiness_metrics_manifest_count", readiness_summary.get("metrics_manifest_count"), 6),
        BASE_MODULE._expect("readiness_no_go_summary_count", readiness_summary.get("no_go_summary_count"), EXPECTED_SOURCE_NO_GO_COUNT),
        BASE_MODULE._expect("readiness_evidence_matrix_count", readiness_summary.get("evidence_matrix_count"), 6),
        BASE_MODULE._expect("source_evidence_lock_names", [item.get("name") for item in evidence_locks], list(EXPECTED_EVIDENCE_LOCKS)),
        BASE_MODULE._expect("source_required_input_manifest_names", [item.get("name") for item in input_manifests], list(EXPECTED_REQUIRED_INPUT_MANIFESTS)),
        BASE_MODULE._expect("source_preflight_plan_names", [item.get("name") for item in preflight_plan], list(EXPECTED_PREFLIGHT_ITEMS)),
        BASE_MODULE._expect("source_preflight_plan_no_execution", sorted({item.get("executes_paired_evaluation") for item in preflight_plan}), [False]),
        BASE_MODULE._expect("source_future_output_names", [item.get("name") for item in future_outputs], list(EXPECTED_FUTURE_OUTPUTS)),
        BASE_MODULE._expect("source_no_go_names", [item.get("name") for item in no_go], list(EXPECTED_NO_GO)),
        BASE_MODULE._expect("source_preflight_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        BASE_MODULE._expect("source_analysis_no_paired_evaluation_execution", analysis.get("paired_evaluation_execution"), False),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(BASE_MODULE._expect(f"source_preflight_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(BASE_MODULE._expect(f"source_preflight_decision_{flag}", decision.get(flag), False))
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(BASE_MODULE._expect(f"source_preflight_analysis_{flag}", analysis.get(flag), False))
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
        checks.append(BASE_MODULE._expect(f"source_preflight_analysis_{flag}", analysis.get(flag), False))
    return checks


def _source_surface_checks(script_text: str, test_text: str, safety_score_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._check("preflight_script_schema_token", "promotion_evidence_acquisition_paired_evaluation_execution_preflight_v1" in script_text, "promotion_evidence_acquisition_paired_evaluation_execution_preflight_v1", "present"),
        BASE_MODULE._check("preflight_script_static_review_next", "paired_evaluation_execution_preflight_static_review_only" in script_text, "paired_evaluation_execution_preflight_static_review_only", "present"),
        BASE_MODULE._check("preflight_script_evidence_locks", "EXPECTED_EVIDENCE_LOCKS" in script_text, "EXPECTED_EVIDENCE_LOCKS", "present"),
        BASE_MODULE._check("preflight_script_required_manifests", "EXPECTED_REQUIRED_INPUT_MANIFESTS" in script_text, "EXPECTED_REQUIRED_INPUT_MANIFESTS", "present"),
        BASE_MODULE._check("preflight_script_execution_not_authorized", '"paired_evaluation_execution_authorized": False' in script_text, '"paired_evaluation_execution_authorized": False', "present"),
        BASE_MODULE._check("preflight_test_rejects_hash_drift", "rejects_hash_drift" in test_text, "rejects_hash_drift", "present"),
        BASE_MODULE._check("preflight_test_rejects_runtime_claim_leak", "rejects_runtime_claim_leak" in test_text, "rejects_runtime_claim_leak", "present"),
        BASE_MODULE._check("preflight_test_rejects_delta_claim_scope_drift", "rejects_delta_claim_scope_drift" in test_text, "rejects_delta_claim_scope_drift", "present"),
        BASE_MODULE._check("preflight_test_requires_enable", "requires_enable" in test_text, "requires_enable", "present"),
        BASE_MODULE._check("safety_score_doc_claim_rule", "ci95_high(DeltaSafetyCost_v1) < 0" in safety_score_text, "ci95_high(DeltaSafetyCost_v1) < 0", "present"),
        BASE_MODULE._check("safety_score_doc_forbids_formal_seeds", "no paired run uses seeds `11`, `12`, or `13`" in safety_score_text, "no paired run uses seeds `11`, `12`, or `13`", "present"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("audit_latest_status_is_execution_preflight_ready", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS),
        BASE_MODULE._expect("audit_latest_eof_authorizes_static_review", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("audit_execution_preflight_ready", BASE_MODULE._latest_value(v14_text, "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_ready"), "True"),
        BASE_MODULE._expect("audit_execution_preflight_static_review_authorized", BASE_MODULE._latest_value(v14_text, "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_authorized"), "True"),
        BASE_MODULE._expect("audit_paired_evaluation_not_executed", BASE_MODULE._latest_value(v14_text, "paired_evaluation_executed_by_current_gate"), "False"),
        BASE_MODULE._expect("audit_paired_evaluation_execution_not_authorized_yet", BASE_MODULE._latest_value(v14_text, "paired_evaluation_execution_authorized"), "False"),
        BASE_MODULE._expect("audit_selector_promotion_false", BASE_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        BASE_MODULE._expect("audit_deployment_false", BASE_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        BASE_MODULE._expect("audit_safety_claim_false", BASE_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        BASE_MODULE._expect("audit_camp_over_dp_claim_false", BASE_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        BASE_MODULE._expect("status_doc_latest_status_is_execution_preflight_ready", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS),
        BASE_MODULE._expect("status_doc_latest_eof_authorizes_static_review", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
    ]


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_preflight.get("final_decision"))
    return {
        "schema_version": source_preflight.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "preflight_check_count": len(BASE_MODULE._list(source_preflight.get("preflight_checks"))),
        "failed_check_count": len(BASE_MODULE._list(decision.get("failed_checks"))),
        "paired_evaluation_executed_by_this_gate": decision.get("paired_evaluation_executed_by_this_gate"),
        "paired_evaluation_execution_authorized": decision.get("paired_evaluation_execution_authorized"),
    }


def _source_static_review_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    return BASE_MODULE._dict(source_preflight.get("source_static_review_summary"))


def _preflight_contract_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_lock_count": len(BASE_MODULE._list(source_preflight.get("evidence_locks"))),
        "required_input_manifest_count": len(BASE_MODULE._list(source_preflight.get("required_input_manifests"))),
        "preflight_plan_count": len(BASE_MODULE._list(source_preflight.get("preflight_plan"))),
        "future_output_count": len(BASE_MODULE._list(source_preflight.get("future_outputs"))),
        "no_go_count": len(BASE_MODULE._list(source_preflight.get("no_go_register"))),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_paired_evaluation_execution_preflight_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "preflight_", "runtime_", "delta_", "readiness_", "safety_score_doc_")) for name in failed):
        failure_class = "source_paired_evaluation_execution_preflight_static_review_contract_failure"
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
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_passed": passed,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_authorized": passed,
        "paired_evaluation_executed_by_this_gate": False,
        "paired_evaluation_execution_authorized": passed,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "execute_paired_evaluation_only" if passed else "repair_contract_before_rerun",
        "immediate_action": "execute_paired_evaluation_only" if passed else "repair_contract_before_rerun",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
