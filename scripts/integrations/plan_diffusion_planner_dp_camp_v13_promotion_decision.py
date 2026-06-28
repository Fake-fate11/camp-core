#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_ready"
SOURCE_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_promotion_decision_plan_only_after_explicit_user_authorization"
)
READY_STATUS = "dp_camp_v13_promotion_decision_plan_ready"
REJECT_STATUS = "dp_camp_v13_promotion_decision_plan_rejected"
AUTHORIZED_NEXT_WORK = "dp_camp_v13_promotion_evidence_package_preflight_only"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
DEFAULT_EXPECTED_COUNTS = {
    "records_total": 51200,
    "records_without_feasible_candidate": 14058,
    "training_records": 11262,
    "validation_records": 2796,
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
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "production_selector_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Planning-only promotion-decision gate for the v13 DP-CAMP offline "
            "nonpromotion static reranker. It consumes the result-review "
            "artifact and emits a future evidence plan; it does not promote, "
            "deploy, train, replay, generate candidates, or modify DP."
        )
    )
    parser.add_argument("--result_review_json", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    for name, default in DEFAULT_EXPECTED_COUNTS.items():
        parser.add_argument(f"--expected_{name}", type=int, default=default)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_promotion_decision_planning",
        action="store_true",
        help="Explicit opt-in for planning only; no promotion action is executed.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        result_review=_load_json(args.result_review_json),
        result_review_json=str(args.result_review_json),
        current_camp_head=args.current_camp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        expected_counts={
            name: getattr(args, f"expected_{name}") for name in DEFAULT_EXPECTED_COUNTS
        },
        enabled=args.enable_v13_promotion_decision_planning,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_report(
    *,
    result_review: dict[str, Any],
    result_review_json: str,
    current_camp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    expected_counts: dict[str, int] | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    expected = _expected_counts(expected_counts)
    source_summary = _source_summary(result_review)
    checks = [
        _check_equal("planning_enabled", enabled, True),
        _check_equal("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check_true("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head),
        *_source_checks(source_summary),
        *_artifact_contract_checks(source_summary, expected),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_v13_promotion_decision_plan_v1",
            "label": label,
            "role": (
                "planning-only gate for deciding what evidence would be needed "
                "before any v13 static CAMP reranker promotion decision"
            ),
            "result_review_json": result_review_json,
            "current_camp_head": current_camp_head,
            "required_dp_head": required_dp_head,
            "planning_only": True,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "selector_promotion": False,
            "deployment": False,
            "dp_modification": False,
            "math_boundary": (
                "DP remains a fixed black-box candidate trajectory generator. "
                "Any future CAMP selector may only rerank the current tick's "
                "finite fixed DP candidates by affine score_k(w)=a_k^T w, "
                "with simplex/CVaR/L2 terms kept convex. This plan does not "
                "construct or claim a DP-side classical Benders decomposition."
            ),
        },
        "source_summary": source_summary,
        "promotion_decision_plan": _promotion_decision_plan(),
        "evidence_package_preflight": _evidence_package_preflight(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["promotion_decision_plan"]
    lines = [
        "# DP-CAMP V13 Promotion-Decision Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Actual promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- DP modification authorized: `{decision['dp_modification_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        "",
        "## Source",
        "",
        f"- Result-review status: `{source['status']}`",
        f"- Result-review passed: `{source['passed']}`",
        f"- Records total: `{source['records_total']}`",
        f"- Fallback-risk records: `{source['records_without_feasible_candidate']}`",
        f"- Training / validation: `{source['training_records']}` / `{source['validation_records']}`",
        f"- Candidates / atoms: `{source['num_candidates']}` / `{source['num_atoms']}`",
        f"- Score expression: `{source['score_expression']}`",
        "",
        "## Planning Decision",
        "",
        f"- Recommendation: `{plan['recommendation']}`",
        f"- Promotion class under consideration: `{plan['promotion_class_under_consideration']}`",
        f"- Immediate action: `{plan['immediate_action']}`",
        "",
        "## Required Evidence Before Any Promotion",
        "",
    ]
    for item in plan["required_evidence_before_promotion"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## No-Go Conditions",
            "",
        ]
    )
    for item in plan["no_go_conditions"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate does not promote atoms or selectors, deploy a checkpoint, "
            "train CAMP, run replay, generate candidates, modify DP, change an "
            "online selector, or authorize safety/CAMP-over-DP claims.",
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


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    artifact = _dict(report.get("artifact_summary"))
    return {
        "schema_version": report.get("schema_version"),
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "result_review_ready": bool(decision.get("result_review_ready")),
        "promotion_decision_plan_authorized": bool(
            decision.get("promotion_decision_plan_authorized")
        ),
        "selector_promotion_authorized": bool(decision.get("selector_promotion_authorized")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "deployment_authorized": bool(decision.get("deployment_authorized")),
        "deployable_checkpoint_claim_authorized": bool(
            decision.get("deployable_checkpoint_claim_authorized")
        ),
        "safety_benefit_claim_authorized": bool(
            decision.get("safety_benefit_claim_authorized")
        ),
        "camp_over_dp_top1_claim_authorized": bool(
            decision.get("camp_over_dp_top1_claim_authorized")
        ),
        "training_authorized": bool(decision.get("training_authorized")),
        "training_execution_authorized": bool(
            decision.get("training_execution_authorized")
        ),
        "replay_execution_authorized": bool(decision.get("replay_execution_authorized")),
        "candidate_generation_authorized": bool(
            decision.get("candidate_generation_authorized")
        ),
        "dp_modification_authorized": bool(decision.get("dp_modification_authorized")),
        "failed_checks": list(decision.get("failed_checks") or []),
        "records_total": artifact.get("records_total"),
        "records_without_feasible_candidate": artifact.get(
            "records_without_feasible_candidate"
        ),
        "records_with_feasible_candidate": artifact.get("records_with_feasible_candidate"),
        "training_records": artifact.get("training_records"),
        "validation_records": artifact.get("validation_records"),
        "num_candidates": artifact.get("num_candidates"),
        "num_atoms": artifact.get("num_atoms"),
        "atom_schema_version": artifact.get("atom_schema_version"),
        "score_expression": artifact.get("score_expression"),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status_ready", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_this_planning_gate",
            source["authorized_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_result_review_ready", source["result_review_ready"], True),
        _check_equal(
            "source_promotion_decision_plan_authorized",
            source["promotion_decision_plan_authorized"],
            True,
        ),
        _check_empty("source_failed_checks_empty", source["failed_checks"]),
        *[
            _check_equal(f"source_{name}_false", source[name], False)
            for name in BLOCKED_ACTIONS
            if name in source
        ],
    ]


def _expected_counts(expected_counts: dict[str, int] | None) -> dict[str, int]:
    expected = dict(DEFAULT_EXPECTED_COUNTS)
    if expected_counts:
        expected.update(expected_counts)
    return expected


def _artifact_contract_checks(
    source: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        _check_equal("records_total_v13", source["records_total"], expected["records_total"]),
        _check_equal(
            "records_without_feasible_candidate_v13",
            source["records_without_feasible_candidate"],
            expected["records_without_feasible_candidate"],
        ),
        _check_equal("training_records_v13", source["training_records"], expected["training_records"]),
        _check_equal("validation_records_v13", source["validation_records"], expected["validation_records"]),
        _check_equal("num_candidates_fixed", source["num_candidates"], 8),
        _check_equal("num_atoms_expected", source["num_atoms"], 14),
        _check_equal(
            "atom_schema_expected",
            source["atom_schema_version"],
            "dp_camp_v10_14d",
        ),
        _check_equal("score_expression_affine", source["score_expression"], "score_k(w)=a_k^T w"),
    ]


def _promotion_decision_plan() -> dict[str, Any]:
    return {
        "recommendation": "do_not_promote_from_current_evidence_alone",
        "promotion_class_under_consideration": (
            "future_default_off_shadow_or_development_reranker_candidate"
        ),
        "immediate_action": "build_evidence_package_preflight_only",
        "required_evidence_before_promotion": [
            "immutable_artifact_manifest_for_weights_scales_training_and_audits",
            "static_integration_contract_for_fixed_dp_candidate_reranking_only",
            "default_off_shadow_selector_wiring_plan_with_kill_switch",
            "latency_determinism_and_missing_candidate_behavior_preflight",
            "nonformal_closed_loop_evaluation_design_with_formal_seeds_forbidden",
            "predeclared_metrics_and_statistical_accept_reject_thresholds",
            "rollback_plan_and_runtime_observability_contract",
            "independent_safety_claim_gate_before_any_safety_language",
        ],
        "no_go_conditions": [
            "dp_head_differs_from_fixed_tieriv_commit",
            "candidate_tensor_contract_changes_or_k_not_8",
            "camp_generates_or_modifies_trajectories",
            "score_is_not_affine_in_simplex_weights",
            "formal_seed_11_12_13_usage",
            "online_selector_change_without_default_off_shadow_gate",
            "deployable_or_safety_claim_without_closed_loop_evidence_gate",
        ],
    }


def _evidence_package_preflight() -> dict[str, Any]:
    return {
        "status": "planned_not_executed",
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "execution_authorized_now": False,
        "inputs_to_collect": [
            "v13_result_review_json",
            "v13_training_summary_json",
            "v13_weights_json_and_npy",
            "v13_atom_scales_json",
            "v13_collection_and_pipeline_summaries",
            "nonpromotion_and_holdout_audit_json",
            "static_selector_integration_diff_or_contract",
        ],
    }


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "promotion_decision_plan_ready": passed,
        "evidence_package_preflight_authorized": passed,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "production_selector_change_authorized": False,
        "failed_checks": failed,
    }


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


def _check_true(name: str, passed: bool, observed: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": True,
    }


def _check_empty(name: str, observed: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": len(observed) == 0,
        "observed": _stable(observed),
        "expected": "[]",
    }


def _stable(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


if __name__ == "__main__":
    raise SystemExit(main())
