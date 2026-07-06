#!/usr/bin/env python3
"""Plan a continuation for the objective-level 3200-row outcome gap.

This gate is plan/preflight only. It records that the existing audited
SafetyCost evidence is run-level (32 pairs), while the active objective asks
for 3200 strictly paired shadow-selected closed-loop outcome rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_outcome_continuation_plan_v1"
)
SOURCE_CLOSEOUT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_no_promotion_no_claim_closeout_recorded"
)
AUTHORIZED_CURRENT_WORK = (
    "no_further_action_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "actual_safetycost_evidence_does_not_support_promotion_or_claim"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight_static_review_only"
)

PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation_plan.md"
)

BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "training_authorized",
    "training_execution_authorized",
    "candidate_generation_authorized",
    "replay_execution_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
)
FALSE_EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "replay_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
    "actual_safetycost_outcome_materialization_executed_by_this_gate",
)
OBJECTIVE_REQUIRED_RECORDS = 3200
EXISTING_RUN_LEVEL_PAIR_TARGET = 32


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_closeout_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_closeout_json", type=Path, required=True)
    parser.add_argument("--source_closeout_md", type=Path, required=True)
    parser.add_argument("--source_closeout_sha256s", type=Path, required=True)
    parser.add_argument("--source_materialization_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_materialization_json", type=Path, required=True)
    parser.add_argument("--source_materialization_sha256s", type=Path, required=True)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_closeout_artifact_dir=args.source_closeout_artifact_dir,
        source_closeout_json=args.source_closeout_json,
        source_closeout_md=args.source_closeout_md,
        source_closeout_sha256s=args.source_closeout_sha256s,
        source_materialization_artifact_dir=args.source_materialization_artifact_dir,
        source_materialization_json=args.source_materialization_json,
        source_materialization_sha256s=args.source_materialization_sha256s,
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_sha256s=args.source_result_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation_plan,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_closeout_artifact_dir: Path,
    source_closeout_json: Path,
    source_closeout_md: Path,
    source_closeout_sha256s: Path,
    source_materialization_artifact_dir: Path,
    source_materialization_json: Path,
    source_materialization_sha256s: Path,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
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
    paths = {
        "source_closeout_artifact_dir": source_closeout_artifact_dir.resolve(),
        "source_closeout_json": source_closeout_json.resolve(),
        "source_closeout_md": source_closeout_md.resolve(),
        "source_closeout_sha256s": source_closeout_sha256s.resolve(),
        "source_materialization_artifact_dir": source_materialization_artifact_dir.resolve(),
        "source_materialization_json": source_materialization_json.resolve(),
        "source_materialization_sha256s": source_materialization_sha256s.resolve(),
        "source_result_review_artifact_dir": source_result_review_artifact_dir.resolve(),
        "source_result_review_json": source_result_review_json.resolve(),
        "source_result_review_sha256s": source_result_review_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
        "output_dir": output_dir.resolve(),
    }
    closeout = _read_json_dict(paths["source_closeout_json"])
    materialization = _read_json_dict(paths["source_materialization_json"])
    result_review = _read_json_dict(paths["source_result_review_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    closeout_heads = _parse_key_values(_read_text(paths["source_closeout_artifact_dir"] / "HEADS"))
    materialization_heads = _parse_key_values(_read_text(paths["source_materialization_artifact_dir"] / "HEADS"))
    result_heads = _parse_key_values(_read_text(paths["source_result_review_artifact_dir"] / "HEADS"))

    gap_summary = _gap_summary(materialization, result_review)
    checks = _checks(
        enabled=enabled,
        paths=paths,
        closeout=closeout,
        materialization=materialization,
        result_review=result_review,
        v14_text=v14_text,
        status_text=status_text,
        closeout_heads=closeout_heads,
        materialization_heads=materialization_heads,
        result_heads=result_heads,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        gap_summary=gap_summary,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "preflight_only": True,
            "read_only": True,
            "objective_3200_outcome_gap_reopened_for_planning_only": bool(passed),
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
        "inputs": {name: str(path) for name, path in paths.items()},
        "source_hashes": _source_hashes(paths),
        "source_closeout_summary": _source_closeout_summary(closeout),
        "source_result_review_summary": _source_result_review_summary(result_review),
        "source_materialization_summary": _source_materialization_summary(materialization),
        "objective_gap_summary": gap_summary,
        "preflight_plan": _preflight_plan(),
        "no_go_register": _no_go_register(),
        "artifact_contract": _artifact_contract(),
        "plan_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, gap_summary=gap_summary),
    }


def _checks(
    *,
    enabled: bool,
    paths: dict[str, Path],
    closeout: dict[str, Any],
    materialization: dict[str, Any],
    result_review: dict[str, Any],
    v14_text: str,
    status_text: str,
    closeout_heads: dict[str, str],
    materialization_heads: dict[str, str],
    result_heads: dict[str, str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    gap_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def expect(name: str, actual: Any, expected: Any) -> None:
        checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})

    def require(name: str, passed: bool, actual: Any = None, expected: Any = True) -> None:
        checks.append({"name": name, "passed": bool(passed), "actual": actual if actual is not None else bool(passed), "expected": expected})

    latest_audit_status = _latest_value(v14_text, "current_v14_status")
    latest_audit_next = _latest_value(v14_text, "next_work_target")
    latest_status_doc_status = _latest_value(status_text, "current_v14_status")
    latest_status_doc_next = _latest_value(status_text, "next_work_target")
    closeout_decision = _dict(closeout.get("final_decision"))
    mat_decision = _dict(materialization.get("final_decision"))
    review_decision = _dict(result_review.get("final_decision"))

    require("continuation_plan_enabled", enabled)
    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("audit_latest_status", latest_audit_status, SOURCE_CLOSEOUT_STATUS)
    expect("audit_latest_next_work", latest_audit_next, AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", latest_status_doc_status, SOURCE_CLOSEOUT_STATUS)
    expect("status_doc_latest_next_work", latest_status_doc_next, AUTHORIZED_CURRENT_WORK)

    for name, path in paths.items():
        if name.endswith("_artifact_dir") or name == "output_dir":
            continue
        require(f"{name}_exists", path.is_file(), str(path), "file")
    for name in ("source_closeout_artifact_dir", "source_materialization_artifact_dir", "source_result_review_artifact_dir"):
        require(f"{name}_exists", paths[name].is_dir(), str(paths[name]), "directory")

    expect("closeout_dp_head_fixed", _kv(closeout_heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect("materialization_dp_head_fixed", _kv(materialization_heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect("result_review_dp_head_fixed", _kv(result_heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect("closeout_passed", closeout_decision.get("passed"), True)
    expect("closeout_no_further_action", closeout_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("closeout_no_promotion", closeout_decision.get("selector_promotion_authorized"), False)
    expect("closeout_no_deployment", closeout_decision.get("deployment_authorized"), False)
    expect("closeout_no_safety_claim", closeout_decision.get("safety_benefit_claim_authorized"), False)
    expect("closeout_no_camp_over_dp_claim", closeout_decision.get("camp_over_dp_top1_claim_authorized"), False)
    expect("materialization_passed", mat_decision.get("passed"), True)
    expect("result_review_passed", review_decision.get("passed"), True)
    expect("result_review_safety_claim_supported", review_decision.get("safety_benefit_claim_supported"), False)
    expect("result_review_camp_over_dp_supported", review_decision.get("camp_over_dp_top1_claim_supported"), False)

    expect("objective_required_records", gap_summary["objective_required_records"], OBJECTIVE_REQUIRED_RECORDS)
    expect("runtime_record_count", gap_summary["runtime_record_count"], OBJECTIVE_REQUIRED_RECORDS)
    expect("existing_top1_summary_count", gap_summary["existing_top1_summary_count"], EXISTING_RUN_LEVEL_PAIR_TARGET)
    expect("existing_shadow_summary_count", gap_summary["existing_shadow_summary_count"], EXISTING_RUN_LEVEL_PAIR_TARGET)
    expect("existing_delta_count", gap_summary["existing_delta_count"], EXISTING_RUN_LEVEL_PAIR_TARGET)
    expect("candidate_closed_loop_outcome_records", gap_summary["candidate_closed_loop_outcome_records"], 0)
    expect("missing_candidate_closed_loop_outcome_records", gap_summary["missing_candidate_closed_loop_outcome_records"], OBJECTIVE_REQUIRED_RECORDS)
    expect("objective_3200_gap_present", gap_summary["objective_3200_gap_present"], True)
    expect("closeout_does_not_satisfy_objective", gap_summary["closeout_does_not_satisfy_objective"], True)
    return checks


def _decision(*, passed: bool, checks: list[dict[str, Any]], gap_summary: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "continuation_plan_enabled" in failed:
        failure_class = "explicit_objective_3200_outcome_continuation_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith(("closeout_", "materialization_", "result_review_")) for name in failed):
        failure_class = "source_artifact_contract_failure"
    else:
        failure_class = "objective_3200_gap_plan_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_outcome_continuation_plan_ready": bool(passed),
        "objective_3200_outcome_source_inventory_static_review_authorized": bool(passed),
        "objective_3200_gap_present": gap_summary["objective_3200_gap_present"],
        "objective_required_records": gap_summary["objective_required_records"],
        "existing_run_level_pair_count": gap_summary["existing_delta_count"],
        "per_record_shadow_outcome_records": gap_summary["candidate_closed_loop_outcome_records"],
        "missing_per_record_shadow_outcome_records": gap_summary["missing_candidate_closed_loop_outcome_records"],
        "direct_promotion_recommendation": False,
        "recommendation": "static_review_objective_3200_outcome_source_inventory_preflight_only" if passed else "repair_or_rerun_same_plan_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _gap_summary(materialization: dict[str, Any], result_review: dict[str, Any]) -> dict[str, Any]:
    mat_summary = _dict(materialization.get("materialization_summary"))
    runtime = _dict(materialization.get("runtime_source_summary"))
    review_source = _dict(result_review.get("source_execution_summary"))
    candidate_records = int(runtime.get("candidate_closed_loop_outcome_records") or 0)
    missing_records = int(runtime.get("missing_candidate_closed_loop_outcome_records") or 0)
    delta_count = int(mat_summary.get("delta_count") or review_source.get("delta_count") or 0)
    return {
        "objective_required_records": OBJECTIVE_REQUIRED_RECORDS,
        "runtime_record_count": int(runtime.get("record_count") or 0),
        "runtime_selection_log_count": int(runtime.get("selection_log_count") or 0),
        "existing_top1_summary_count": int(mat_summary.get("top1_summary_count") or 0),
        "existing_shadow_summary_count": int(mat_summary.get("shadow_summary_count") or 0),
        "existing_paired_run_key_count": int(mat_summary.get("paired_run_key_count") or 0),
        "existing_delta_count": delta_count,
        "candidate_closed_loop_outcome_records": candidate_records,
        "missing_candidate_closed_loop_outcome_records": missing_records,
        "objective_3200_gap_present": candidate_records < OBJECTIVE_REQUIRED_RECORDS,
        "closeout_does_not_satisfy_objective": delta_count < OBJECTIVE_REQUIRED_RECORDS,
        "delta_mean": _dict(mat_summary.get("delta_summary")).get("mean"),
        "delta_ci95_low": _dict(mat_summary.get("delta_bootstrap_ci95")).get("ci95_low"),
        "delta_ci95_high": _dict(mat_summary.get("delta_bootstrap_ci95")).get("ci95_high"),
    }


def _preflight_plan() -> list[dict[str, Any]]:
    return [
        {
            "step": "inventory_existing_shadow_selected_outputs",
            "purpose": "Find whether the 32 run-level shadow-selected summaries include recoverable per-record closed-loop outcomes.",
            "execution": "read_only",
        },
        {
            "step": "inventory_runtime_selection_logs",
            "purpose": "Map all 3200 fixed-DP candidate tensor rows to scenario/seed/sample/tl/run keys and shadow_selected_index.",
            "execution": "read_only",
        },
        {
            "step": "validate_fixed_candidate_identity_per_record",
            "purpose": "Require candidate tensor identity and mutation count checks before any 3200-row materialization.",
            "execution": "read_only",
        },
        {
            "step": "define_per_record_outcome_source_contract",
            "purpose": "Accept only existing or newly replayed fixed-DP candidate executions; reject generated, repaired, blended, or postprocessed trajectories.",
            "execution": "plan_only",
        },
        {
            "step": "fail_closed_if_only_run_level_summaries_exist",
            "purpose": "Do not relabel 32 run-level summaries as 3200 per-record outcomes.",
            "execution": "plan_only",
        },
        {
            "step": "authorize_next_static_review_only",
            "purpose": "Review this inventory/preflight contract before any replay or materialization.",
            "execution": "static_review_only",
        },
    ]


def _no_go_register() -> list[str]:
    return [
        "dp_head_drift",
        "camp_generates_repairs_rewrites_or_blends_trajectory",
        "candidate_tensor_not_fixed_dp_source",
        "per_record_outcome_source_missing",
        "closed_loop_outcome_used_for_training_or_online_input",
        "full36_or_formal_seed_11_12_13_present",
        "non_affine_score_or_nonconvex_master",
        "promotion_deployment_online_selector_or_claim",
    ]


def _artifact_contract() -> dict[str, Any]:
    return {
        "required_files": ["HEADS", "COMMAND", "stdout", "stderr", "run.exit", PLAN_JSON_NAME, PLAN_MD_NAME, "SHA256SUMS"],
        "nested_sha256s_required": True,
        "root_sha256s_required": True,
        "source_artifacts_required": [
            "actual_safetycost_materialization_execution",
            "actual_safetycost_result_review",
            "actual_safetycost_no_promotion_no_claim_closeout",
        ],
    }


def _source_closeout_summary(closeout: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(closeout.get("final_decision"))
    closeout_summary = _dict(closeout.get("closeout_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "no_further_action_recommended": decision.get("no_further_action_recommended"),
        "delta_mean": closeout_summary.get("delta_mean"),
        "better_records": closeout_summary.get("better_records"),
        "worse_records": closeout_summary.get("worse_records"),
    }


def _source_result_review_summary(result_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(result_review.get("final_decision"))
    source = _dict(result_review.get("source_execution_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "safety_benefit_claim_supported": decision.get("safety_benefit_claim_supported"),
        "camp_over_dp_top1_claim_supported": decision.get("camp_over_dp_top1_claim_supported"),
        "delta_count": source.get("delta_count"),
        "delta_mean": source.get("delta_mean"),
    }


def _source_materialization_summary(materialization: dict[str, Any]) -> dict[str, Any]:
    mat_summary = _dict(materialization.get("materialization_summary"))
    runtime = _dict(materialization.get("runtime_source_summary"))
    return {
        "runtime_record_count": runtime.get("record_count"),
        "candidate_closed_loop_outcome_records": runtime.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": runtime.get("missing_candidate_closed_loop_outcome_records"),
        "top1_summary_count": mat_summary.get("top1_summary_count"),
        "shadow_summary_count": mat_summary.get("shadow_summary_count"),
        "delta_count": mat_summary.get("delta_count"),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{_sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    gap = report["objective_gap_summary"]
    lines = [
        "# v14 Objective 3200 Outcome Continuation Plan",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Gap",
        "",
        f"- Objective required records: `{gap['objective_required_records']}`",
        f"- Existing run-level paired deltas: `{gap['existing_delta_count']}`",
        f"- Per-record shadow outcome records: `{gap['candidate_closed_loop_outcome_records']}`",
        f"- Missing per-record shadow outcomes: `{gap['missing_candidate_closed_loop_outcome_records']}`",
        f"- Closeout satisfies objective: `{not gap['closeout_does_not_satisfy_objective']}`",
        "",
        "## Boundary",
        "",
        "- Plan/preflight only: no replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


def _source_hashes(paths: dict[str, Path]) -> dict[str, str | None]:
    return {name: _sha256(path) if path.is_file() else None for name, path in paths.items() if name != "output_dir"}


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def _kv(values: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in values:
            return values[key]
    return None


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
