#!/usr/bin/env python3
"""Read-only v14 runtime shadow replay result review.

This gate consumes an existing runtime shadow replay execution artifact and its
existing execution audit report. It does not run replay, generate candidates,
train CAMP, modify Diffusion Planner, promote artifacts, deploy, or make
safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_v1"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CURRENT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_execution_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_promotion_decision_plan_only_after_explicit_"
    "user_authorization"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_rejected"
)
EXECUTION_AUDIT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_execution_passed"
)
EXECUTION_CAMP_HEAD_AUDIT_KEY = (
    "v14_public_simulator_default_off_selector_runtime_shadow_replay_"
    "execution_camp_head"
)
EXECUTION_CAMP_ORIGIN_AUDIT_KEY = (
    "v14_public_simulator_default_off_selector_runtime_shadow_replay_"
    "execution_camp_origin_main"
)
DEFAULT_EXPECTED_LOG_COUNT = 32
DEFAULT_EXPECTED_RECORDS = 3200
DEFAULT_EXPECTED_STEPS_PER_LOG = 100


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--execution_output_dir", type=Path, required=True)
    parser.add_argument("--execution_audit_json", type=Path, required=True)
    parser.add_argument("--execution_audit_md", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--expected_log_count", type=int, default=DEFAULT_EXPECTED_LOG_COUNT)
    parser.add_argument("--expected_records", type=int, default=DEFAULT_EXPECTED_RECORDS)
    parser.add_argument(
        "--expected_steps_per_log",
        type=int,
        default=DEFAULT_EXPECTED_STEPS_PER_LOG,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        execution_artifact_dir=args.execution_artifact_dir,
        execution_output_dir=args.execution_output_dir,
        execution_audit_json=args.execution_audit_json,
        execution_audit_md=args.execution_audit_md,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        expected_log_count=args.expected_log_count,
        expected_records=args.expected_records,
        expected_steps_per_log=args.expected_steps_per_log,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    execution_artifact_dir: Path,
    execution_output_dir: Path,
    execution_audit_json: Path,
    execution_audit_md: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    expected_log_count: int = DEFAULT_EXPECTED_LOG_COUNT,
    expected_records: int = DEFAULT_EXPECTED_RECORDS,
    expected_steps_per_log: int = DEFAULT_EXPECTED_STEPS_PER_LOG,
) -> dict[str, Any]:
    execution_artifact_dir = execution_artifact_dir.resolve()
    execution_output_dir = execution_output_dir.resolve()
    execution_audit_json = execution_audit_json.resolve()
    execution_audit_md = execution_audit_md.resolve()
    output_dir = output_dir.resolve()
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    heads = _parse_key_values(_read_text(execution_artifact_dir / "HEADS"))
    audit_exit = _read_text(execution_artifact_dir / "audit.exit").strip()
    source_report = _read_json(execution_audit_json)
    source_decision = _dict(source_report.get("final_decision"))
    source_execution = _dict(source_report.get("execution"))
    source_records = _dict(source_report.get("records"))
    source_heads = _dict(source_report.get("heads"))
    source_hashes = _dict(source_report.get("source_hashes"))
    source_violations = _dict(source_records.get("violation_counts"))
    source_failed_checks = source_decision.get("failed_checks")
    checks = _checks(
        execution_artifact_dir=execution_artifact_dir,
        execution_output_dir=execution_output_dir,
        execution_audit_json=execution_audit_json,
        execution_audit_md=execution_audit_md,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        audit_exit=audit_exit,
        source_decision=source_decision,
        source_execution=source_execution,
        source_records=source_records,
        source_heads=source_heads,
        source_hashes=source_hashes,
        source_violations=source_violations,
        source_failed_checks=source_failed_checks,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        expected_log_count=expected_log_count,
        expected_records=expected_records,
        expected_steps_per_log=expected_steps_per_log,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "result_review_only": True,
            "replay_executed_by_source": True,
            "replay_executed_by_review": False,
            "candidate_generation_executed_by_review": False,
            "training_executed_by_review": False,
            "dp_modified_by_review": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "inputs": {
            "execution_artifact_dir": str(execution_artifact_dir),
            "execution_output_dir": str(execution_output_dir),
            "execution_audit_json": str(execution_audit_json),
            "execution_audit_md": str(execution_audit_md),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "artifact_camp_head": heads.get("CAMP_HEAD"),
            "artifact_camp_origin_main": heads.get("CAMP_ORIGIN_MAIN"),
            "artifact_dp_head": heads.get("DP_HEAD"),
            "source_audit_execution_camp_head": source_heads.get("execution_camp_head"),
            "source_audit_current_dp_head": source_heads.get("current_dp_head"),
        },
        "source_hashes": {
            "execution_audit_json": _sha256(execution_audit_json)
            if execution_audit_json.is_file()
            else None,
            "execution_audit_md": _sha256(execution_audit_md)
            if execution_audit_md.is_file()
            else None,
            "execution_artifact_sha256s": _sha256(execution_artifact_dir / "SHA256SUMS")
            if (execution_artifact_dir / "SHA256SUMS").is_file()
            else None,
        },
        "execution": {
            "audit_exit": audit_exit,
            "selection_log_count": source_execution.get("selection_log_count"),
            "validation_summary_count": source_execution.get("validation_summary_count"),
            "replay_summary_count": source_execution.get("replay_summary_count"),
            "formal_seed_path_count": source_execution.get("formal_seed_path_count"),
            "stderr_lines": source_execution.get("stderr_lines"),
            "runbook_exit": source_execution.get("runbook_exit"),
        },
        "records": {
            "record_count": source_records.get("record_count"),
            "log_record_counts_min": source_records.get("log_record_counts_min"),
            "log_record_counts_max": source_records.get("log_record_counts_max"),
            "default_off_selector_records": source_records.get(
                "default_off_selector_records"
            ),
            "artifact_contract_ready_records": source_records.get(
                "artifact_contract_ready_records"
            ),
            "executed_top1_records": source_records.get("executed_top1_records"),
            "selected_index_matches_executed_index_records": source_records.get(
                "selected_index_matches_executed_index_records"
            ),
            "shadow_selected_index_nonzero_records": source_records.get(
                "shadow_selected_index_nonzero_records"
            ),
            "shadow_selected_index_differs_from_executed_index_records": (
                source_records.get(
                    "shadow_selected_index_differs_from_executed_index_records"
                )
            ),
            "feasible_records": source_records.get("feasible_records"),
            "used_fallback_records": source_records.get("used_fallback_records"),
            "masked_selection_score_inf_count": source_records.get(
                "masked_selection_score_inf_count"
            ),
            "max_affine_score_error": source_records.get("max_affine_score_error"),
            "violation_counts": source_violations,
        },
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result_review_report.json", report)
    (output_dir / "result_review_report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    execution = report["execution"]
    records = report["records"]
    lines = [
        "# V14 Runtime Shadow Replay Result Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Source runbook exit: `{execution.get('runbook_exit')}`",
        f"- Source audit exit: `{execution.get('audit_exit')}`",
        f"- Selection logs: `{execution.get('selection_log_count')}`",
        f"- Validation summaries: `{execution.get('validation_summary_count')}`",
        f"- Replay summaries: `{execution.get('replay_summary_count')}`",
        f"- Records: `{records.get('record_count')}`",
        f"- Executed DP Top-1 records: `{records.get('executed_top1_records')}`",
        f"- Default-off selector records: `{records.get('default_off_selector_records')}`",
        f"- Shadow non-Top-1 records: `{records.get('shadow_selected_index_nonzero_records')}`",
        f"- Fail-closed fallback records: `{records.get('used_fallback_records')}`",
        f"- Max affine score error: `{records.get('max_affine_score_error')}`",
        "",
        "This is a read-only result review. It does not run replay, generate "
        "candidates, train CAMP, modify DP, promote, deploy, or make "
        "safety/CAMP-over-DP claims.",
        "",
        "CAMP remains a default-off shadow reranker over fixed DP candidate "
        "tensors; the executed trajectory policy remains DP Top-1.",
        "",
    ]
    return "\n".join(lines)


def _checks(
    *,
    execution_artifact_dir: Path,
    execution_output_dir: Path,
    execution_audit_json: Path,
    execution_audit_md: Path,
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    audit_exit: str,
    source_decision: dict[str, Any],
    source_execution: dict[str, Any],
    source_records: dict[str, Any],
    source_heads: dict[str, Any],
    source_hashes: dict[str, Any],
    source_violations: dict[str, Any],
    source_failed_checks: Any,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    expected_log_count: int,
    expected_records: int,
    expected_steps_per_log: int,
) -> list[dict[str, Any]]:
    execution_camp_head = _latest_value(v14_text, EXECUTION_CAMP_HEAD_AUDIT_KEY)
    execution_camp_origin = _latest_value(v14_text, EXECUTION_CAMP_ORIGIN_AUDIT_KEY)
    return [
        _check(
            "execution_artifact_dir_exists",
            execution_artifact_dir.is_dir(),
            str(execution_artifact_dir),
            "directory",
        ),
        _check(
            "execution_output_dir_exists",
            execution_output_dir.is_dir(),
            str(execution_output_dir),
            "directory",
        ),
        _check(
            "execution_audit_json_exists",
            execution_audit_json.is_file(),
            str(execution_audit_json),
            "file",
        ),
        _check(
            "execution_audit_md_exists",
            execution_audit_md.is_file(),
            str(execution_audit_md),
            "file",
        ),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("artifact_dp_head_fixed", heads.get("DP_HEAD"), required_dp_head),
        _expect(
            "source_audit_dp_head_fixed",
            source_heads.get("current_dp_head"),
            required_dp_head,
        ),
        _expect(
            "current_camp_head_matches_origin",
            current_camp_head,
            current_camp_origin_main,
        ),
        _expect(
            "artifact_camp_head_matches_execution_audit",
            heads.get("CAMP_HEAD"),
            execution_camp_head,
        ),
        _expect(
            "artifact_camp_origin_matches_execution_audit",
            heads.get("CAMP_ORIGIN_MAIN"),
            execution_camp_origin,
        ),
        _expect(
            "audit_latest_status",
            _latest_value(v14_text, "current_v14_status"),
            EXPECTED_CURRENT_STATUS,
        ),
        _expect(
            "audit_latest_next_work",
            _latest_value(v14_text, "next_work_target"),
            authorized_current_work,
        ),
        _check(
            "status_doc_mentions_current_status",
            EXPECTED_CURRENT_STATUS in status_text,
            EXPECTED_CURRENT_STATUS in status_text,
            True,
        ),
        _check(
            "status_doc_mentions_current_work",
            authorized_current_work in status_text,
            authorized_current_work in status_text,
            True,
        ),
        _expect("source_audit_exit_zero", audit_exit, "0"),
        _expect("source_audit_decision_passed", source_decision.get("passed"), True),
        _expect("source_audit_status", source_decision.get("status"), EXECUTION_AUDIT_STATUS),
        _expect("source_audit_failed_checks_empty", source_failed_checks, []),
        _expect(
            "source_audit_authorized_current_work",
            source_decision.get("authorized_next_work"),
            authorized_current_work,
        ),
        _expect(
            "source_audit_replay_by_audit_false",
            source_decision.get("replay_execution_performed_by_this_audit"),
            False,
        ),
        _expect(
            "source_audit_candidate_generation_by_camp_blocked",
            source_decision.get("candidate_generation_by_camp_authorized"),
            False,
        ),
        _expect(
            "source_audit_dp_modification_blocked",
            source_decision.get("dp_modification_authorized"),
            False,
        ),
        _expect(
            "source_audit_selector_promotion_blocked",
            source_decision.get("selector_promotion_authorized"),
            False,
        ),
        _expect(
            "source_audit_safety_claim_blocked",
            source_decision.get("safety_benefit_claim_authorized"),
            False,
        ),
        _expect(
            "source_audit_camp_over_dp_claim_blocked",
            source_decision.get("camp_over_dp_top1_claim_authorized"),
            False,
        ),
        _expect("source_runbook_exit_zero", source_execution.get("runbook_exit"), "0"),
        _expect(
            "selection_log_count",
            source_execution.get("selection_log_count"),
            expected_log_count,
        ),
        _expect(
            "validation_summary_count",
            source_execution.get("validation_summary_count"),
            expected_log_count,
        ),
        _expect(
            "replay_summary_count",
            source_execution.get("replay_summary_count"),
            expected_log_count,
        ),
        _expect("record_count", source_records.get("record_count"), expected_records),
        _expect(
            "log_record_counts_min",
            source_records.get("log_record_counts_min"),
            expected_steps_per_log,
        ),
        _expect(
            "log_record_counts_max",
            source_records.get("log_record_counts_max"),
            expected_steps_per_log,
        ),
        _expect(
            "default_off_selector_all_records",
            source_records.get("default_off_selector_records"),
            expected_records,
        ),
        _expect(
            "artifact_contract_ready_all_records",
            source_records.get("artifact_contract_ready_records"),
            expected_records,
        ),
        _expect(
            "executed_top1_all_records",
            source_records.get("executed_top1_records"),
            expected_records,
        ),
        _expect(
            "selected_index_matches_executed_index_all_records",
            source_records.get("selected_index_matches_executed_index_records"),
            expected_records,
        ),
        _expect(
            "formal_seed_path_count_zero",
            source_execution.get("formal_seed_path_count"),
            0,
        ),
        _check(
            "max_affine_score_error_small",
            _as_float(source_records.get("max_affine_score_error")) <= 1.0e-6,
            source_records.get("max_affine_score_error"),
            "<=1e-6",
        ),
        _expect("affine_score_violations_zero", source_violations.get("affine_score"), 0),
        _expect("atom_schema_violations_zero", source_violations.get("atom_schema"), 0),
        _expect(
            "closed_loop_outcomes_violations_zero",
            source_violations.get("closed_loop_outcomes"),
            0,
        ),
        _expect(
            "default_off_contract_violations_zero",
            source_violations.get("default_off_contract"),
            0,
        ),
        _expect("executed_top1_violations_zero", source_violations.get("executed_top1"), 0),
        _expect("guidance_violations_zero", source_violations.get("guidance"), 0),
        _expect("postselection_violations_zero", source_violations.get("postselection"), 0),
        _expect("reference_blend_violations_zero", source_violations.get("reference_blend"), 0),
        _expect(
            "selected_executed_mismatch_violations_zero",
            source_violations.get("selected_executed_mismatch"),
            0,
        ),
        _expect(
            "selection_score_mask_violations_zero",
            source_violations.get("selection_score_mask"),
            0,
        ),
        _expect("shape_violations_zero", source_violations.get("shape"), 0),
        _check(
            "source_hashes_present",
            bool(source_hashes),
            sorted(source_hashes),
            "non-empty",
        ),
        _check(
            "source_stdout_hash_recorded",
            bool(source_hashes.get("execution_stdout")),
            source_hashes.get("execution_stdout"),
            "sha256",
        ),
        _check(
            "source_stderr_hash_recorded",
            bool(source_hashes.get("execution_stderr")),
            source_hashes.get("execution_stderr"),
            "sha256",
        ),
    ]


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": sorted(failed),
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "result_review_complete": bool(passed),
        "promotion_decision_plan_authorized_next": bool(passed),
        "replay_executed_by_review": False,
        "candidate_generation_executed_by_review": False,
        "training_executed_by_review": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
    }


def _failure_class(failed: list[str]) -> str:
    if any("audit_latest" in check or "status_doc" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    if any("count" in check or "records" in check or "summary" in check for check in failed):
        return "execution_result_shape_or_count_contract_failure"
    default_off_markers = (
        "top1",
        "selection",
        "online",
        "postselection",
        "closed_loop",
        "blend",
        "guidance",
        "affine",
        "default_off",
    )
    if any(any(marker in check for marker in default_off_markers) for check in failed):
        return "default_off_shadow_contract_failure"
    return "result_review_contract_failure"


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    values = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    return values[-1] if values else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    lines = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": observed,
        "expected": expected,
    }


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
