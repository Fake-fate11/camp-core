#!/usr/bin/env python3
"""Read-only source inventory preflight for objective-3200 outcome evidence."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_outcome_source_inventory_"
        "preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_source_inventory_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


REVIEW_MODULE = _load_static_review_module()
PLAN_MODULE = REVIEW_MODULE.PLAN_MODULE

FIXED_DP_HEAD = REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = REVIEW_MODULE.READY_STATUS
BLOCKED_ACTIONS = REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = REVIEW_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_outcome_source_inventory_preflight_v1"
)
AUTHORIZED_CURRENT_WORK = REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan_only"
)

PREFLIGHT_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight.json"
)
PREFLIGHT_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_continuation_plan_json", type=Path, required=True)
    parser.add_argument("--source_materialization_json", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_closeout_json", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_continuation_plan_json=args.source_continuation_plan_json,
        source_materialization_json=args.source_materialization_json,
        source_result_review_json=args.source_result_review_json,
        source_closeout_json=args.source_closeout_json,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_sha256s: Path,
    source_continuation_plan_json: Path,
    source_materialization_json: Path,
    source_result_review_json: Path,
    source_closeout_json: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    paths = {
        "source_static_review_artifact_dir": source_static_review_artifact_dir.resolve(),
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
        "source_continuation_plan_json": source_continuation_plan_json.resolve(),
        "source_materialization_json": source_materialization_json.resolve(),
        "source_result_review_json": source_result_review_json.resolve(),
        "source_closeout_json": source_closeout_json.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
        "output_dir": output_dir.resolve(),
    }
    static_review = PLAN_MODULE._read_json_dict(paths["source_static_review_json"])
    continuation_plan = PLAN_MODULE._read_json_dict(paths["source_continuation_plan_json"])
    materialization = PLAN_MODULE._read_json_dict(paths["source_materialization_json"])
    result_review = PLAN_MODULE._read_json_dict(paths["source_result_review_json"])
    closeout = PLAN_MODULE._read_json_dict(paths["source_closeout_json"])
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])
    heads = PLAN_MODULE._parse_key_values(
        PLAN_MODULE._read_text(paths["source_static_review_artifact_dir"] / "HEADS")
    )

    inventory = _inventory_summary(
        continuation_plan=continuation_plan,
        materialization=materialization,
        result_review=result_review,
        closeout=closeout,
    )
    checks = _checks(
        enabled=enabled,
        paths=paths,
        static_review=static_review,
        continuation_plan=continuation_plan,
        result_review=result_review,
        closeout=closeout,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        inventory=inventory,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "source_inventory_preflight_only": True,
            "source_inventory_preflight_executed": True,
            "outcome_materialization_executed": False,
            "replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {name: str(path) for name, path in paths.items()},
        "source_hashes": {
            name: PLAN_MODULE._sha256(path)
            for name, path in paths.items()
            if name != "output_dir" and path.is_file()
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_static_review_camp_head": heads.get("CAMP_HEAD"),
            "source_static_review_camp_origin_main": heads.get("CAMP_ORIGIN_MAIN"),
            "source_static_review_dp_head": PLAN_MODULE._kv(heads, "DP_HEAD", "dp_head"),
        },
        "inventory_summary": inventory,
        "source_static_review_summary": _source_static_review_summary(static_review),
        "preflight_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, inventory=inventory),
    }


def _checks(
    *,
    enabled: bool,
    paths: dict[str, Path],
    static_review: dict[str, Any],
    continuation_plan: dict[str, Any],
    result_review: dict[str, Any],
    closeout: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        _expect("source_inventory_preflight_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("audit_latest_status", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        _expect("audit_latest_next_work", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_dp_head_fixed", PLAN_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
    ]
    for name, path in paths.items():
        if name == "output_dir":
            continue
        expected = "directory" if name.endswith("_artifact_dir") else "file"
        actual = path.is_dir() if expected == "directory" else path.is_file()
        checks.append(_check(f"{name}_exists", actual, str(path), expected))

    static_decision = _dict(static_review.get("final_decision"))
    plan_decision = _dict(continuation_plan.get("final_decision"))
    result_decision = _dict(result_review.get("final_decision"))
    closeout_decision = _dict(closeout.get("final_decision"))
    checks.extend(
        [
            _expect("source_static_review_schema", static_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
            _expect("source_static_review_passed", static_decision.get("passed"), True),
            _expect("source_static_review_status", static_decision.get("status"), SOURCE_REVIEW_STATUS),
            _expect("source_static_review_authorized_next", static_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            _expect("source_plan_passed", plan_decision.get("passed"), True),
            _expect("source_plan_gap_present", plan_decision.get("objective_3200_gap_present"), True),
            _expect("source_result_review_passed", result_decision.get("passed"), True),
            _expect("source_result_review_safety_claim_supported", result_decision.get("safety_benefit_claim_supported"), False),
            _expect("source_result_review_camp_over_dp_supported", result_decision.get("camp_over_dp_top1_claim_supported"), False),
            _expect("source_closeout_passed", closeout_decision.get("passed"), True),
            _expect("source_closeout_no_further_action", closeout_decision.get("authorized_next_work"), PLAN_MODULE.AUTHORIZED_CURRENT_WORK),
        ]
    )
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_{action}", static_decision.get(action), False))
    checks.extend(
        [
            _expect("inventory_objective_required_records", inventory["objective_required_records"], PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS),
            _expect("inventory_runtime_record_count", inventory["runtime_record_count"], PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS),
            _expect("inventory_existing_delta_count", inventory["existing_delta_count"], PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET),
            _expect("inventory_candidate_closed_loop_outcome_records", inventory["candidate_closed_loop_outcome_records"], 0),
            _expect("inventory_missing_candidate_closed_loop_outcome_records", inventory["missing_candidate_closed_loop_outcome_records"], PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS),
            _expect("inventory_existing_artifacts_satisfy_objective", inventory["existing_artifacts_satisfy_objective"], False),
            _expect("inventory_per_record_outcome_source_available", inventory["per_record_outcome_source_available"], False),
            _expect("inventory_requires_acquisition_plan", inventory["requires_acquisition_plan"], True),
        ]
    )
    return checks


def _inventory_summary(
    *,
    continuation_plan: dict[str, Any],
    materialization: dict[str, Any],
    result_review: dict[str, Any],
    closeout: dict[str, Any],
) -> dict[str, Any]:
    gap = _dict(continuation_plan.get("objective_gap_summary"))
    runtime = _dict(materialization.get("runtime_source_summary"))
    mat = _dict(materialization.get("materialization_summary"))
    result_source = _dict(result_review.get("source_execution_summary"))
    candidate_records = int(gap.get("candidate_closed_loop_outcome_records") or 0)
    missing_records = int(gap.get("missing_candidate_closed_loop_outcome_records") or 0)
    existing_delta_count = int(gap.get("existing_delta_count") or mat.get("delta_count") or result_source.get("delta_count") or 0)
    return {
        "objective_required_records": int(gap.get("objective_required_records") or PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS),
        "runtime_record_count": int(gap.get("runtime_record_count") or runtime.get("record_count") or 0),
        "runtime_selection_log_count": int(gap.get("runtime_selection_log_count") or runtime.get("selection_log_count") or 0),
        "existing_top1_summary_count": int(gap.get("existing_top1_summary_count") or mat.get("top1_summary_count") or 0),
        "existing_shadow_summary_count": int(gap.get("existing_shadow_summary_count") or mat.get("shadow_summary_count") or 0),
        "existing_paired_run_key_count": int(gap.get("existing_paired_run_key_count") or mat.get("paired_run_key_count") or 0),
        "existing_delta_count": existing_delta_count,
        "candidate_closed_loop_outcome_records": candidate_records,
        "missing_candidate_closed_loop_outcome_records": missing_records,
        "per_record_outcome_source_available": candidate_records >= PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS,
        "existing_artifacts_satisfy_objective": existing_delta_count >= PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS,
        "requires_acquisition_plan": missing_records > 0,
        "source_closeout_status": _dict(closeout.get("final_decision")).get("status"),
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "source_inventory_preflight_enabled" in failed:
        failure_class = "explicit_objective_3200_source_inventory_preflight_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith("source_") for name in failed):
        failure_class = "source_artifact_contract_failure"
    else:
        failure_class = "objective_3200_source_inventory_preflight_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_outcome_source_inventory_preflight_passed": bool(passed),
        "objective_3200_outcome_acquisition_plan_authorized": bool(passed),
        "existing_artifacts_satisfy_objective": inventory["existing_artifacts_satisfy_objective"],
        "per_record_outcome_source_available": inventory["per_record_outcome_source_available"],
        "requires_acquisition_plan": inventory["requires_acquisition_plan"],
        "candidate_closed_loop_outcome_records": inventory["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": inventory["missing_candidate_closed_loop_outcome_records"],
        "recommendation": "plan_only_objective_3200_outcome_acquisition" if passed else "repair_or_rerun_same_preflight_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    decision["source_inventory_preflight_executed_by_this_gate"] = bool(passed)
    decision["replay_executed_by_this_gate"] = False
    decision["training_executed_by_this_gate"] = False
    decision["candidate_generation_executed_by_this_gate"] = False
    return decision


def _source_static_review_summary(static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(static_review.get("final_decision"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
    json_path.write_text(json.dumps(PLAN_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{PLAN_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    inventory = report["inventory_summary"]
    return "\n".join(
        [
            "# Objective-3200 Outcome Source Inventory Preflight",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Inventory",
            "",
            f"- Objective required records: `{inventory['objective_required_records']}`",
            f"- Runtime records: `{inventory['runtime_record_count']}`",
            f"- Existing deltas: `{inventory['existing_delta_count']}`",
            f"- Per-record shadow outcomes: `{inventory['candidate_closed_loop_outcome_records']}`",
            f"- Missing per-record shadow outcomes: `{inventory['missing_candidate_closed_loop_outcome_records']}`",
            f"- Existing artifacts satisfy objective: `{inventory['existing_artifacts_satisfy_objective']}`",
            f"- Requires acquisition plan: `{inventory['requires_acquisition_plan']}`",
        ]
    ) + "\n"


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _check(name: str, passed: bool, actual: Any | None = None, expected: Any = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual if actual is not None else bool(passed), "expected": expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
