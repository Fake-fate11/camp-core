#!/usr/bin/env python3
"""Plan remediation for v13 fresh evaluation split executed-index failures.

This is a plan-only gate after a rejected fresh evaluation execution. It reads
the failed evaluation artifact and the staged selection logs to attribute the
contract failure, then authorizes only a static contract review for the
remediation. It does not run DP, generate candidates, replay, train CAMP,
modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_plan_rejected"
)
FAILED_EVALUATION_STATUS = "dp_camp_v13_fresh_evaluation_split_evaluation_rejected"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_rejected_executed_index_contract_violation"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_static_contract_review_only"
)
AUDIT_FALSE_FLAGS = (
    "training_preflight_authorized_next",
    "training_execution_authorized_by_current_boundary",
    "runtime_shadow_selector_execution_authorized",
    "replay_execution_authorized_by_current_boundary",
    "fixed_dp_candidate_generation_authorized_by_current_boundary",
    "candidate_generation_by_camp_authorized_by_current_boundary",
    "trajectory_generation_by_camp_authorized_by_current_boundary",
    "trajectory_modification_by_camp_authorized_by_current_boundary",
    "dp_modification_authorized_by_current_boundary",
    "formal_seed_11_12_13_execution_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only remediation after fresh evaluation split execution "
            "rejects non-DP-top1 executed_index records."
        )
    )
    parser.add_argument("--failed_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        failed_execution_artifact_dir=args.failed_execution_artifact_dir,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    failed_execution_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    artifact_dir = failed_execution_artifact_dir.resolve()
    audit_md = v13_audit_md.resolve()
    result_json = artifact_dir / "fresh_evaluation_split_evaluation.json"
    failed_report = _load_json_dict(result_json)
    audit_text = _read_text(audit_md)
    source_log_summary = _summarize_source_logs(artifact_dir)
    failure_summary = _failure_summary(failed_report)
    remediation_plan = _remediation_plan()
    checks = _checks(
        artifact_dir=artifact_dir,
        result_json=result_json,
        audit_md=audit_md,
        audit_text=audit_text,
        failed_report=failed_report,
        failure_summary=failure_summary,
        source_log_summary=source_log_summary,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "read_only_inputs": True,
            "fresh_evaluation_split_evaluation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "failed_execution_artifact_dir": str(artifact_dir),
            "fresh_evaluation_split_evaluation_json": str(result_json),
            "v13_audit_md": str(audit_md),
        },
        "source_hashes": {
            "fresh_evaluation_split_evaluation_json_sha256": (
                _sha256(result_json) if result_json.is_file() else None
            ),
            "v13_audit_md_sha256": _sha256(audit_md) if audit_md.is_file() else None,
        },
        "failure_summary": failure_summary,
        "source_log_contract_summary": source_log_summary,
        "remediation_plan": remediation_plan,
        "review_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "static_contract_review_authorized_next": passed,
            "implementation_authorized_next": False,
            "fresh_evaluation_split_evaluation_execution_authorized_next": False,
            "fresh_evaluation_split_evaluation_result_review_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failure = report["failure_summary"]
    logs = report["source_log_contract_summary"]
    return "\n".join(
        [
            "# V13 Fresh Evaluation Split Executed-Index Failure Remediation Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Failed evaluation checks: `{failure['failed_checks']}`",
            f"- Evaluation records: `{failure['record_count']}`",
            f"- Executed-index violations: `{failure['executed_index_violations']}`",
            f"- Source logs inspected: `{logs['selection_log_count']}`",
            f"- Source records inspected: `{logs['record_count']}`",
            f"- Nonzero executed-index records: `{logs['nonzero_executed_index_records']}`",
            "",
            (
                "The next gate is static contract review only. The same failed "
                "execution artifact must not be treated as a passed holdout or "
                "replayed without member-source contract remediation."
            ),
            "",
        ]
    )


def _failure_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    evaluation = _dict(payload.get("evaluation"))
    clean_contract = _dict(payload.get("clean_contract"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "record_count": _int(evaluation.get("record_count")),
        "selection_log_count": _int(evaluation.get("selection_log_count")),
        "executed_index_violations": _int(evaluation.get("executed_index_violations")),
        "online_selector_change_violations": _int(
            evaluation.get("online_selector_change_violations")
        ),
        "closed_loop_outcome_records": _int(evaluation.get("closed_loop_outcome_records")),
        "shadow_differs_from_dp_top1_records": _int(
            evaluation.get("shadow_differs_from_dp_top1_records")
        ),
        "clean_contract_passed": clean_contract.get("passed"),
        "clean_contract_records": _int(clean_contract.get("records")),
        "clean_contract_failed_record_count": len(_list(clean_contract.get("failed_records"))),
    }


def _summarize_source_logs(artifact_dir: Path) -> dict[str, Any]:
    selection_logs = sorted((artifact_dir / "evaluation_selection_logs").rglob("camp_selection_log.json"))
    counts = {
        "selection_log_count": len(selection_logs),
        "record_count": 0,
        "nonzero_executed_index_records": 0,
        "nonzero_selected_index_records": 0,
        "selected_equals_executed_nonzero_records": 0,
        "missing_default_off_shadow_selector_records": 0,
        "missing_shadow_selected_index_records": 0,
        "selection_effect_true_records": 0,
        "online_selector_change_true_records": 0,
        "executed_output_policy_not_dp_top1_records": 0,
    }
    samples: list[dict[str, Any]] = []
    for log_path in selection_logs:
        for index, record in enumerate(_load_records(log_path)):
            if not isinstance(record, dict):
                continue
            counts["record_count"] += 1
            selected = _int(record.get("selected_index"))
            executed = _int(record.get("executed_index"))
            shadow = _int(record.get("shadow_selected_index"))
            selector = _dict(record.get("default_off_shadow_selector"))
            if executed not in (0, None):
                counts["nonzero_executed_index_records"] += 1
            if selected not in (0, None):
                counts["nonzero_selected_index_records"] += 1
            if selected == executed and selected not in (0, None):
                counts["selected_equals_executed_nonzero_records"] += 1
            if not selector:
                counts["missing_default_off_shadow_selector_records"] += 1
            if shadow is None:
                counts["missing_shadow_selected_index_records"] += 1
            if selector.get("selection_effect") is True or record.get("selection_effect") is True:
                counts["selection_effect_true_records"] += 1
            if selector.get("online_selector_change") is True:
                counts["online_selector_change_true_records"] += 1
            policy = selector.get("executed_output_policy", record.get("executed_output_policy"))
            if policy not in ("dp_top1", None):
                counts["executed_output_policy_not_dp_top1_records"] += 1
            if len(samples) < 5 and (
                executed not in (0, None) or not selector or shadow is None
            ):
                samples.append(
                    {
                        "relative_log": str(log_path.relative_to(artifact_dir)),
                        "record_index": index,
                        "selected_index": selected,
                        "executed_index": executed,
                        "shadow_selected_index": shadow,
                        "has_default_off_shadow_selector": bool(selector),
                        "selector_selection_effect": selector.get("selection_effect"),
                        "selector_executed_output_policy": selector.get("executed_output_policy"),
                    }
                )
    counts["sample_failure_records"] = samples
    return counts


def _remediation_plan() -> dict[str, Any]:
    return {
        "objective": (
            "prevent fresh evaluation execution from using member-source logs "
            "that encode CAMP selected_index as executed_index instead of "
            "default-off shadow_selected_index"
        ),
        "root_cause": (
            "the selected member source can be zero-overlap while still being "
            "legacy selection-log schema; zero-overlap alone does not prove "
            "executed output remains DP Top-1"
        ),
        "required_contracts": {
            "member_source_selection_must_require_default_off_shadow_selector_payload": True,
            "selected_index_must_remain_dp_top1_zero": True,
            "executed_index_must_remain_dp_top1_zero": True,
            "shadow_selected_index_required_for_camp_choice": True,
            "legacy_selection_logs_with_nonzero_executed_index_rejected": True,
            "zero_overlap_four_registries_still_required": True,
            "split_root_zero_alone_remains_insufficient": True,
            "same_failed_execution_artifact_must_not_be_reused_as_holdout": True,
        },
        "implementation_requirements": {
            "add_strict_default_off_member_source_filter_before_selection": True,
            "record_rejection_reasons_for_contract_failed_members": True,
            "require_zero_selected_contract_failed_members_in_selected_split": True,
            "preserve_existing_nonoverlap_registry_checks": True,
            "do_not_modify_candidate_tensors_or_trajectories": True,
            "do_not_change_dp_code_config_or_weights": True,
            "do_not_use_closed_loop_outcomes": True,
        },
        "verification_requirements": {
            "unit_test_rejects_legacy_nonzero_executed_index_member": True,
            "unit_test_accepts_default_off_shadow_member_with_shadow_index_nonzero": True,
            "materialized_fresh_member_source_must_pass_evaluation_execution_before_result_review": True,
            "formal_seeds_11_12_13_and_full36_remain_excluded": True,
            "score_expression_remains_affine": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "simplex_cvar_l2_master_remains_convex": True,
        },
        "blocked_by_this_plan": {
            "fresh_evaluation_split_evaluation_execution": True,
            "fresh_evaluation_split_evaluation_result_review": True,
            "training_preflight": True,
            "training_execution": True,
            "fixed_dp_candidate_generation": True,
            "replay_execution": True,
            "promotion": True,
            "deployment": True,
        },
    }


def _checks(
    *,
    artifact_dir: Path,
    result_json: Path,
    audit_md: Path,
    audit_text: str,
    failed_report: dict[str, Any],
    failure_summary: dict[str, Any],
    source_log_summary: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(failed_report.get("final_decision"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD, current_dp_head, FIXED_DP_HEAD),
        _check("failed_execution_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        _check("fresh_evaluation_split_evaluation_json_exists", result_json.is_file(), str(result_json), "file"),
        _check("v13_audit_md_exists", audit_md.is_file(), str(audit_md), "file"),
        _check("failed_evaluation_status_rejected", decision.get("status") == FAILED_EVALUATION_STATUS, decision.get("status"), FAILED_EVALUATION_STATUS),
        _check("failed_evaluation_passed_false", decision.get("passed") is False, decision.get("passed"), False),
        _check(
            "failed_evaluation_executed_index_check_present",
            "evaluation_executed_index_violations_zero" in failure_summary["failed_checks"],
            failure_summary["failed_checks"],
            "evaluation_executed_index_violations_zero",
        ),
        _check("failed_evaluation_authorized_next_absent", decision.get("authorized_next_work") is None, decision.get("authorized_next_work"), None),
        _check("failed_evaluation_records_present", (failure_summary["record_count"] or 0) > 0, failure_summary["record_count"], ">0"),
        _check("failed_evaluation_executed_index_violations_positive", (failure_summary["executed_index_violations"] or 0) > 0, failure_summary["executed_index_violations"], ">0"),
        _check("source_logs_present", source_log_summary["selection_log_count"] > 0, source_log_summary["selection_log_count"], ">0"),
        _check("source_records_present", source_log_summary["record_count"] > 0, source_log_summary["record_count"], ">0"),
        _check("source_logs_have_nonzero_executed_index_records", source_log_summary["nonzero_executed_index_records"] > 0, source_log_summary["nonzero_executed_index_records"], ">0"),
        _check("source_logs_have_legacy_missing_default_off_payloads", source_log_summary["missing_default_off_shadow_selector_records"] > 0, source_log_summary["missing_default_off_shadow_selector_records"], ">0"),
        _check("audit_latest_status_is_failure", _latest_value(audit_text, "current_v13_status") == LATEST_AUDIT_STATUS, _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _check("audit_latest_next_work", _latest_value(audit_text, "next_work_target") == authorized_current_work, _latest_value(audit_text, "next_work_target"), authorized_current_work),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(
            _check(
                f"audit_blocks_{flag}",
                _latest_value(audit_text, flag) == "False",
                _latest_value(audit_text, flag),
                "False",
            )
        )
    return checks


def _load_records(path: Path) -> list[Any]:
    payload = _load_json(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "selection_records", "steps"):
            records = payload.get(key)
            if isinstance(records, list):
                return records
    return []


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_json_dict(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
