#!/usr/bin/env python3
"""Plan-only gate for default-off member-source generation.

This gate follows a rematerialization attempt that correctly failed closed:
the available candidate member-source logs were non-overlapping, but all were
legacy logs without the default-off shadow selector contract. This script only
plans the next gate. It does not run DP, generate candidates, replay, train
CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
SCHEMA_VERSION = "dp_camp_v13_default_off_member_source_generation_plan_v1"
READY_STATUS = "dp_camp_v13_default_off_member_source_generation_plan_ready"
REJECT_STATUS = "dp_camp_v13_default_off_member_source_generation_plan_rejected"
REJECTED_BUILDER_STATUS = "dp_camp_v13_fresh_evaluation_split_member_source_builder_rejected"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fresh_member_"
    "source_rematerialization_rejected_no_valid_default_off_sources"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_static_contract_review_only"
)
AUDIT_FALSE_FLAGS = (
    "fresh_member_source_materialization_execution_authorized_next",
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "fresh_evaluation_split_evaluation_result_review_authorized_next",
    "data_preparation_authorized_next",
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
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
REQUIRED_PLAN_STEPS = (
    "generate_or_collect_new_fixed_dp_candidate_member_sources_only_after_static_review",
    "keep_dp_code_config_weights_at_fixed_commit",
    "record_default_off_shadow_selector_runtime_schema_for_every_tick",
    "keep_selected_index_and_executed_index_zero_for_every_record",
    "record_shadow_selected_index_as_camp_rerank_choice_without_execution_effect",
    "preserve_score_affine_score_k_w_equals_a_k_transpose_w",
    "forbid_camp_candidate_generation_trajectory_rewrite_blend_or_postprocess",
    "exclude_full36_and_formal_seeds_11_12_13",
    "run_zero_overlap_preflight_before_any_fresh_evaluation_or_training",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rematerialization_artifact_dir", type=Path, required=True)
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
        rematerialization_artifact_dir=args.rematerialization_artifact_dir,
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
    rematerialization_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    artifact_dir = rematerialization_artifact_dir.resolve()
    builder_report = artifact_dir / "rematerialized_outputs" / "member_source_builder_report.json"
    report_payload = _load_json_dict(builder_report)
    audit_text = _read_text(v13_audit_md)
    plan = _plan()
    checks = _checks(
        artifact_dir=artifact_dir,
        builder_report=builder_report,
        report_payload=report_payload,
        audit_text=audit_text,
        v13_audit_md=v13_audit_md,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        plan=plan,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
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
            "promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "rematerialization_artifact_dir": str(artifact_dir),
            "builder_report": str(builder_report),
            "v13_audit_md": str(v13_audit_md.resolve()),
        },
        "source_hashes": {
            "builder_report_sha256": _sha256(builder_report),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "rematerialization_summary": _rematerialization_summary(report_payload),
        "generation_plan": plan,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V13 Default-Off Member-Source Generation Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Static contract review authorized next: `{decision['static_contract_review_authorized_next']}`",
            f"- Fixed-DP candidate generation execution authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "The next gate is only a static contract review. Candidate generation "
            "remains forbidden until that review and later preflight gates pass.",
            "",
        ]
    )


def _plan() -> dict[str, Any]:
    return {
        "required_steps": list(REQUIRED_PLAN_STEPS),
        "failure_class": "no_valid_default_off_member_sources",
        "legacy_non_default_off_sources_reusable_as_holdout": False,
        "next_gate_is_static_contract_review_only": True,
        "fixed_dp_candidate_generation_execution_authorized_now": False,
        "candidate_generation_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "training_authorized": False,
        "score_expression": SCORE_EXPRESSION,
    }


def _checks(
    *,
    artifact_dir: Path,
    builder_report: Path,
    report_payload: dict[str, Any],
    audit_text: str,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    decision = _dict(report_payload.get("final_decision"))
    summary = _dict(report_payload.get("selection_summary"))
    zero_counts = _dict(summary.get("zero_intersection_counts"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("rematerialization_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory exists"),
        _check("builder_report_exists", builder_report.is_file(), str(builder_report), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("builder_status_rejected", decision.get("status"), REJECTED_BUILDER_STATUS),
        _expect("builder_passed_false", decision.get("passed"), False),
        _expect("builder_manifest_not_written", decision.get("member_source_manifest_written"), False),
        _check("builder_failed_no_selected_sources", "fresh_member_source_candidates_after_filters_nonempty" in _list(decision.get("failed_checks")), decision.get("failed_checks"), "contains no-selected failure"),
        _check("candidate_members_nonempty", _as_int(summary.get("candidate_member_count")) > 0, summary.get("candidate_member_count"), ">0"),
        _expect("selected_member_count_zero", _as_int(summary.get("selected_member_count")), 0),
        _check("all_candidates_rejected", _as_int(summary.get("rejected_member_count")) == _as_int(summary.get("candidate_member_count")), summary, "all candidates rejected"),
        _check("all_rejections_are_default_off_contract", _as_int(summary.get("rejected_default_off_contract_failed_count")) == _as_int(summary.get("candidate_member_count")), summary, "all rejected for default-off contract"),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_generation_plan", _latest_value(audit_text, "fresh_member_source_rematerialization_default_off_member_source_generation_plan_authorized_next"), "True"),
        _expect("plan_has_required_steps", sorted(plan["required_steps"]), sorted(REQUIRED_PLAN_STEPS)),
        _expect("plan_static_review_only", plan["next_gate_is_static_contract_review_only"], True),
    ]
    for key in ZERO_INTERSECTION_KEYS:
        checks.append(_expect(f"builder_{key}_zero", _as_int(zero_counts.get(key)), 0))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    return checks


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "static_contract_review_authorized_next": passed,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "replay_execution_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _rematerialization_summary(report_payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report_payload.get("final_decision"))
    summary = _dict(report_payload.get("selection_summary"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "candidate_member_count": summary.get("candidate_member_count"),
        "selected_member_count": summary.get("selected_member_count"),
        "rejected_member_count": summary.get("rejected_member_count"),
        "rejected_default_off_contract_failed_count": summary.get(
            "rejected_default_off_contract_failed_count"
        ),
        "zero_intersection_counts": summary.get("zero_intersection_counts"),
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
