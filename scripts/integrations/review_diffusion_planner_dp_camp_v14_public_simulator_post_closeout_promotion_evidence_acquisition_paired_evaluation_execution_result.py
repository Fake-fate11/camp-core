#!/usr/bin/env python3
"""Read-only result review for the post-closeout paired-evaluation execution."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_execution_module():
    script_path = Path(__file__).resolve().with_name(
        "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_paired_evaluation.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


EXECUTION_MODULE = _load_execution_module()

FIXED_DP_HEAD = EXECUTION_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = EXECUTION_MODULE.SCORE_EXPRESSION
SOURCE_EXECUTION_SCHEMA = EXECUTION_MODULE.SCHEMA_VERSION
SOURCE_EXECUTION_STATUS = EXECUTION_MODULE.READY_STATUS
SOURCE_EXECUTION_JSON_NAME = EXECUTION_MODULE.EXECUTION_JSON_NAME
SOURCE_EXECUTION_MD_NAME = EXECUTION_MODULE.EXECUTION_MD_NAME
BLOCKED_ACTIONS = EXECUTION_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = EXECUTION_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_evidence_acquisition_paired_evaluation_execution_result_review_v1"
)
AUTHORIZED_CURRENT_WORK = EXECUTION_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_only"
)

REVIEW_JSON_NAME = "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review.json"
REVIEW_MD_NAME = "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_execution_json", type=Path, required=True)
    parser.add_argument("--source_execution_md", type=Path, required=True)
    parser.add_argument("--source_execution_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_record_count", type=int, default=EXECUTION_MODULE.EXPECTED_RECORD_COUNT)
    parser.add_argument(
        "--expected_shadow_diff_records",
        type=int,
        default=2832,
    )
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_execution_artifact_dir=args.source_execution_artifact_dir,
        source_execution_json=args.source_execution_json,
        source_execution_md=args.source_execution_md,
        source_execution_sha256s=args.source_execution_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_record_count=args.expected_record_count,
        expected_shadow_diff_records=args.expected_shadow_diff_records,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_execution_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_record_count: int = EXECUTION_MODULE.EXPECTED_RECORD_COUNT,
    expected_shadow_diff_records: int = 2832,
    enabled: bool = False,
) -> dict[str, Any]:
    source_execution_artifact_dir = source_execution_artifact_dir.resolve()
    source_execution_json = source_execution_json.resolve()
    source_execution_md = source_execution_md.resolve()
    source_execution_sha256s = source_execution_sha256s.resolve()
    output_dir = output_dir.resolve()
    source_execution = _read_json_dict(source_execution_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    heads = _parse_key_values(_read_text(source_execution_artifact_dir / "HEADS"))
    run_exit = _read_text(source_execution_artifact_dir / "run.exit").strip()
    root_sha256s = _read_sha256sums(source_execution_artifact_dir / "SHA256SUMS")
    nested_sha256s = _read_sha256sums(source_execution_sha256s)
    checks = _checks(
        enabled=enabled,
        source_execution_artifact_dir=source_execution_artifact_dir,
        source_execution_json=source_execution_json,
        source_execution_md=source_execution_md,
        source_execution_sha256s=source_execution_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
        source_execution=source_execution,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_shadow_diff_records=expected_shadow_diff_records,
    )
    passed = all(check["passed"] for check in checks)
    decision = _decision(passed=passed, checks=checks, source_execution=source_execution)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "result_review_only": True,
            "paired_evaluation_executed_by_review": False,
            "replay_executed_by_review": False,
            "training_executed_by_review": False,
            "candidate_generation_executed_by_review": False,
            "dp_modified_by_review": False,
            "promotion_executed_by_review": False,
            "deployment_executed_by_review": False,
            "online_selector_change_by_review": False,
            "safety_or_camp_over_dp_claim_by_review": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_execution_artifact_dir": str(source_execution_artifact_dir),
            "source_execution_json": str(source_execution_json),
            "source_execution_md": str(source_execution_md),
            "source_execution_sha256s": str(source_execution_sha256s),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "source_artifact_hashes": _source_hashes(
            source_execution_artifact_dir=source_execution_artifact_dir,
            source_execution_json=source_execution_json,
            source_execution_md=source_execution_md,
            source_execution_sha256s=source_execution_sha256s,
        ),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": heads.get("CAMP_HEAD"),
            "source_artifact_camp_origin_main": heads.get("CAMP_ORIGIN_MAIN"),
            "source_artifact_dp_head": heads.get("DP_HEAD"),
        },
        "source_execution_summary": _source_execution_summary(source_execution),
        "evidence_gap_summary": _evidence_gap_summary(source_execution),
        "review_checks": checks,
        "final_decision": decision,
    }


def _checks(
    *,
    enabled: bool,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_execution_sha256s: Path,
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    source_execution: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_shadow_diff_records: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = _dict(source_execution.get("final_decision"))
    record_summary = _dict(source_execution.get("paired_record_summary"))
    run_key_index = _dict(source_execution.get("paired_run_key_index"))
    tensor_table = _dict(source_execution.get("candidate_tensor_identity_table"))
    score_table = _dict(source_execution.get("shadow_vs_top1_metric_delta_table"))
    selection_delta = _dict(score_table.get("selection_score_delta"))
    raw_delta = _dict(score_table.get("raw_affine_score_delta"))
    safety_table = _dict(source_execution.get("safetycost_v1_confidence_interval_table"))
    no_go = _dict(source_execution.get("paired_execution_no_go_report"))

    def expect(name: str, actual: Any, expected: Any) -> None:
        checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})

    def require(name: str, passed: bool, actual: Any = None, expected: Any = True) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "actual": actual if actual is not None else bool(passed),
                "expected": expected,
            }
        )

    latest_audit_status = _latest_value(v14_text, "current_v14_status")
    latest_audit_next = _latest_value(v14_text, "next_work_target")
    latest_status_doc_status = _latest_value(status_text, "current_v14_status")
    latest_status_doc_next = _latest_value(status_text, "next_work_target")

    require("result_review_enabled", enabled)
    require("source_execution_artifact_dir_exists", source_execution_artifact_dir.is_dir())
    require("source_execution_json_exists", source_execution_json.is_file())
    require("source_execution_md_exists", source_execution_md.is_file())
    require("source_execution_sha256s_exists", source_execution_sha256s.is_file())
    require("source_execution_heads_exists", (source_execution_artifact_dir / "HEADS").is_file())
    require("source_execution_command_exists", (source_execution_artifact_dir / "COMMAND").is_file())
    require("source_execution_stdout_exists", (source_execution_artifact_dir / "stdout").is_file())
    require("source_execution_stderr_exists", (source_execution_artifact_dir / "stderr").is_file())
    require("source_execution_run_exit_exists", (source_execution_artifact_dir / "run.exit").is_file())
    require("source_execution_root_sha256s_exists", (source_execution_artifact_dir / "SHA256SUMS").is_file())

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", heads.get("DP_HEAD"), required_dp_head)
    expect("source_execution_run_exit", run_exit, "0")
    expect("audit_latest_status", latest_audit_status, SOURCE_EXECUTION_STATUS)
    expect("audit_latest_next_work", latest_audit_next, AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", latest_status_doc_status, SOURCE_EXECUTION_STATUS)
    expect("status_doc_latest_next_work", latest_status_doc_next, AUTHORIZED_CURRENT_WORK)

    expect("source_execution_schema", source_execution.get("schema_version"), SOURCE_EXECUTION_SCHEMA)
    expect("source_execution_passed", decision.get("passed"), True)
    expect("source_execution_status", decision.get("status"), SOURCE_EXECUTION_STATUS)
    expect("source_execution_failed_checks", decision.get("failed_checks"), [])
    expect("source_execution_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_execution_paired_executed", decision.get("paired_evaluation_executed_by_this_gate"), True)
    expect("source_execution_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False)
    expect("source_execution_actual_safetycost_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_execution_decision_{action}", decision.get(action), False)
    for flag in FALSE_EXECUTION_FLAGS:
        expect(f"source_execution_decision_{flag}", decision.get(flag), False)

    expect("paired_record_count", record_summary.get("record_count"), expected_record_count)
    expect("paired_run_key_count", run_key_index.get("paired_run_key_count"), expected_record_count)
    expect("unique_paired_run_key_count", run_key_index.get("unique_paired_run_key_count"), expected_record_count)
    expect("duplicate_paired_run_key_count", run_key_index.get("duplicate_paired_run_key_count"), 0)
    expect("executed_top1_records", record_summary.get("executed_top1_records"), expected_record_count)
    expect("shadow_diff_records", record_summary.get("shadow_selected_index_differs_from_executed_index_records"), expected_shadow_diff_records)
    expect("candidate_tensor_identity_records", tensor_table.get("identity_match_records"), expected_record_count)
    expect("candidate_tensor_mutation_records", tensor_table.get("candidate_tensor_mutation_records"), 0)
    expect("formal_seed_records", record_summary.get("formal_seed_records"), 0)
    expect("full36_path_records", record_summary.get("full36_path_records"), 0)
    expect("non_affine_score_records", record_summary.get("non_affine_score_records"), 0)
    expect("non_simplex_weight_records", record_summary.get("non_simplex_weight_records"), 0)
    expect("selection_score_worse_records", selection_delta.get("worse_records"), 0)
    expect("selection_score_uncomparable_records", selection_delta.get("uncomparable_records"), 0)
    require("selection_score_better_records_positive", int(selection_delta.get("better_records") or 0) > 0)
    expect("raw_affine_score_records", raw_delta.get("records"), expected_record_count)
    expect("no_go_failed_count", no_go.get("failed_count"), 0)
    expect("actual_safetycost_v1_available", safety_table.get("actual_safetycost_v1_available"), False)
    expect("actual_safetycost_v1_claim_rule_evaluable", safety_table.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect("safetycost_v1_claim_authorized", safety_table.get("safetycost_v1_claim_authorized"), False)
    expect("camp_over_dp_top1_claim_authorized", safety_table.get("camp_over_dp_top1_claim_authorized"), False)

    _expect_sha(checks, "nested_execution_json_sha", nested_sha256s, source_execution_json.name, source_execution_json)
    _expect_sha(checks, "nested_execution_md_sha", nested_sha256s, source_execution_md.name, source_execution_md)
    _expect_sha(checks, "root_execution_json_sha", root_sha256s, f"./evaluation/{source_execution_json.name}", source_execution_json)
    _expect_sha(checks, "root_execution_md_sha", root_sha256s, f"./evaluation/{source_execution_md.name}", source_execution_md)
    _expect_sha(checks, "root_execution_sha256s_sha", root_sha256s, "./evaluation/SHA256SUMS", source_execution_sha256s)
    return checks


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_execution: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "result_review_enabled" in failed:
        failure_class = "explicit_paired_evaluation_execution_result_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_execution_") for name in failed):
        failure_class = "source_paired_evaluation_execution_contract_failure"
    elif any(name.startswith(("paired_", "candidate_", "selection_", "raw_", "no_go_", "actual_safety")) for name in failed):
        failure_class = "paired_evaluation_result_contract_failure"
    else:
        failure_class = "artifact_hash_or_review_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review_passed": bool(passed),
        "paired_evaluation_executed_by_this_gate": False,
        "paired_evaluation_execution_reviewed_by_this_gate": True,
        "actual_safetycost_v1_available": _dict(source_execution.get("final_decision")).get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": _dict(source_execution.get("final_decision")).get("actual_safetycost_v1_claim_rule_evaluable"),
        "actual_safetycost_evidence_gap_closure_plan_authorized": bool(passed),
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "plan_actual_safetycost_evidence_gap_closure_only" if passed else "repair_or_rerun_same_review_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _source_execution_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_execution.get("final_decision"))
    records = _dict(source_execution.get("paired_record_summary"))
    run_keys = _dict(source_execution.get("paired_run_key_index"))
    tensor = _dict(source_execution.get("candidate_tensor_identity_table"))
    score = _dict(_dict(source_execution.get("shadow_vs_top1_metric_delta_table")).get("selection_score_delta"))
    no_go = _dict(source_execution.get("paired_execution_no_go_report"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "paired_record_count": records.get("record_count"),
        "unique_paired_run_key_count": run_keys.get("unique_paired_run_key_count"),
        "shadow_diff_records": records.get("shadow_selected_index_differs_from_executed_index_records"),
        "candidate_tensor_identity_records": tensor.get("identity_match_records"),
        "candidate_tensor_mutation_records": tensor.get("candidate_tensor_mutation_records"),
        "selection_score_better_records": score.get("better_records"),
        "selection_score_worse_records": score.get("worse_records"),
        "no_go_failed_count": no_go.get("failed_count"),
    }


def _evidence_gap_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    safety = _dict(source_execution.get("safetycost_v1_confidence_interval_table"))
    return {
        "actual_safetycost_v1_available": safety.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": safety.get("actual_safetycost_v1_claim_rule_evaluable"),
        "unavailable_reason": safety.get("unavailable_reason"),
        "safetycost_v1_claim_authorized": safety.get("safetycost_v1_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": safety.get("camp_over_dp_top1_claim_authorized"),
        "next_evidence_need": "paired shadow-selected run-level closed-loop outcome summaries",
    }


def _source_hashes(
    *,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_execution_sha256s: Path,
) -> dict[str, Any]:
    root_sha = source_execution_artifact_dir / "SHA256SUMS"
    return {
        "source_execution_json_sha256": _sha256(source_execution_json),
        "source_execution_md_sha256": _sha256(source_execution_md),
        "source_execution_sha256s_sha256": _sha256(source_execution_sha256s),
        "source_execution_root_sha256s_sha256": _sha256(root_sha) if root_sha.is_file() else None,
        "heads_sha256": _sha256(source_execution_artifact_dir / "HEADS"),
        "command_sha256": _sha256(source_execution_artifact_dir / "COMMAND"),
        "stdout_sha256": _sha256(source_execution_artifact_dir / "stdout"),
        "stderr_sha256": _sha256(source_execution_artifact_dir / "stderr"),
        "run_exit_sha256": _sha256(source_execution_artifact_dir / "run.exit"),
    }


def _expect_sha(
    checks: list[dict[str, Any]],
    name: str,
    sums: dict[str, str],
    key: str,
    path: Path,
) -> None:
    actual = sums.get(key) or sums.get(key.removeprefix("./"))
    expected = _sha256(path) if path.is_file() else None
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{_sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_execution_summary"]
    gap = report["evidence_gap_summary"]
    lines = [
        "# v14 Paired Evaluation Execution Result Review",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Execution",
        "",
        f"- Paired records: `{summary['paired_record_count']}`",
        f"- Unique paired keys: `{summary['unique_paired_run_key_count']}`",
        f"- Shadow differs from Top-1 records: `{summary['shadow_diff_records']}`",
        f"- Candidate tensor mutation records: `{summary['candidate_tensor_mutation_records']}`",
        f"- Selection-score better/worse records: `{summary['selection_score_better_records']} / {summary['selection_score_worse_records']}`",
        f"- No-go failed count: `{summary['no_go_failed_count']}`",
        "",
        "## Evidence Gap",
        "",
        f"- Actual SafetyCost v1 available: `{gap['actual_safetycost_v1_available']}`",
        f"- Claim rule evaluable: `{gap['actual_safetycost_v1_claim_rule_evaluable']}`",
        f"- Unavailable reason: `{gap['unavailable_reason']}`",
        f"- Next evidence need: `{gap['next_evidence_need']}`",
        "",
        "## Boundary",
        "",
        "- Review only: no replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_sha256sums(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if digest and name:
            sums[name.strip()] = digest.strip()
    return sums


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip()
    return values


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
