#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_dry_run import (  # noqa: E402
    ATOM_NAME,
    COEFFICIENT_FIELD,
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
    PAYLOAD_KEY,
)


SOURCE_READY_STATUS = "candidate_set_consensus_shadow_atom_dry_run_ready"
SOURCE_READY_NEXT_WORK = "candidate_set_consensus_shadow_atom_dry_run_result_review_only"
READY_STATUS = "candidate_set_consensus_shadow_atom_weight_sensitivity_plan_ready"
REJECT_STATUS = "candidate_set_consensus_shadow_atom_weight_sensitivity_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_weight_sensitivity_implementation_unit_tests_only"
)

DEFAULT_REPLAY_ROOT = (
    "/root/autodl-tmp/camp_dp_candidate_set_consensus_broader_nonformal_materiality"
)
DEFAULT_CANDIDATE_ROOT = f"{DEFAULT_REPLAY_ROOT}/logging_enabled"
DEFAULT_AUDIT_ROOT = f"{DEFAULT_REPLAY_ROOT}/audit"
DEFAULT_LAMBDA_GRID = (0.0, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0)
MAX_LAMBDA = 1.0

BLOCKED_ACTIONS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for a future candidate-set consensus shadow atom "
            "weight-sensitivity sweep over existing nonformal logs. It does "
            "not execute the sweep, run replay, train CAMP, promote atoms, or "
            "modify DP."
        )
    )
    parser.add_argument("--shadow_dry_run_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--candidate_root", default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--audit_root", default=DEFAULT_AUDIT_ROOT)
    parser.add_argument(
        "--lambda_grid",
        type=float,
        action="append",
        default=None,
        help="Predeclared nonnegative sensitivity weight. May be repeated.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        shadow_dry_run=_load_json(args.shadow_dry_run_json),
        label=args.label,
        candidate_root=args.candidate_root,
        audit_root=args.audit_root,
        lambda_grid=tuple(args.lambda_grid or DEFAULT_LAMBDA_GRID),
        paths={"shadow_dry_run_json": str(args.shadow_dry_run_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    shadow_dry_run: dict[str, Any],
    label: str | None = None,
    candidate_root: str = DEFAULT_CANDIDATE_ROOT,
    audit_root: str = DEFAULT_AUDIT_ROOT,
    lambda_grid: tuple[float, ...] = DEFAULT_LAMBDA_GRID,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(shadow_dry_run)
    plan = _sensitivity_plan(
        candidate_root=candidate_root,
        audit_root=audit_root,
        lambda_grid=lambda_grid,
    )
    checks = [
        *_source_checks(source),
        *_scope_checks(plan),
        *_lambda_grid_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_shadow_atom_weight_sensitivity_plan_v1",
            "label": label,
            "role": (
                "plan-only offline weight-sensitivity design after candidate-set "
                "consensus shadow dry-run result review"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "safety_score_fields_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "The planned sensitivity sweep may read existing nonformal "
                "selection logs and evaluate score'_k(lambda) = "
                "selection_score_k + lambda * "
                "candidate_set_consensus_center_rms_m[k] over fixed finite DP "
                "candidates. Lambda is predeclared, finite, nonnegative, and "
                "diagnostic only. The coefficient is fixed before scoring and "
                "the expression remains affine in weights. The sweep may not "
                "train CAMP, change deployed weights, run DP, use closed-loop "
                "outcomes or safety scores for selection, use formal seeds, "
                "or claim a DP-side classical Benders decomposition."
            ),
        },
        "source_summary": source,
        "sensitivity_plan": plan,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["sensitivity_plan"]
    lines = [
        "# Candidate-Set Consensus Shadow Atom Weight-Sensitivity Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Sensitivity implementation authorized: `{decision['sensitivity_implementation_authorized']}`",
        f"- Sensitivity execution authorized: `{decision['sensitivity_execution_authorized']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source",
        "",
        f"- Source status: `{source['status']}`",
        f"- Source authorized next work: `{source['authorized_next_work']}`",
        f"- Records: `{source['records']}`",
        f"- Valid records: `{source['valid_records']}`",
        f"- Ranking signal records: `{source['ranking_signal_records']}`",
        f"- Consensus-only changed records: `{source['consensus_only_changed_records']}`",
        f"- Max zero-weight score diff: `{source['max_shadow_zero_weight_score_abs_diff']}`",
        "",
        "## Planned Scope",
        "",
        f"- Candidate root: `{plan['candidate_root']}`",
        f"- Audit root: `{plan['audit_root']}`",
        f"- Expected logs: `{plan['expected_logs']}`",
        f"- Expected records: `{plan['expected_records']}`",
        f"- Expected candidates: `{plan['expected_candidates']}`",
        f"- Lambda grid: `{plan['lambda_grid']}`",
        f"- Formal seeds forbidden: `{plan['formal_seeds_forbidden']}`",
        "",
        "## Required Future Checks",
        "",
    ]
    for item in plan["required_sensitivity_checks"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan does not authorize sensitivity execution, replay, atom "
            "promotion, CAMP training, Full36, formal seeds, online selector "
            "changes, safety-benefit claims, DP modification, or a DP-side "
            "classical Benders claim.",
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
    summary = _dict(report.get("dry_run_summary"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "shadow_atom_dry_run_ready": bool(decision.get("shadow_atom_dry_run_ready")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "blocked_action_conflicts": conflicts,
        "records": int(summary.get("records", -1)),
        "valid_records": int(summary.get("valid_records", -1)),
        "available_records": int(summary.get("available_records", -1)),
        "shadow_appended_records": int(summary.get("shadow_appended_records", -1)),
        "ranking_signal_records": int(summary.get("ranking_signal_records", -1)),
        "consensus_only_changed_records": int(
            summary.get("consensus_only_would_change_selected_index_records", -1)
        ),
        "formal_seed_log_count": int(summary.get("formal_seed_log_count", -1)),
        "record_error_counts": dict(summary.get("record_error_counts") or {}),
        "max_shadow_zero_weight_score_abs_diff": _float(
            summary.get(
                "max_shadow_zero_weight_score_abs_diff",
                decision.get("max_shadow_zero_weight_score_abs_diff"),
            )
        ),
        "max_shadow_zero_weight_selection_score_abs_diff": _float(
            summary.get(
                "max_shadow_zero_weight_selection_score_abs_diff",
                decision.get("max_shadow_zero_weight_selection_score_abs_diff"),
            )
        ),
    }


def _sensitivity_plan(
    *,
    candidate_root: str,
    audit_root: str,
    lambda_grid: tuple[float, ...],
) -> dict[str, Any]:
    parsed_grid = [_float(value) for value in lambda_grid]
    return {
        "plan_only": True,
        "candidate_root": candidate_root,
        "audit_root": audit_root,
        "expected_logs": EXPECTED_LOGS,
        "expected_records": EXPECTED_RECORDS,
        "expected_candidates": EXPECTED_CANDIDATES,
        "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
        "atom_name": ATOM_NAME,
        "payload_key": PAYLOAD_KEY,
        "coefficient_field": COEFFICIENT_FIELD,
        "lambda_grid": parsed_grid,
        "max_lambda": MAX_LAMBDA,
        "score_formula": (
            "score_prime_k(lambda) = selection_score_k + lambda * "
            "candidate_set_consensus_center_rms_m[k]"
        ),
        "candidate_domain_policy": (
            "evaluate finite selection_scores only on feasible_mask true; retain "
            "logged selected_index for all-infeasible fallback records"
        ),
        "route_level_reporting": [
            "record_count",
            "ranking_signal_records",
            "changed_records_by_lambda",
            "critical_lambda_distribution",
            "selected_index_transition_counts",
        ],
        "accept_reject_criteria": [
            "source shadow dry-run passed with 60 valid available records",
            "formal_seed_log_count remains zero",
            "zero-weight shadow score deltas remain exactly zero in the source artifact",
            "lambda grid is finite, sorted, nonnegative, includes 0.0, and is bounded by 1.0",
            "future sensitivity implementation reads existing logs only and writes JSON/markdown/SHA/HEADS",
            "future sensitivity implementation reports route-level heterogeneity, including no-change routes",
        ],
        "required_sensitivity_checks": [
            "read existing logging_enabled camp_selection_log.json files only",
            "require exactly 6 logs, 60 records, and 8 candidates per valid record",
            "reject any run id or artifact path containing formal seed 11, 12, or 13",
            "require candidate_set_consensus_payload_logging.available=true for sensitivity records",
            "require coefficient field candidate_set_consensus_center_rms_m length equals candidate_count",
            "require coefficient values are finite and nonnegative",
            "use only selection_scores, feasible_mask, selected_index, fallback fields, and current-tick coefficient for selection",
            "do not use closed-loop outcomes or safety-score summaries to define or select candidates",
            "retain all-infeasible fallback records and report them separately",
            "evaluate score_prime_k(lambda) = selection_score_k + lambda * coefficient_k for predeclared lambda grid",
            "report per-lambda changed_records, route-level changes, critical lambda, and selected-index transitions",
            "write sensitivity JSON/markdown/SHA/HEADS artifacts before any later result-review gate",
            "do not change deployed atom schema, CAMP weights, online selector, DP code, or DP weights",
        ],
        "commands_if_later_implemented": {
            "implementation_target": (
                "scripts/integrations/analyze_diffusion_planner_candidate_set_"
                "consensus_shadow_atom_weight_sensitivity.py"
            ),
            "test_target": (
                "camp_core/tests/test_diffusion_planner_candidate_set_consensus_"
                "shadow_atom_weight_sensitivity.py"
            ),
            "cli_shape": [
                "python",
                "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity.py",
                "--shadow_dry_run_json",
                "<candidate_set_consensus_shadow_atom_dry_run.json>",
                "--candidate_root",
                candidate_root,
                "--expected_logs",
                str(EXPECTED_LOGS),
                "--expected_records",
                str(EXPECTED_RECORDS),
                "--expected_candidates",
                str(EXPECTED_CANDIDATES),
                "--output_json",
                f"{audit_root}/candidate_set_consensus_shadow_atom_weight_sensitivity.json",
                "--output_md",
                f"{audit_root}/candidate_set_consensus_shadow_atom_weight_sensitivity.md",
            ],
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_result_review",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_shadow_atom_dry_run_ready",
            source["shadow_atom_dry_run_ready"],
            True,
        ),
        _check_equal("source_atom_promotion_not_authorized", source["atom_promotion_authorized"], False),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_records", source["records"], EXPECTED_RECORDS),
        _check_equal("source_valid_records", source["valid_records"], EXPECTED_RECORDS),
        _check_equal("source_available_records", source["available_records"], EXPECTED_RECORDS),
        _check_equal("source_shadow_appended_records", source["shadow_appended_records"], EXPECTED_RECORDS),
        _check_equal("source_ranking_signal_present", source["ranking_signal_records"] > 0, True),
        _check_equal(
            "source_consensus_only_change_present",
            source["consensus_only_changed_records"] > 0,
            True,
        ),
        _check_equal("source_formal_seed_logs_zero", source["formal_seed_log_count"], 0),
        _check_equal("source_record_errors_empty", source["record_error_counts"], {}),
        _check_equal(
            "source_zero_weight_score_diff_zero",
            source["max_shadow_zero_weight_score_abs_diff"],
            0.0,
        ),
        _check_equal(
            "source_zero_weight_selection_score_diff_zero",
            source["max_shadow_zero_weight_selection_score_abs_diff"],
            0.0,
        ),
    ]


def _scope_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_only", plan["plan_only"], True),
        _check_equal("expected_logs", plan["expected_logs"], EXPECTED_LOGS),
        _check_equal("expected_records", plan["expected_records"], EXPECTED_RECORDS),
        _check_equal("expected_candidates", plan["expected_candidates"], EXPECTED_CANDIDATES),
        _check_equal(
            "formal_seeds_forbidden",
            sorted(plan["formal_seeds_forbidden"]),
            sorted(FORMAL_SEEDS),
        ),
        _check_equal("candidate_root_is_logging_enabled", plan["candidate_root"].endswith("/logging_enabled"), True),
        _check_equal("audit_root_declared", bool(plan["audit_root"]), True),
        _check_equal("atom_name", plan["atom_name"], ATOM_NAME),
        _check_equal("payload_key", plan["payload_key"], PAYLOAD_KEY),
        _check_equal("coefficient_field", plan["coefficient_field"], COEFFICIENT_FIELD),
    ]


def _lambda_grid_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    grid = list(plan.get("lambda_grid") or [])
    finite = all(math.isfinite(value) for value in grid)
    nonnegative = all(value >= 0.0 for value in grid)
    sorted_unique = grid == sorted(set(grid))
    return [
        _check_equal("lambda_grid_nonempty", bool(grid), True),
        _check_equal("lambda_grid_finite", finite, True),
        _check_equal("lambda_grid_nonnegative", nonnegative, True),
        _check_equal("lambda_grid_sorted_unique", sorted_unique, True),
        _check_equal("lambda_grid_contains_zero", 0.0 in grid, True),
        _check_equal("lambda_grid_has_positive_value", any(value > 0.0 for value in grid), True),
        _check_equal("lambda_grid_bounded", max(grid) <= plan["max_lambda"] if grid else False, True),
        _check_equal(
            "score_formula_affine",
            "selection_score_k + lambda *" in plan["score_formula"],
            True,
        ),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    required_text = " ".join(plan.get("required_sensitivity_checks") or []).lower()
    criteria_text = " ".join(plan.get("accept_reject_criteria") or []).lower()
    return [
        _check_equal("blocks_formal_seeds", "formal seed" in required_text, True),
        _check_equal("blocks_closed_loop_outcomes", "closed-loop outcomes" in required_text, True),
        _check_equal("blocks_safety_score_selection", "safety-score" in required_text, True),
        _check_equal("blocks_online_selector_change", "online selector" in required_text, True),
        _check_equal("blocks_dp_change", "dp code" in required_text and "dp weights" in required_text, True),
        _check_equal("requires_sha_heads_artifact", "sha/heads" in required_text, True),
        _check_equal("requires_route_level_reporting", "route-level" in criteria_text, True),
        _check_equal("fallback_policy_declared", "fallback" in plan["candidate_domain_policy"], True),
        _check_equal(
            "implementation_target_predeclared",
            plan["commands_if_later_implemented"]["implementation_target"].endswith(
                "candidate_set_consensus_shadow_atom_weight_sensitivity.py"
            ),
            True,
        ),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "weight_sensitivity_plan_ready": passed,
        "sensitivity_implementation_authorized": passed,
        "sensitivity_execution_authorized": False,
        "atom_promotion_authorized": False,
        "safety_benefit_evidence": False,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
