#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "temporal_consistency_materiality_diagnosis_ready"
SOURCE_READY_NEXT_WORK = "temporal_consistency_atom_schema_preflight_only"
READY_STATUS = "temporal_consistency_atom_schema_preflight_ready"
REJECT_STATUS = "temporal_consistency_atom_schema_preflight_rejected"
AUTHORIZED_NEXT_WORK = "temporal_consistency_shadow_atom_dry_run_only"

ATOM_NAME = "previous_plan_temporal_consistency_rms_m"
PAYLOAD_KEY = "temporal_consistency_payload_logging"
COEFFICIENT_KEY = "previous_plan_temporal_consistency_rms_m"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
    "atom_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Schema-only preflight for the temporal-consistency atom candidate. "
            "This does not change CAMP selection or train weights."
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
    schema = _atom_schema(source)
    checks = [
        *_source_checks(source),
        *_schema_checks(schema),
        *_math_boundary_checks(schema),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_atom_schema_preflight_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "paths": paths or {},
            "math_boundary": (
                "This preflight defines a schema candidate only. The atom value "
                "is a current-tick finite-candidate coefficient produced by "
                "default-off logging before CAMP scoring and before closed-loop "
                "outcomes. Because the coefficient is fixed with respect to the "
                "weight vector w, adding it to an atom vector preserves affine "
                "score_k(w)=a_k^T w. The simplex/CVaR/L2 master remains convex. "
                "No trajectory-coordinate convexity and no DP-side classical "
                "Benders decomposition are claimed."
            ),
        },
        "source_summary": source,
        "atom_schema": schema,
        "schema_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    summary = report.get("materiality_summary") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "source_materiality_evidence": bool(
            decision.get("source_materiality_evidence")
        ),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_schema_preflight_authorized": bool(
            decision.get("atom_schema_preflight_authorized")
        ),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
        "available_records": int(decision.get("available_records", -1)),
        "lower_feasible_candidate_records": int(
            decision.get("lower_feasible_candidate_records", -1)
        ),
        "mean_feasible_gap_m": float(decision.get("mean_feasible_gap_m", -1.0)),
        "valid_records": int(summary.get("valid_records", -1)),
        "invalid_records": int(summary.get("invalid_records", -1)),
        "nonzero_range_records": int(summary.get("nonzero_range_records", -1)),
    }


def _atom_schema(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "atom_name": ATOM_NAME,
        "payload_key": PAYLOAD_KEY,
        "coefficient_key": COEFFICIENT_KEY,
        "direction": "lower_is_better",
        "candidate_axis": "finite_dp_candidate_index",
        "value_domain": "[0, +inf)",
        "nonnegative_by_definition": True,
        "signed_split_required": False,
        "hinge_required": False,
        "current_tick_observable": True,
        "uses_future_outcomes": False,
        "uses_closed_loop_outcomes": False,
        "selection_effect": False,
        "missing_policy": "fail_closed_unavailable_not_zero",
        "shape_contract": "length equals candidate_count when available",
        "score_term": "w_temporal_consistency * a_temporal_consistency,k",
        "affine_score_compatible": True,
        "convex_master_compatible": True,
        "classic_benders_claim": False,
        "trajectory_coordinate_convexity_claim": False,
        "scale_policy": (
            "schema-only; any later scale must be fixed from a declared "
            "calibration source before training/evaluation and cannot use "
            "future outcomes"
        ),
        "materiality_evidence": {
            "available_records": source["available_records"],
            "lower_feasible_candidate_records": source[
                "lower_feasible_candidate_records"
            ],
            "mean_feasible_gap_m": source["mean_feasible_gap_m"],
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_schema_preflight",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_materiality_evidence",
            source["source_materiality_evidence"],
            True,
        ),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal(
            "source_atom_schema_preflight_authorized",
            source["atom_schema_preflight_authorized"],
            True,
        ),
        _check_equal(
            "source_atom_promotion_not_authorized",
            source["atom_promotion_authorized"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_invalid_records_zero", source["invalid_records"], 0),
        _check_equal("source_has_material_available_records", source["available_records"] >= 40, True),
        _check_equal(
            "source_has_lower_feasible_alternatives",
            source["lower_feasible_candidate_records"] >= 20,
            True,
        ),
        _check_equal(
            "source_has_nonzero_ranges",
            source["nonzero_range_records"] >= 40,
            True,
        ),
    ]


def _schema_checks(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("atom_name_declared", schema["atom_name"], ATOM_NAME),
        _check_equal("payload_key_declared", schema["payload_key"], PAYLOAD_KEY),
        _check_equal("coefficient_key_declared", schema["coefficient_key"], COEFFICIENT_KEY),
        _check_equal("lower_is_better_direction", schema["direction"], "lower_is_better"),
        _check_equal("nonnegative_by_definition", schema["nonnegative_by_definition"], True),
        _check_equal("signed_split_not_required", schema["signed_split_required"], False),
        _check_equal("hinge_not_required", schema["hinge_required"], False),
        _check_equal("current_tick_observable", schema["current_tick_observable"], True),
        _check_equal("future_outcomes_not_used", schema["uses_future_outcomes"], False),
        _check_equal("closed_loop_outcomes_not_used", schema["uses_closed_loop_outcomes"], False),
        _check_equal("missing_policy_fail_closed", schema["missing_policy"], "fail_closed_unavailable_not_zero"),
    ]


def _math_boundary_checks(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("affine_score_compatible", schema["affine_score_compatible"], True),
        _check_equal("convex_master_compatible", schema["convex_master_compatible"], True),
        _check_equal("classic_benders_claim_false", schema["classic_benders_claim"], False),
        _check_equal(
            "trajectory_coordinate_convexity_claim_false",
            schema["trajectory_coordinate_convexity_claim"],
            False,
        ),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "atom_schema_preflight_ready": passed,
        "atom_promotion_authorized": False,
        "safety_benefit_evidence": False,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Run a shadow-only atom dry-run that appends this coefficient to a "
            "candidate atom table without changing online selection or training."
            if passed
            else "Reject this atom schema or repair the failed source/schema checks."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Temporal Consistency Atom Schema Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        "",
        "## Atom Schema",
        "",
        f"`{report['atom_schema']}`",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["schema_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
