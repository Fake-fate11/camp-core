#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_broader_materiality import (
    AUTHORIZED_NEXT_WORK as SOURCE_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = "candidate_set_consensus_atom_design_review_plan_ready"
REJECT_STATUS = "candidate_set_consensus_atom_design_review_plan_rejected"
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_shadow_atom_dry_run_plan_only"

ATOM_NAME = "candidate_set_consensus_center_rms_cost_v1"
PAYLOAD_KEY = "candidate_set_consensus_payload_logging"
COEFFICIENT_FIELD = "candidate_set_consensus_center_rms_m"
MIN_VALID_RECORD_RATE = 0.80
MIN_POSITIVE_SPREAD_RATE = 0.25
MIN_RECORDS = 60
MIN_CANDIDATE_ROWS = 480

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
            "Plan-only atom design review for the candidate-set consensus "
            "coefficient after broader nonformal materiality passed. This "
            "does not implement, promote, train, replay, or modify DP."
        )
    )
    parser.add_argument("--materiality_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        materiality=_load_json(args.materiality_json),
        label=args.label,
        paths={"materiality_json": str(args.materiality_json)},
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
    materiality: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(materiality)
    atom = _atom_design(source)
    review = _review_protocol(source)
    checks = [
        *_source_checks(source),
        *_atom_design_checks(atom),
        *_math_boundary_checks(atom),
        *_review_protocol_checks(review),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_atom_design_review_plan_v1",
            "label": label,
            "role": (
                "plan-only atom design legality review after broader "
                "candidate-set consensus materiality; no atom implementation"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "The proposed atom is a fixed current-tick finite-candidate "
                "coefficient read from default-off payload logging after DP "
                "has generated the candidate tensor and before CAMP scoring. "
                "The coefficient is finite and nonnegative by construction, "
                "so no hinge or signed split is needed. If a later dry-run "
                "gate appends it as an atom coefficient a_k, CAMP scoring "
                "remains affine as score_k(w)=a_k^T w and the simplex/CVaR/L2 "
                "master remains convex in w. DP remains a black-box candidate "
                "generator, and this review constructs no DP-side classical "
                "Benders master/subproblem, dual, or valid cuts."
            ),
        },
        "source_summary": source,
        "proposed_atom_design": atom,
        "review_protocol": review,
        "design_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    atom = report["proposed_atom_design"]
    source = report["source_summary"]
    lines = [
        "# Candidate-Set Consensus Atom Design Review Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Atom design review ready: `{decision['atom_design_review_ready']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Evidence",
        "",
        f"- Source status: `{source['status']}`",
        f"- Materiality gate passed: `{source['materiality_gate_passed']}`",
        f"- Signal present: `{source['signal_present']}`",
        f"- Records: `{source['records']}`",
        f"- Valid record rate: `{source['valid_record_rate']}`",
        f"- Candidate rows: `{source['candidate_rows']}`",
        f"- Positive spread rate: `{source['positive_spread_rate']}`",
        f"- Selected not best records: `{source['selected_not_consensus_best_records']}`",
        f"- Finite lambda records: `{source['finite_lambda_records']}`",
        "",
        "## Proposed Atom",
        "",
        f"- Atom name: `{atom['atom_name']}`",
        f"- Payload key: `{atom['payload_key']}`",
        f"- Coefficient field: `{atom['coefficient_field']}`",
        f"- Direction: `{atom['direction']}`",
        f"- Value domain: `{atom['value_domain']}`",
        f"- Missing policy: `{atom['missing_policy']}`",
        f"- Normalization policy: {atom['normalization_policy']}",
        "",
        "## Review Protocol",
        "",
    ]
    for item in report["review_protocol"]["required_next_gate_checks"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan does not authorize atom promotion, CAMP retraining, "
            "Full36, formal seeds, online selector changes, DP modification, "
            "or a DP-side classical Benders claim.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["design_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    summary = _dict(report.get("record_summary"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "screen_completed": bool(decision.get("screen_completed")),
        "materiality_gate_passed": bool(decision.get("materiality_gate_passed")),
        "signal_present": bool(decision.get("signal_present")),
        "sample_too_small_for_promotion": bool(
            decision.get("sample_too_small_for_promotion")
        ),
        "atom_design_review_plan_authorized": bool(
            decision.get("atom_design_review_plan_authorized")
        ),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "blocked_action_conflicts": conflicts,
        "formal_seed_run_ids": list(summary.get("formal_seed_run_ids") or []),
        "records": int(summary.get("records", -1)),
        "valid_records": int(summary.get("valid_records", -1)),
        "valid_record_rate": _float(summary.get("valid_record_rate")),
        "candidate_rows": int(summary.get("candidate_rows", -1)),
        "valid_candidate_rows": int(summary.get("valid_candidate_rows", -1)),
        "positive_spread_records": int(summary.get("positive_spread_records", -1)),
        "positive_spread_rate": _float(summary.get("positive_spread_rate")),
        "selected_not_consensus_best_records": int(
            summary.get("selected_not_consensus_best_records", -1)
        ),
        "finite_lambda_records": int(summary.get("finite_lambda_records", -1)),
        "min_lambda_to_change_any_record": _float(
            summary.get("min_lambda_to_change_any_record")
        ),
    }


def _atom_design(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "atom_name": ATOM_NAME,
        "payload_key": PAYLOAD_KEY,
        "coefficient_field": COEFFICIENT_FIELD,
        "payload_schema_version": "candidate_set_consensus_payload_v1",
        "definition": (
            "For each current-tick DP candidate k, compute the RMS xy distance "
            "between candidate k and the coordinate-wise median centerline of "
            "the same finite candidate set over the logged prefix horizon."
        ),
        "candidate_axis": "finite_dp_candidate_index",
        "direction": "lower_is_better",
        "value_domain": "nonnegative_finite_scalar_per_candidate",
        "units": "meters",
        "nonnegative_by_definition": True,
        "hinge_required": False,
        "signed_split_required": False,
        "current_tick_observable": True,
        "computed_before_scoring": True,
        "uses_future_outcomes": False,
        "uses_closed_loop_outcomes": False,
        "uses_safety_scores": False,
        "selection_effect": False,
        "shape_contract": "length equals candidate_count when payload is available",
        "missing_policy": "fail_closed_unavailable_not_zero",
        "normalization_policy": (
            "schema-only; any scale must be fixed in a later plan from "
            "predeclared nonformal calibration statistics before training or "
            "evaluation and cannot use outcomes"
        ),
        "score_term": "w_candidate_set_consensus * a_candidate_set_consensus,k",
        "affine_score_compatible": True,
        "convex_master_compatible": True,
        "classic_benders_claim": False,
        "dp_modification_required": False,
        "materiality_evidence": {
            "records": source["records"],
            "valid_records": source["valid_records"],
            "valid_record_rate": source["valid_record_rate"],
            "candidate_rows": source["candidate_rows"],
            "positive_spread_rate": source["positive_spread_rate"],
            "selected_not_consensus_best_records": source[
                "selected_not_consensus_best_records"
            ],
            "finite_lambda_records": source["finite_lambda_records"],
            "min_lambda_to_change_any_record": source[
                "min_lambda_to_change_any_record"
            ],
        },
    }


def _review_protocol(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_type": "plan_only",
        "authorized_next_gate": AUTHORIZED_NEXT_WORK,
        "required_next_gate_checks": [
            "append atom in a shadow-only table without changing runtime selection",
            "prove payload field shape equals candidate_count for every valid record",
            "prove nonnegative finite coefficient contract remains true",
            "prove source rows are nonformal and contain no seed 11/12/13 runs",
            "prove selector-visible scores, weights, atoms, and selected_index are unchanged",
            "record artifact JSON/markdown/SHA/HEADS before any later implementation gate",
            "keep safety scores and closed-loop outcomes out of online coefficients",
            "keep atom promotion, CAMP retraining, Full36, formal seeds, online selector changes, and DP modification blocked",
        ],
        "minimum_evidence_to_carry_forward": {
            "records": source["records"],
            "valid_record_rate": source["valid_record_rate"],
            "positive_spread_rate": source["positive_spread_rate"],
            "finite_lambda_records": source["finite_lambda_records"],
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_atom_design_review",
            source["authorized_next_work"],
            SOURCE_NEXT_WORK,
        ),
        _check_equal("source_screen_completed", source["screen_completed"], True),
        _check_equal("source_materiality_gate_passed", source["materiality_gate_passed"], True),
        _check_equal("source_signal_present", source["signal_present"], True),
        _check_equal(
            "source_sample_not_too_small",
            source["sample_too_small_for_promotion"],
            False,
        ),
        _check_equal(
            "source_atom_design_review_plan_authorized",
            source["atom_design_review_plan_authorized"],
            True,
        ),
        _check_equal(
            "source_atom_promotion_not_authorized",
            source["atom_promotion_authorized"],
            False,
        ),
        _check_equal(
            "source_safety_benefit_not_claimed",
            source["safety_benefit_evidence"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_no_formal_seed_runs", source["formal_seed_run_ids"], []),
        _check_gte("source_records", source["records"], MIN_RECORDS),
        _check_gte("source_valid_record_rate", source["valid_record_rate"], MIN_VALID_RECORD_RATE),
        _check_gte("source_candidate_rows", source["candidate_rows"], MIN_CANDIDATE_ROWS),
        _check_gte(
            "source_positive_spread_rate",
            source["positive_spread_rate"],
            MIN_POSITIVE_SPREAD_RATE,
        ),
        _check_gte(
            "source_selected_not_best_records",
            source["selected_not_consensus_best_records"],
            1,
        ),
        _check_gte("source_finite_lambda_records", source["finite_lambda_records"], 1),
    ]


def _atom_design_checks(atom: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("atom_name_declared", atom["atom_name"], ATOM_NAME),
        _check_equal("payload_key_declared", atom["payload_key"], PAYLOAD_KEY),
        _check_equal("coefficient_field_declared", atom["coefficient_field"], COEFFICIENT_FIELD),
        _check_equal("direction_lower_is_better", atom["direction"], "lower_is_better"),
        _check_equal(
            "domain_nonnegative_finite",
            atom["value_domain"],
            "nonnegative_finite_scalar_per_candidate",
        ),
        _check_equal("nonnegative_by_definition", atom["nonnegative_by_definition"], True),
        _check_equal("hinge_not_required", atom["hinge_required"], False),
        _check_equal("signed_split_not_required", atom["signed_split_required"], False),
        _check_equal("current_tick_observable", atom["current_tick_observable"], True),
        _check_equal("computed_before_scoring", atom["computed_before_scoring"], True),
        _check_equal("future_outcomes_not_used", atom["uses_future_outcomes"], False),
        _check_equal("closed_loop_outcomes_not_used", atom["uses_closed_loop_outcomes"], False),
        _check_equal("safety_scores_not_used", atom["uses_safety_scores"], False),
        _check_equal("selection_effect_false", atom["selection_effect"], False),
        _check_equal("missing_policy_fail_closed", atom["missing_policy"], "fail_closed_unavailable_not_zero"),
    ]


def _math_boundary_checks(atom: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("affine_score_compatible", atom["affine_score_compatible"], True),
        _check_equal("convex_master_compatible", atom["convex_master_compatible"], True),
        _check_equal("classic_benders_claim_false", atom["classic_benders_claim"], False),
        _check_equal("dp_modification_not_required", atom["dp_modification_required"], False),
    ]


def _review_protocol_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    joined = " ".join(review["required_next_gate_checks"]).lower()
    return [
        _check_equal("review_is_plan_only", review["review_type"], "plan_only"),
        _check_equal(
            "review_authorizes_shadow_atom_dry_run_plan",
            review["authorized_next_gate"],
            AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("review_requires_shadow_only", "shadow-only" in joined, True),
        _check_equal("review_blocks_promotion", "promotion" in joined, True),
        _check_equal("review_blocks_retraining", "retraining" in joined, True),
        _check_equal("review_blocks_formal_seeds", "formal seeds" in joined, True),
        _check_equal("review_blocks_dp_modification", "dp modification" in joined, True),
        _check_equal("review_requires_sha_heads", "sha/heads" in joined, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "atom_design_review_ready": passed,
        "shadow_atom_dry_run_plan_authorized": passed,
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


def _check_gte(name: str, observed: Any, expected: float) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": f">= {expected}",
        "passed": _float(observed) >= float(expected),
    }


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
