#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
SUMMARY_SCHEMA_VERSION = "dp_native_fallback_risk_validated_dataset_summary_v1"
REPORT_SCHEMA_VERSION = "dp_native_fallback_risk_validated_dataset_summary_materializer_report_v1"
VALIDATOR_COMPLETE_STATUS = "dp_native_fallback_risk_training_data_validator_complete"
EXPECTED_VALIDATED_FALLBACK_RECORDS = 15
DISABLED_STATUS = "dp_native_fallback_risk_validated_dataset_summary_materializer_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_validated_dataset_summary_materializer_complete"
REJECT_STATUS = "dp_native_fallback_risk_validated_dataset_summary_materializer_rejected"

FORBIDDEN_FLAGS = (
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "camp_training_authorized",
    "camp_retraining_authorized",
    "Full36_authorized",
    "formal_seeds_11_12_13_authorized",
    "dp_modification_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_postselection_authorized",
    "closed_loop_outcome_online_input_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "fallback_risk_training_authorized_now",
    "fallback_dataset_training_sufficiency_claim",
    "feasible_ranking_master_change_authorized",
    "hard_feasibility_relaxation_authorized",
    "all_infeasible_records_added_to_feasible_training",
    "production_selector_change_authorized",
    "online_selector_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only materializer for the validated fallback-risk "
            "dataset summary required by the training sufficiency preflight."
        )
    )
    parser.add_argument("--dataset_json", type=Path, required=True)
    parser.add_argument("--expected_dataset_sha256", required=True)
    parser.add_argument("--validator_output_json", type=Path, required=True)
    parser.add_argument("--expected_validator_output_sha256", required=True)
    parser.add_argument(
        "--enable_default_off_fallback_risk_training_validated_dataset_summary_materializer",
        action="store_true",
        help="Explicit opt-in required before reading any input artifact.",
    )
    parser.add_argument("--output_summary_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_validated_dataset_summary_report(
        dataset_json=args.dataset_json,
        expected_dataset_sha256=args.expected_dataset_sha256,
        validator_output_json=args.validator_output_json,
        expected_validator_output_sha256=args.expected_validator_output_sha256,
        enabled=args.enable_default_off_fallback_risk_training_validated_dataset_summary_materializer,
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if report["final_decision"]["status"] == COMPLETE_STATUS:
        args.output_summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_summary_json.write_text(
            json.dumps(report["validated_dataset_summary"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_validated_dataset_summary_report(
    *,
    dataset_json: Path,
    expected_dataset_sha256: str,
    validator_output_json: Path,
    expected_validator_output_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_training_validated_dataset_summary_materializer_v1",
            "default_off": True,
            "enabled": bool(enabled),
            "read_only": True,
            "existing_artifacts_only": True,
            "preflight_executed": False,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
        },
        "source_paths": {
            "dataset_json": str(dataset_json),
            "validator_output_json": str(validator_output_json),
        },
        "source_hashes": {},
        "validated_dataset_summary": {},
        "final_decision": _decision(
            status=DISABLED_STATUS,
            passed=True,
            enabled=False,
            errors=[],
            summary_output_written=False,
        ),
    }
    if not enabled:
        return report

    errors: list[str] = []
    _validate_sha_literal(expected_dataset_sha256, "expected_dataset_sha256", errors)
    _validate_sha_literal(expected_validator_output_sha256, "expected_validator_output_sha256", errors)

    dataset = _load_json(dataset_json, "dataset_json", errors)
    validator = _load_json(validator_output_json, "validator_output_json", errors)

    dataset_sha = _record_sha(
        dataset_json,
        "dataset_json",
        expected_dataset_sha256,
        "dataset_sha256_mismatch",
        errors,
        report,
    )
    validator_sha = _record_sha(
        validator_output_json,
        "validator_output_json",
        expected_validator_output_sha256,
        "validator_output_sha256_mismatch",
        errors,
        report,
    )

    dataset_record_count = _validate_dataset(dataset, errors)
    validator_record_count = _validate_validator(
        validator,
        dataset_sha=dataset_sha,
        errors=errors,
    )
    records = validator_record_count or dataset_record_count
    if dataset_record_count and validator_record_count and dataset_record_count != validator_record_count:
        errors.append("dataset_validator_record_count_mismatch")

    if not errors:
        report["validated_dataset_summary"] = _summary(
            dataset_sha=dataset_sha,
            validator_sha=validator_sha,
            records=records,
        )
    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
        summary_output_written=not errors,
    )
    return report


def _load_json(path: Path, name: str, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{name}_unreadable:{type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{name}_not_object")
        return {}
    return payload


def _record_sha(
    path: Path,
    name: str,
    expected_sha: str,
    mismatch_error: str,
    errors: list[str],
    report: dict[str, Any],
) -> str:
    if not path.is_file():
        return ""
    actual = _sha256_file(path)
    report["source_hashes"][name] = actual
    if _is_sha256(expected_sha) and actual != expected_sha:
        errors.append(mismatch_error)
    return actual


def _validate_dataset(payload: dict[str, Any], errors: list[str]) -> int:
    if payload.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("dataset_schema_version_mismatch")
    records = payload.get("records")
    if not isinstance(records, list):
        errors.append("dataset_records_not_list")
        record_count = 0
    else:
        record_count = len(records)
        if record_count <= 0:
            errors.append("dataset_record_count_not_positive")
    decision = payload.get("final_decision")
    if isinstance(decision, dict):
        if decision.get("passed") is not True:
            errors.append("dataset_final_decision_not_passed")
        _validate_forbidden_flags(decision, "dataset_final_decision", errors)
        if decision.get("training_authorized", False) is not False:
            errors.append("dataset_final_decision_training_authorized_not_false")
    elif "final_decision" in payload:
        errors.append("dataset_final_decision_not_object")
    for field in ("training_sufficiency_claim", "deployable_checkpoint_claim"):
        if payload.get(field) not in (None, False):
            errors.append(f"{field}_leak")
    return record_count


def _validate_validator(payload: dict[str, Any], *, dataset_sha: str, errors: list[str]) -> int:
    source_hashes = payload.get("source_hashes")
    if not isinstance(source_hashes, dict):
        errors.append("validator_source_hashes_not_object")
    elif dataset_sha and source_hashes.get("dataset_json") != dataset_sha:
        errors.append("validator_dataset_sha256_mismatch")

    record_counts = payload.get("record_counts")
    if not isinstance(record_counts, dict):
        errors.append("validator_record_counts_not_object")
        records_checked = 0
    else:
        records_checked = record_counts.get("records_checked")
        failed_records = record_counts.get("failed_records")
        if not isinstance(records_checked, int) or records_checked <= 0:
            errors.append("validator_records_checked_not_positive")
            records_checked = 0
        if failed_records != 0:
            errors.append("validator_failed_records_nonzero")

    decision = payload.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("validator_final_decision_not_object")
    else:
        if decision.get("status") != VALIDATOR_COMPLETE_STATUS:
            errors.append("validator_status_not_complete")
        if decision.get("passed") is not True:
            errors.append("validator_not_passed")
        if decision.get("errors") not in ([], None):
            errors.append("validator_errors_not_empty")
        if decision.get("training_authorized", False) is not False:
            errors.append("validator_training_authorized_not_false")
        _validate_forbidden_flags(decision, "validator_final_decision", errors)

    for field in ("training_sufficiency_claim", "deployable_checkpoint_claim"):
        if payload.get(field) not in (None, False):
            errors.append(f"validator_{field}_leak")
    return records_checked if isinstance(records_checked, int) else 0


def _validate_forbidden_flags(payload: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for flag in FORBIDDEN_FLAGS:
        if flag in payload and payload.get(flag) is not False:
            errors.append(f"{prefix}_{flag}_not_false")


def _summary(*, dataset_sha: str, validator_sha: str, records: int) -> dict[str, Any]:
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "sha256": dataset_sha,
        "records": int(records),
        "validator_status": VALIDATOR_COMPLETE_STATUS,
        "validator_passed": True,
        "training_sufficiency_claim": False,
        "deployable_checkpoint_claim": False,
        "source_validator_output_sha256": validator_sha,
    }


def _decision(
    *,
    status: str,
    passed: bool,
    enabled: bool,
    errors: list[str],
    summary_output_written: bool,
) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "status": status,
        "passed": bool(passed),
        "enabled": bool(enabled),
        "errors": sorted(set(errors)),
        "summary_output_written": bool(summary_output_written),
        "training_sufficiency_preflight_executed": False,
        "training_sufficiency_preflight_execution_authorized": False,
        "training_authorized": False,
        "fallback_dataset_training_sufficiency_claim": False,
        "camp_retraining_authorized_now": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


def _validate_sha_literal(value: Any, field: str, errors: list[str]) -> None:
    if not _is_sha256(value):
        errors.append(f"{field}_invalid")


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("validated_dataset_summary")
    records = summary.get("records") if isinstance(summary, dict) else None
    lines = [
        "# DP Native Fallback Risk Training Validated Dataset Summary",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"summary_output_written={decision['summary_output_written']}",
        f"records={records}",
        "training_sufficiency_preflight_executed=False",
        "training_sufficiency_preflight_execution_authorized=False",
        "training_authorized=False",
        "camp_retraining_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "```",
        "",
        "This materializer only reads the accepted dataset artifact and its "
        "validator output when explicitly enabled. It does not run the "
        "sufficiency preflight, train CAMP, modify DP, promote a selector or "
        "atom, or claim safety benefit.",
        "",
    ]
    if decision["errors"]:
        lines.extend(["## Errors", "", "```text"])
        lines.extend(str(error) for error in decision["errors"])
        lines.extend(["```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
