#!/usr/bin/env python3
"""Plan objective-3200 shadow-selected outcome acquisition.

This gate is plan-only. It consumes the read-only source inventory preflight
that proved existing artifacts do not contain 3200 per-record shadow-selected
closed-loop outcomes, then defines the audited contract for a future
acquisition path.
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
    "objective_3200_outcome_acquisition_plan_v1"
)
SOURCE_PREFLIGHT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_source_inventory_preflight_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan_static_review_only"
)

PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan.md"
)

OBJECTIVE_REQUIRED_RECORDS = 3200
EXISTING_RUN_LEVEL_PAIR_TARGET = 32
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
    "outcome_acquisition_executed_by_this_gate",
    "actual_safetycost_outcome_materialization_executed_by_this_gate",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_inventory_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_inventory_preflight_json", type=Path, required=True)
    parser.add_argument("--source_inventory_preflight_md", type=Path, required=True)
    parser.add_argument("--source_inventory_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_inventory_preflight_artifact_dir=args.source_inventory_preflight_artifact_dir,
        source_inventory_preflight_json=args.source_inventory_preflight_json,
        source_inventory_preflight_md=args.source_inventory_preflight_md,
        source_inventory_preflight_sha256s=args.source_inventory_preflight_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_plan,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_inventory_preflight_artifact_dir: Path,
    source_inventory_preflight_json: Path,
    source_inventory_preflight_md: Path,
    source_inventory_preflight_sha256s: Path,
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
        "source_inventory_preflight_artifact_dir": source_inventory_preflight_artifact_dir.resolve(),
        "source_inventory_preflight_json": source_inventory_preflight_json.resolve(),
        "source_inventory_preflight_md": source_inventory_preflight_md.resolve(),
        "source_inventory_preflight_sha256s": source_inventory_preflight_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
        "output_dir": output_dir.resolve(),
    }
    source_preflight = _read_json_dict(paths["source_inventory_preflight_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    heads = _parse_key_values(_read_text(paths["source_inventory_preflight_artifact_dir"] / "HEADS"))
    gap = _gap_summary(source_preflight)
    checks = _checks(
        enabled=enabled,
        paths=paths,
        source_preflight=source_preflight,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        gap=gap,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "outcome_acquisition_plan_only": True,
            "outcome_acquisition_executed": False,
            "closed_loop_replay_execution": False,
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
        "source_hashes": _source_hashes(paths),
        "source_inventory_preflight_summary": _source_preflight_summary(source_preflight),
        "objective_gap_summary": gap,
        "acquisition_plan": _acquisition_plan(),
        "strict_pairing_contract": _strict_pairing_contract(),
        "no_go_register": _no_go_register(),
        "artifact_contract": _artifact_contract(),
        "plan_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, gap=gap),
    }


def _checks(
    *,
    enabled: bool,
    paths: dict[str, Path],
    source_preflight: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    gap: dict[str, Any],
) -> list[dict[str, Any]]:
    decision = _dict(source_preflight.get("final_decision"))
    analysis = _dict(source_preflight.get("analysis"))
    checks: list[dict[str, Any]] = [
        _expect("acquisition_plan_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("source_artifact_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
    ]
    for name, path in paths.items():
        if name == "output_dir":
            continue
        expected = "directory" if name.endswith("_artifact_dir") else "file"
        actual = path.is_dir() if expected == "directory" else path.is_file()
        checks.append(_check(f"{name}_exists", actual, str(path), expected))

    checks.extend(
        [
            _expect("source_preflight_passed", decision.get("passed"), True),
            _expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
            _expect("source_preflight_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            _expect("source_preflight_existing_artifacts_satisfy_objective", decision.get("existing_artifacts_satisfy_objective"), False),
            _expect("source_preflight_per_record_outcome_source_available", decision.get("per_record_outcome_source_available"), False),
            _expect("source_preflight_requires_acquisition_plan", decision.get("requires_acquisition_plan"), True),
            _expect("source_preflight_read_only", analysis.get("read_only"), True),
            _expect("source_preflight_replay_execution", analysis.get("replay_execution"), False),
            _expect("source_preflight_training_execution", analysis.get("training_execution"), False),
            _expect("source_preflight_candidate_generation", analysis.get("candidate_generation"), False),
            _expect("source_preflight_dp_modification", analysis.get("dp_modification"), False),
            _expect("source_preflight_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
            _expect("objective_required_records", gap["objective_required_records"], OBJECTIVE_REQUIRED_RECORDS),
            _expect("runtime_record_count", gap["runtime_record_count"], OBJECTIVE_REQUIRED_RECORDS),
            _expect("existing_delta_count", gap["existing_delta_count"], EXISTING_RUN_LEVEL_PAIR_TARGET),
            _expect("candidate_closed_loop_outcome_records", gap["candidate_closed_loop_outcome_records"], 0),
            _expect("missing_candidate_closed_loop_outcome_records", gap["missing_candidate_closed_loop_outcome_records"], OBJECTIVE_REQUIRED_RECORDS),
            _expect("existing_artifacts_satisfy_objective", gap["existing_artifacts_satisfy_objective"], False),
            _expect("requires_acquisition_plan", gap["requires_acquisition_plan"], True),
        ]
    )
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_preflight_{action}", decision.get(action), False))
    return checks


def _gap_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    inventory = _dict(source_preflight.get("inventory_summary"))
    return {
        "objective_required_records": int(inventory.get("objective_required_records") or 0),
        "runtime_record_count": int(inventory.get("runtime_record_count") or 0),
        "runtime_selection_log_count": int(inventory.get("runtime_selection_log_count") or 0),
        "existing_top1_summary_count": int(inventory.get("existing_top1_summary_count") or 0),
        "existing_shadow_summary_count": int(inventory.get("existing_shadow_summary_count") or 0),
        "existing_paired_run_key_count": int(inventory.get("existing_paired_run_key_count") or 0),
        "existing_delta_count": int(inventory.get("existing_delta_count") or 0),
        "candidate_closed_loop_outcome_records": int(inventory.get("candidate_closed_loop_outcome_records") or 0),
        "missing_candidate_closed_loop_outcome_records": int(inventory.get("missing_candidate_closed_loop_outcome_records") or 0),
        "per_record_outcome_source_available": inventory.get("per_record_outcome_source_available"),
        "existing_artifacts_satisfy_objective": inventory.get("existing_artifacts_satisfy_objective"),
        "requires_acquisition_plan": inventory.get("requires_acquisition_plan"),
    }


def _acquisition_plan() -> list[dict[str, Any]]:
    return [
        {
            "step": "build_fixed_dp_row_manifest",
            "execution": "future_read_only_preflight_then_execution_only",
            "purpose": "Enumerate all 3200 scenario/seed/sample/tl/run records and their fixed DP candidate tensor source.",
            "required_evidence": ["paired_key", "candidate_tensor_digest", "shadow_selected_index", "top1_index"],
        },
        {
            "step": "bind_shadow_selected_candidate_per_record",
            "execution": "future_read_only_preflight_then_execution_only",
            "purpose": "Bind CAMP output only to the fixed DP candidate row selected by shadow_selected_index.",
            "forbidden": ["trajectory_generation", "trajectory_repair", "trajectory_rewrite", "trajectory_blend"],
        },
        {
            "step": "execute_or_locate_shadow_selected_fixed_dp_candidate_outcomes",
            "execution": "future_execution_gate_after_static_review",
            "purpose": "Acquire missing closed-loop outcome summaries by executing or locating the selected fixed-DP candidate, not by changing it.",
            "target_count": OBJECTIVE_REQUIRED_RECORDS,
        },
        {
            "step": "enforce_strict_pairing_with_dp_top1",
            "execution": "future_materialization_gate",
            "purpose": "Pair every shadow-selected outcome with the same-key DP Top-1 outcome before SafetyCost delta calculation.",
            "pairing_keys": ["scenario", "seed", "sample", "traffic_light_mode", "run_key"],
        },
        {
            "step": "fail_closed_on_forbidden_sources",
            "execution": "all_future_gates",
            "purpose": "Reject Full36, formal seeds 11/12/13, closed-loop outcome training input, DP changes, and candidate mutation.",
        },
        {
            "step": "authorize_next_static_review_only",
            "execution": "this_gate",
            "purpose": "Review this acquisition plan before any acquisition/replay execution.",
        },
    ]


def _strict_pairing_contract() -> dict[str, Any]:
    return {
        "required_rows": OBJECTIVE_REQUIRED_RECORDS,
        "same_candidate_tensor_batch": True,
        "shadow_selection_source": "shadow_selected_index_only",
        "top1_source": "fixed_dp_candidate_tensor_top1",
        "allowed_camp_action": "rerank_or_select_fixed_dp_candidate_only",
        "safetycost_delta": "SafetyCost_v1(CAMP shadow-selected fixed-DP candidate execution) - SafetyCost_v1(DP Top-1 execution)",
        "forbidden_seed_policy": "no Full36 and no formal seeds 11/12/13",
        "closed_loop_outcomes_usage": "offline_evaluation_evidence_only",
    }


def _no_go_register() -> list[str]:
    return [
        "dp_head_drift",
        "candidate_tensor_identity_missing_or_mutated",
        "shadow_selected_candidate_not_from_fixed_dp_tensor",
        "camp_generates_repairs_rewrites_or_blends_trajectory",
        "full36_or_formal_seed_11_12_13_present",
        "closed_loop_outcome_used_for_training_or_online_input",
        "non_affine_score_or_non_simplex_weight",
        "promotion_deployment_online_selector_or_claim_before_claim_review",
    ]


def _artifact_contract() -> dict[str, Any]:
    return {
        "required_files": ["HEADS", "COMMAND", "stdout", "stderr", "run.exit", PLAN_JSON_NAME, PLAN_MD_NAME, "SHA256SUMS"],
        "nested_sha256s_required": True,
        "root_sha256s_required": True,
        "source_artifacts_required": ["objective_3200_outcome_source_inventory_preflight"],
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], gap: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "acquisition_plan_enabled" in failed:
        failure_class = "explicit_objective_3200_outcome_acquisition_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_preflight") for name in failed):
        failure_class = "source_inventory_preflight_contract_failure"
    else:
        failure_class = "objective_3200_outcome_acquisition_plan_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_outcome_acquisition_plan_ready": bool(passed),
        "objective_3200_outcome_acquisition_plan_static_review_authorized": bool(passed),
        "objective_required_records": gap["objective_required_records"],
        "candidate_closed_loop_outcome_records": gap["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": gap["missing_candidate_closed_loop_outcome_records"],
        "existing_artifacts_satisfy_objective": gap["existing_artifacts_satisfy_objective"],
        "requires_acquisition_execution": bool(passed),
        "direct_replay_execution_authorized": False,
        "direct_promotion_recommendation": False,
        "recommendation": "static_review_objective_3200_outcome_acquisition_plan_only" if passed else "repair_or_rerun_same_plan_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_preflight.get("final_decision"))
    inventory = _dict(source_preflight.get("inventory_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "objective_required_records": inventory.get("objective_required_records"),
        "candidate_closed_loop_outcome_records": inventory.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": inventory.get("missing_candidate_closed_loop_outcome_records"),
        "requires_acquisition_plan": inventory.get("requires_acquisition_plan"),
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
    return "\n".join(
        [
            "# Objective-3200 Outcome Acquisition Plan",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Gap",
            "",
            f"- Objective required records: `{gap['objective_required_records']}`",
            f"- Existing deltas: `{gap['existing_delta_count']}`",
            f"- Per-record shadow outcomes: `{gap['candidate_closed_loop_outcome_records']}`",
            f"- Missing per-record shadow outcomes: `{gap['missing_candidate_closed_loop_outcome_records']}`",
            f"- Existing artifacts satisfy objective: `{gap['existing_artifacts_satisfy_objective']}`",
            "",
            "## Boundary",
            "",
            "- Plan only: no outcome acquisition, replay execution, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
            f"- Score expression: `{report['analysis']['score_expression']}`",
        ]
    ) + "\n"


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


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _check(name: str, passed: bool, actual: Any | None = None, expected: Any = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual if actual is not None else bool(passed), "expected": expected}


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
