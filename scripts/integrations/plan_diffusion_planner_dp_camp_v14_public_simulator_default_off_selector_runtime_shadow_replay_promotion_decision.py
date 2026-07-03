#!/usr/bin/env python3
"""Planning-only v14 runtime default-off selector promotion decision gate.

This gate consumes the existing runtime shadow replay result review and the
read-only shadow-vs-Top1 delta review. It emits a conservative promotion
decision plan. It does not promote, deploy, train, replay, generate candidates,
modify Diffusion Planner, change an online selector, or make safety/CAMP-over-
DP claims.
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
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_decision_plan_v1"
)
SOURCE_RESULT_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_passed"
)
SOURCE_DELTA_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_vs_top1_delta_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_promotion_decision_plan_only_after_explicit_"
    "user_authorization"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_promotion_decision_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_promotion_decision_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_promotion_evidence_package_preflight_only"
)

DEFAULT_EXPECTED_COUNTS = {
    "selection_log_count": 32,
    "validation_summary_count": 32,
    "replay_summary_count": 32,
    "records": 3200,
    "shadow_selected_index_nonzero_records": 2832,
    "shadow_selected_index_differs_from_executed_index_records": 2832,
    "executed_top1_records": 3200,
    "selected_index_matches_executed_index_records": 3200,
    "default_off_selector_records": 3200,
    "feasible_records": 2914,
    "used_fallback_records": 286,
    "selection_score_better_records": 2832,
    "selection_score_tie_records": 368,
    "selection_score_worse_records": 0,
    "selection_score_uncomparable_records": 0,
    "shadow_diff_selection_score_better_records": 2832,
    "shadow_diff_selection_score_worse_records": 0,
}

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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime_result_review_json", type=Path, required=True)
    parser.add_argument("--shadow_vs_top1_delta_review_json", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    for name, default in DEFAULT_EXPECTED_COUNTS.items():
        parser.add_argument(f"--expected_{name}", type=int, default=default)
    parser.add_argument(
        "--enable_v14_runtime_promotion_decision_planning",
        action="store_true",
        help="Explicit opt-in for planning only; no promotion action is executed.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_result_review_json=args.runtime_result_review_json,
        shadow_vs_top1_delta_review_json=args.shadow_vs_top1_delta_review_json,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_runtime_promotion_decision_planning,
        expected_counts={
            name: getattr(args, f"expected_{name}")
            for name in DEFAULT_EXPECTED_COUNTS
        },
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_result_review_json: Path,
    shadow_vs_top1_delta_review_json: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
    expected_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    expected = dict(DEFAULT_EXPECTED_COUNTS)
    if expected_counts:
        expected.update(expected_counts)
    result_review = _read_json_dict(runtime_result_review_json)
    delta_review = _read_json_dict(shadow_vs_top1_delta_review_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    result_source = _result_review_summary(result_review)
    delta_source = _delta_review_summary(delta_review)
    checks = [
        _expect("planning_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect(
            "current_camp_head_matches_origin",
            current_camp_head,
            current_camp_origin_main,
        ),
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _check(
            "runtime_result_review_json_exists",
            runtime_result_review_json.is_file(),
            str(runtime_result_review_json),
            "file",
        ),
        _check(
            "shadow_vs_top1_delta_review_json_exists",
            shadow_vs_top1_delta_review_json.is_file(),
            str(shadow_vs_top1_delta_review_json),
            "file",
        ),
        _check("v14_audit_md_exists", v14_audit_md.is_file(), str(v14_audit_md), "file"),
        _check(
            "current_status_md_exists",
            current_status_md.is_file(),
            str(current_status_md),
            "file",
        ),
        *_result_review_checks(result_source, expected),
        *_delta_review_checks(delta_source, expected),
        *_audit_checks(v14_text, status_text),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "planning_only": True,
            "runtime_result_review_json": str(runtime_result_review_json.resolve()),
            "shadow_vs_top1_delta_review_json": str(
                shadow_vs_top1_delta_review_json.resolve()
            ),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "static_objective_delta_used_as_supporting_evidence": True,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "selector_promotion": False,
            "deployment": False,
            "dp_modification": False,
            "math_boundary": (
                "DP remains a fixed black-box candidate trajectory generator. "
                "CAMP may only shadow-rerank/select the current tick fixed "
                "finite DP candidate tensor by affine score_k(w)=a_k^T w over "
                "approved atoms with nonnegative simplex weights. This plan "
                "does not authorize selector promotion, atom promotion, "
                "deployment, online selector changes, trajectory changes, or "
                "safety/CAMP-over-DP claims."
            ),
        },
        "source_hashes": {
            "runtime_result_review_json": _sha256(runtime_result_review_json)
            if runtime_result_review_json.is_file()
            else None,
            "shadow_vs_top1_delta_review_json": _sha256(
                shadow_vs_top1_delta_review_json
            )
            if shadow_vs_top1_delta_review_json.is_file()
            else None,
        },
        "runtime_result_review_summary": result_source,
        "shadow_vs_top1_delta_review_summary": delta_source,
        "promotion_decision_plan": _promotion_decision_plan(),
        "evidence_package_preflight": _evidence_package_preflight(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_promotion_decision_plan.json", report)
    (output_dir / "runtime_promotion_decision_plan.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    result = report["runtime_result_review_summary"]
    delta = report["shadow_vs_top1_delta_review_summary"]
    plan = report["promotion_decision_plan"]
    lines = [
        "# V14 Runtime Default-Off Selector Promotion-Decision Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Recommendation: `{decision['recommendation']}`",
        f"- Immediate action: `{decision['immediate_action']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP-Top1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Source Result Review",
        "",
        f"- Status / passed: `{result['status']}` / `{result['passed']}`",
        f"- Selection logs / records: `{result['selection_log_count']}` / `{result['records']}`",
        f"- Executed DP Top-1 records: `{result['executed_top1_records']}`",
        f"- Shadow non-Top-1 records: `{result['shadow_selected_index_nonzero_records']}`",
        f"- Feasible / fallback records: `{result['feasible_records']}` / `{result['used_fallback_records']}`",
        f"- Score expression: `{result['score_expression']}`",
        "",
        "## Shadow-vs-Top1 Delta",
        "",
        f"- Status / passed: `{delta['status']}` / `{delta['passed']}`",
        f"- Static objective delta supported: `{delta['static_objective_delta_supported']}`",
        f"- Masked objective better/tie/worse/uncomparable: `{delta['selection_score_better_records']}` / `{delta['selection_score_tie_records']}` / `{delta['selection_score_worse_records']}` / `{delta['selection_score_uncomparable_records']}`",
        f"- Shadow-different better/worse: `{delta['shadow_diff_selection_score_better_records']}` / `{delta['shadow_diff_selection_score_worse_records']}`",
        f"- Claim scope: `{delta['claim_scope']}`",
        "",
        "## Required Evidence Before Any Promotion",
        "",
    ]
    for item in plan["required_evidence_before_promotion"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## No-Go Conditions", ""])
    for item in plan["no_go_conditions"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate is planning-only. It does not promote atoms or selectors, "
            "deploy a checkpoint, train CAMP, run replay, generate candidates, "
            "modify DP, change online selection, or authorize safety/CAMP-over-DP "
            "claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["plan_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _result_review_summary(review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(review.get("final_decision"))
    records = _dict(review.get("records"))
    execution = _dict(review.get("execution"))
    analysis = _dict(review.get("analysis"))
    heads = _dict(review.get("heads"))
    return {
        "schema_version": review.get("schema_version"),
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": list(decision.get("failed_checks") or []),
        "authorized_next_work": decision.get("authorized_next_work"),
        "promotion_decision_plan_authorized_next": bool(
            decision.get("promotion_decision_plan_authorized_next")
        ),
        "selector_promotion_authorized": bool(decision.get("selector_promotion_authorized")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "deployment_authorized": bool(decision.get("deployment_authorized")),
        "safety_benefit_claim_authorized": bool(
            decision.get("safety_benefit_claim_authorized")
        ),
        "camp_over_dp_top1_claim_authorized": bool(
            decision.get("camp_over_dp_top1_claim_authorized")
        ),
        "candidate_generation_executed_by_review": bool(
            analysis.get("candidate_generation_executed_by_review")
        ),
        "training_executed_by_review": bool(analysis.get("training_executed_by_review")),
        "replay_executed_by_review": bool(analysis.get("replay_executed_by_review")),
        "dp_modified_by_review": bool(analysis.get("dp_modified_by_review")),
        "current_dp_head": heads.get("current_dp_head"),
        "selection_log_count": execution.get("selection_log_count"),
        "validation_summary_count": execution.get("validation_summary_count"),
        "replay_summary_count": execution.get("replay_summary_count"),
        "formal_seed_path_count": execution.get("formal_seed_path_count"),
        "records": records.get("record_count"),
        "default_off_selector_records": records.get("default_off_selector_records"),
        "executed_top1_records": records.get("executed_top1_records"),
        "selected_index_matches_executed_index_records": records.get(
            "selected_index_matches_executed_index_records"
        ),
        "shadow_selected_index_nonzero_records": records.get(
            "shadow_selected_index_nonzero_records"
        ),
        "shadow_selected_index_differs_from_executed_index_records": records.get(
            "shadow_selected_index_differs_from_executed_index_records"
        ),
        "feasible_records": records.get("feasible_records"),
        "used_fallback_records": records.get("used_fallback_records"),
        "max_affine_score_error": records.get("max_affine_score_error"),
        "score_expression": analysis.get("score_expression")
        or decision.get("score_expression")
        or SCORE_EXPRESSION,
        "violation_counts": _dict(records.get("violation_counts")),
    }


def _delta_review_summary(review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(review.get("final_decision"))
    records = _dict(review.get("records"))
    analysis = _dict(review.get("analysis"))
    heads = _dict(review.get("heads"))
    selection = _dict(records.get("selection_score_comparison"))
    shadow_diff = _dict(
        records.get("selection_score_comparison_among_shadow_diff_records")
    )
    raw_affine = _dict(records.get("raw_affine_score_comparison"))
    return {
        "schema_version": review.get("schema_version"),
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": list(decision.get("failed_checks") or []),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_objective_delta_supported": bool(
            decision.get("static_objective_delta_supported")
        ),
        "selector_promotion_authorized": bool(decision.get("selector_promotion_authorized")),
        "deployment_authorized": bool(decision.get("deployment_authorized")),
        "safety_benefit_claim_authorized": bool(
            decision.get("safety_benefit_claim_authorized")
        ),
        "camp_over_dp_top1_claim_authorized": bool(
            decision.get("camp_over_dp_top1_claim_authorized")
        ),
        "current_dp_head": heads.get("current_dp_head"),
        "selection_log_count": records.get("selection_log_count"),
        "records": records.get("record_count"),
        "executed_top1_records": records.get("executed_top1_records"),
        "selected_index_matches_executed_index_records": records.get(
            "selected_matches_executed_records"
        ),
        "shadow_selected_index_nonzero_records": records.get(
            "shadow_selected_index_nonzero_records"
        ),
        "shadow_selected_index_differs_from_executed_index_records": records.get(
            "shadow_selected_index_differs_from_executed_index_records"
        ),
        "formal_seed_path_count": records.get("formal_seed_path_count"),
        "selection_score_better_records": selection.get("better_records"),
        "selection_score_tie_records": selection.get("tie_records"),
        "selection_score_worse_records": selection.get("worse_records"),
        "selection_score_uncomparable_records": selection.get("uncomparable_records"),
        "shadow_diff_selection_score_better_records": shadow_diff.get("better_records"),
        "shadow_diff_selection_score_worse_records": shadow_diff.get("worse_records"),
        "raw_affine_score_better_records": raw_affine.get("better_records"),
        "raw_affine_score_worse_records": raw_affine.get("worse_records"),
        "score_expression": analysis.get("score_expression"),
        "claim_scope": analysis.get("claim_scope"),
    }


def _result_review_checks(
    source: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    checks = [
        _expect("result_review_status_ready", source["status"], SOURCE_RESULT_REVIEW_STATUS),
        _expect("result_review_passed", source["passed"], True),
        _expect("result_review_failed_checks_empty", source["failed_checks"], []),
        _expect(
            "result_review_authorizes_this_planning_gate",
            source["authorized_next_work"],
            AUTHORIZED_CURRENT_WORK,
        ),
        _expect(
            "result_review_promotion_decision_plan_authorized_next",
            source["promotion_decision_plan_authorized_next"],
            True,
        ),
        _expect("result_current_dp_head_fixed", source["current_dp_head"], FIXED_DP_HEAD),
        _expect("result_selection_log_count", source["selection_log_count"], expected["selection_log_count"]),
        _expect("result_validation_summary_count", source["validation_summary_count"], expected["validation_summary_count"]),
        _expect("result_replay_summary_count", source["replay_summary_count"], expected["replay_summary_count"]),
        _expect("result_records", source["records"], expected["records"]),
        _expect("result_default_off_selector_records", source["default_off_selector_records"], expected["default_off_selector_records"]),
        _expect("result_executed_top1_records", source["executed_top1_records"], expected["executed_top1_records"]),
        _expect(
            "result_selected_matches_executed_records",
            source["selected_index_matches_executed_index_records"],
            expected["selected_index_matches_executed_index_records"],
        ),
        _expect("result_shadow_nonzero_records", source["shadow_selected_index_nonzero_records"], expected["shadow_selected_index_nonzero_records"]),
        _expect("result_shadow_diff_records", source["shadow_selected_index_differs_from_executed_index_records"], expected["shadow_selected_index_differs_from_executed_index_records"]),
        _expect("result_feasible_records", source["feasible_records"], expected["feasible_records"]),
        _expect("result_used_fallback_records", source["used_fallback_records"], expected["used_fallback_records"]),
        _expect("result_formal_seed_path_count_zero", source["formal_seed_path_count"], 0),
        _expect("result_score_expression_affine", source["score_expression"], SCORE_EXPRESSION),
    ]
    for name, value in source["violation_counts"].items():
        checks.append(_expect(f"result_violation_{name}_zero", value, 0))
    blocked = (
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "deployment_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
        "candidate_generation_executed_by_review",
        "training_executed_by_review",
        "replay_executed_by_review",
        "dp_modified_by_review",
    )
    checks.extend(_expect(f"result_{name}_false", source[name], False) for name in blocked)
    return checks


def _delta_review_checks(
    source: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    blocked = (
        "selector_promotion_authorized",
        "deployment_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
    )
    checks = [
        _expect("delta_review_status_ready", source["status"], SOURCE_DELTA_REVIEW_STATUS),
        _expect("delta_review_passed", source["passed"], True),
        _expect("delta_review_failed_checks_empty", source["failed_checks"], []),
        _expect(
            "delta_review_authorizes_this_planning_gate",
            source["authorized_next_work"],
            AUTHORIZED_CURRENT_WORK,
        ),
        _expect("delta_current_dp_head_fixed", source["current_dp_head"], FIXED_DP_HEAD),
        _expect(
            "delta_static_objective_supported",
            source["static_objective_delta_supported"],
            True,
        ),
        _expect("delta_selection_log_count", source["selection_log_count"], expected["selection_log_count"]),
        _expect("delta_records", source["records"], expected["records"]),
        _expect("delta_executed_top1_records", source["executed_top1_records"], expected["executed_top1_records"]),
        _expect(
            "delta_selected_matches_executed_records",
            source["selected_index_matches_executed_index_records"],
            expected["selected_index_matches_executed_index_records"],
        ),
        _expect("delta_shadow_nonzero_records", source["shadow_selected_index_nonzero_records"], expected["shadow_selected_index_nonzero_records"]),
        _expect("delta_shadow_diff_records", source["shadow_selected_index_differs_from_executed_index_records"], expected["shadow_selected_index_differs_from_executed_index_records"]),
        _expect("delta_selection_score_better_records", source["selection_score_better_records"], expected["selection_score_better_records"]),
        _expect("delta_selection_score_tie_records", source["selection_score_tie_records"], expected["selection_score_tie_records"]),
        _expect("delta_selection_score_worse_records", source["selection_score_worse_records"], expected["selection_score_worse_records"]),
        _expect("delta_selection_score_uncomparable_records", source["selection_score_uncomparable_records"], expected["selection_score_uncomparable_records"]),
        _expect("delta_shadow_diff_selection_score_better_records", source["shadow_diff_selection_score_better_records"], expected["shadow_diff_selection_score_better_records"]),
        _expect("delta_shadow_diff_selection_score_worse_records", source["shadow_diff_selection_score_worse_records"], expected["shadow_diff_selection_score_worse_records"]),
        _expect("delta_formal_seed_path_count_zero", source["formal_seed_path_count"], 0),
        _expect("delta_score_expression_affine", source["score_expression"], SCORE_EXPRESSION),
        _check(
            "delta_claim_scope_not_safety",
            "does not prove safety" in str(source["claim_scope"]),
            source["claim_scope"],
            "static objective only, no safety claim",
        ),
    ]
    checks.extend(_expect(f"delta_{name}_false", source[name], False) for name in blocked)
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        _expect(
            "audit_latest_status",
            _latest_value(v14_text, "current_v14_status"),
            SOURCE_DELTA_REVIEW_STATUS,
        ),
        _expect(
            "audit_latest_next_work",
            _latest_value(v14_text, "next_work_target"),
            AUTHORIZED_CURRENT_WORK,
        ),
        _expect(
            "status_doc_latest_status",
            _latest_value(status_text, "current_v14_status"),
            SOURCE_DELTA_REVIEW_STATUS,
        ),
        _expect(
            "status_doc_latest_next_work",
            _latest_value(status_text, "next_work_target"),
            AUTHORIZED_CURRENT_WORK,
        ),
        _expect(
            "audit_delta_review_passed",
            _latest_value(
                v14_text,
                "default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_passed",
            ),
            "True",
        ),
        _expect(
            "audit_delta_static_objective_supported",
            _latest_value(
                v14_text,
                "default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_static_objective_delta_supported",
            ),
            "True",
        ),
        _check(
            "status_doc_mentions_delta_scope",
            "static masked-objective delta" in status_text,
            "static masked-objective delta" in status_text,
            True,
        ),
    ]


def _promotion_decision_plan() -> dict[str, Any]:
    return {
        "recommendation": "do_not_promote_from_current_evidence_alone",
        "promotion_class_under_consideration": (
            "future_default_off_shadow_or_development_reranker_candidate"
        ),
        "immediate_action": "build_runtime_promotion_evidence_package_preflight_only",
        "delta_evidence_interpretation": (
            "shadow-vs-Top1 static masked objective delta is positive evidence "
            "for the current objective only, not safety, deployment, or CAMP "
            "superiority over DP Top-1"
        ),
        "required_evidence_before_promotion": [
            "immutable_artifact_manifest_for_runtime_result_delta_weights_scales_and_shadow_logs",
            "fixed_dp_head_and_fixed_candidate_tensor_contract_for_all_evidence",
            "default_off_fail_closed_selector_runtime_contract_with_executed_dp_top1",
            "shadow_vs_top1_delta_review_with_zero_masked_objective_worse_records",
            "independent_holdout_or_expanded_shadow_replay_evidence_with_zero_forbidden_effects",
            "explicit_metric_thresholds_before_any_safety_or_camp_over_dp_claim",
            "human_authorized_promotion_gate_after_evidence_package_review",
        ],
        "no_go_conditions": [
            "dp_head_differs_from_fixed_tieriv_commit",
            "camp_generates_modifies_blends_guides_or_postprocesses_trajectories",
            "score_expression_not_affine_or_weights_not_nonnegative_simplex",
            "online_selector_change_or_executed_trajectory_change_before_promotion",
            "closed_loop_outcome_used_as_training_or_online_input",
            "formal_seed_11_12_13_or_full36_used_without_explicit_gate",
            "safety_benefit_or_camp_over_dp_top1_claim_without_independent_evidence",
            "static_delta_evidence_used_as_closed_loop_outcome_claim",
        ],
    }


def _evidence_package_preflight() -> dict[str, Any]:
    return {
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "preflight_only": True,
        "promotion_authorized": False,
        "deployment_authorized": False,
        "training_authorized": False,
        "replay_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = sorted(check["name"] for check in checks if not check["passed"])
    plan = _promotion_decision_plan()
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "promotion_decision_plan_ready": bool(passed),
        "evidence_package_preflight_authorized": bool(passed),
        "recommendation": plan["recommendation"],
        "immediate_action": plan["immediate_action"],
        "promotion_class_under_consideration": plan[
            "promotion_class_under_consideration"
        ],
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "candidate_generation_authorized": False,
        "replay_execution_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "score_expression": SCORE_EXPRESSION,
    }


def _failure_class(failed: list[str]) -> str:
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    if any("planning_enabled" in check for check in failed):
        return "explicit_planning_authorization_missing"
    if any("delta_" in check for check in failed):
        return "shadow_vs_top1_delta_contract_failure"
    if any("count" in check or "records" in check for check in failed):
        return "source_result_shape_or_count_contract_failure"
    return "runtime_promotion_decision_plan_contract_failure"


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    values = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    return values[-1] if values else None


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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            entries.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _stable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
