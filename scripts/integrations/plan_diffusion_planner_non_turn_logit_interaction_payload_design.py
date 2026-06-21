#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_CAMP_ATOM_NAMES_V10,
)


READY_STATUS = "non_turn_logit_interaction_payload_design_plan_ready"
REJECT_STATUS = "non_turn_logit_interaction_payload_design_plan_rejected"
SOURCE_STATUS = (
    "non_turn_logit_interaction_atom_preflight_promising_for_payload_design"
)
SOURCE_NEXT_WORK = "non_turn_logit_interaction_atom_payload_design_plan_only"
AUTHORIZED_NEXT_WORK = "implement_default_off_non_turn_logit_interaction_payload_only"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "online_optimization_promotion_authorized",
    "schema_promotion_authorized",
)


@dataclass(frozen=True)
class PayloadFieldPlan:
    name: str
    expression: str
    source_fields: tuple[str, ...]
    role: str
    add_as_new_atom_candidate: bool
    duplicate_status: str
    rationale: str


PAYLOAD_FIELDS: tuple[PayloadFieldPlan, ...] = (
    PayloadFieldPlan(
        name="route_progress_deficit_vs_top1_m",
        expression="max(candidate_route_progress[0] - candidate_route_progress[k], 0)",
        source_fields=("candidate_route_progress",),
        role="diagnostic_source",
        add_as_new_atom_candidate=False,
        duplicate_status="near_existing_progress_shortfall",
        rationale=(
            "The best screen uses this progress-loss signal, but the deployed "
            "v10 schema already contains progress_shortfall. Keep it in the "
            "payload only to audit the interaction input; do not add it as a "
            "new schema dimension."
        ),
    ),
    PayloadFieldPlan(
        name="dp_prior_jerk_excess_cost",
        expression="max(candidate_dp_prior_jerk_excess_cost[k], 0)",
        source_fields=("candidate_dp_prior_jerk_excess_cost",),
        role="diagnostic_source",
        add_as_new_atom_candidate=False,
        duplicate_status="exact_existing_dp_camp_v10_atom",
        rationale=(
            "The deployed v10 schema already contains dp_prior_jerk_excess_cost. "
            "Keep it in the payload only to audit the interaction input."
        ),
    ),
    PayloadFieldPlan(
        name="comfort_progress_interaction_cost",
        expression=(
            "route_progress_deficit_vs_top1_m * dp_prior_jerk_excess_cost"
        ),
        source_fields=(
            "candidate_route_progress",
            "candidate_dp_prior_jerk_excess_cost",
        ),
        role="new_interaction_atom_candidate",
        add_as_new_atom_candidate=True,
        duplicate_status="not_in_dp_camp_v10_schema",
        rationale=(
            "The preflight found promising screens driven by progress loss and "
            "jerk cost. The interaction is not an existing v10 atom and exposes "
            "the joint penalty while preserving fixed candidate coefficients."
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for a default-off non-turn-logit interaction "
            "payload. It consumes a promising preflight artifact and checks "
            "that proposed new atom candidates are not merely duplicates of "
            "the existing DP-CAMP v10 schema."
        )
    )
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        preflight_report=_read_json(args.preflight_json),
        label=args.label,
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
    preflight_report: dict[str, Any],
    label: str | None = None,
    payload_fields: tuple[PayloadFieldPlan, ...] = PAYLOAD_FIELDS,
    existing_atom_names: tuple[str, ...] = DP_CAMP_ATOM_NAMES_V10,
) -> dict[str, Any]:
    source_checks = _source_checks(preflight_report)
    overlap_checks = _overlap_checks(payload_fields, existing_atom_names)
    design_checks = _design_checks(payload_fields, preflight_report)
    passed = all(
        check["passed"] for check in [*source_checks, *overlap_checks, *design_checks]
    )
    return {
        "analysis": {
            "name": "dp_camp_non_turn_logit_interaction_payload_design_plan_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "schema_promotion": False,
            "future_outcome_labels_used": False,
            "existing_atom_schema": {
                "version": "dp_camp_v10_14d",
                "atom_names": list(existing_atom_names),
            },
            "payload_schema": {
                "schema_version": "dp_camp_non_turn_logit_interaction_payload_v1",
                "default_off": True,
                "selection_effect": False,
                "future_outcome_leakage": False,
                "closed_loop_outcome_fields_read": False,
                "classic_benders_claim": False,
            },
            "math_boundary": (
                "The payload computes fixed current-tick candidate coefficients "
                "from logged route progress and DP-prior jerk cost before any "
                "closed-loop outcome label. Existing progress and jerk terms are "
                "kept as diagnostics only; the proposed new candidate is their "
                "nonnegative product. If later promoted after further evidence, "
                "it would enter as a fixed a_k coefficient, preserving affine "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 convex master. "
                "This plan does not claim trajectory-coordinate convexity or "
                "construct a DP-side classical Benders decomposition."
            ),
        },
        "source_checks": source_checks,
        "overlap_checks": overlap_checks,
        "design_checks": design_checks,
        "selected_payload_fields": [_field_payload(field) for field in payload_fields],
        "preflight_summary": _preflight_summary(preflight_report),
        "accept_criteria_for_next_gate": _accept_criteria(),
        "reject_criteria_for_next_gate": _reject_criteria(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "payload_implementation_authorized": passed,
            "new_replay_authorized": False,
            "schema_promotion_authorized": False,
            "CAMP_retraining_authorized": False,
            "online_selector_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _source_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    decision = report.get("final_decision", {})
    records = report.get("records", {})
    return [
        {
            "name": "source_preflight_promising",
            "passed": decision.get("status") == SOURCE_STATUS
            and decision.get("passed") is True
            and decision.get("authorized_next_work") == SOURCE_NEXT_WORK,
            "status": decision.get("status"),
            "authorized_next_work": decision.get("authorized_next_work"),
        },
        {
            "name": "source_preflight_blocks_training_and_promotion",
            "passed": decision.get("camp_retraining_authorized") is False
            and decision.get("online_selector_authorized") is False
            and decision.get("full36_authorized") is False
            and decision.get("formal_seeds_authorized") is False
            and decision.get("dp_modification_authorized") is False,
            "decision": decision,
        },
        {
            "name": "source_support_material_and_nonformal",
            "passed": int(records.get("formal_seed_records", -1)) == 0
            and int(records.get("missing_feature_records", -1)) == 0
            and int(records.get("alternative_rows", 0)) > 0
            and int(records.get("class_counts", {}).get("beneficial_alternative", 0))
            > 0
            and int(records.get("class_counts", {}).get("harmful_alternative", 0))
            > 0,
            "records": records,
        },
    ]


def _overlap_checks(
    fields: tuple[PayloadFieldPlan, ...],
    existing_atom_names: tuple[str, ...],
) -> list[dict[str, Any]]:
    existing = set(existing_atom_names)
    new_fields = [field for field in fields if field.add_as_new_atom_candidate]
    duplicate_new = [
        field.name
        for field in new_fields
        if field.name in existing or field.duplicate_status.startswith("exact_existing")
    ]
    diagnostics = [field for field in fields if not field.add_as_new_atom_candidate]
    return [
        {
            "name": "new_atom_candidates_nonempty",
            "passed": bool(new_fields),
            "new_atom_candidates": [field.name for field in new_fields],
        },
        {
            "name": "new_atom_candidates_not_existing_schema_duplicates",
            "passed": not duplicate_new,
            "duplicate_new_atom_candidates": duplicate_new,
            "existing_atom_names": list(existing_atom_names),
        },
        {
            "name": "known_overlaps_kept_diagnostic_only",
            "passed": all(
                field.name not in existing or not field.add_as_new_atom_candidate
                for field in diagnostics
            )
            and any(
                field.duplicate_status != "not_in_dp_camp_v10_schema"
                for field in diagnostics
            ),
            "diagnostic_only_fields": [field.name for field in diagnostics],
        },
    ]


def _design_checks(
    fields: tuple[PayloadFieldPlan, ...],
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    ranked = report.get("ranked_screens") or []
    promising = [
        screen
        for screen in ranked
        if isinstance(screen, dict) and screen.get("promising_screen") is True
    ]
    descriptor_sets = [
        set(screen.get("descriptor_names") or [])
        for screen in promising
        if isinstance(screen.get("descriptor_names"), list)
    ]
    new_candidate_names = {
        field.name for field in fields if field.add_as_new_atom_candidate
    }
    source_names = {
        "route_progress_deficit_vs_top1_m",
        "dp_prior_jerk_excess_cost",
    }
    return [
        {
            "name": "preflight_has_promising_screens",
            "passed": bool(promising),
            "promising_screen_count": len(promising),
        },
        {
            "name": "payload_sources_match_best_preflight_family",
            "passed": any(source_names.issubset(names) for names in descriptor_sets),
            "required_source_family": sorted(source_names),
        },
        {
            "name": "new_interaction_candidate_supported_by_preflight",
            "passed": any(names & new_candidate_names for names in descriptor_sets),
            "new_atom_candidates": sorted(new_candidate_names),
        },
        {
            "name": "payload_field_math_flags",
            "passed": all(
                field.expression
                and field.source_fields
                and field.duplicate_status
                for field in fields
            ),
            "field_count": len(fields),
        },
    ]


def _preflight_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision", {})
    ranked = report.get("ranked_screens") or []
    top = ranked[0] if ranked and isinstance(ranked[0], dict) else None
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "promising_screen_count": decision.get("promising_screen_count"),
        "top_screen": top,
    }


def _field_payload(field: PayloadFieldPlan) -> dict[str, Any]:
    return {
        "name": field.name,
        "expression": field.expression,
        "source_fields": list(field.source_fields),
        "role": field.role,
        "add_as_new_atom_candidate": field.add_as_new_atom_candidate,
        "duplicate_status": field.duplicate_status,
        "rationale": field.rationale,
        "finite_required": True,
        "nonnegative_required": True,
        "fixed_current_tick": True,
        "affine_score_compatible": True,
    }


def _accept_criteria() -> list[str]:
    return [
        "payload is default-off and absent unless explicitly enabled",
        "payload reports selection_effect=false and future_outcome_leakage=false",
        "payload records route_progress_deficit_vs_top1_m and dp_prior_jerk_excess_cost as diagnostic sources only",
        "payload records comfort_progress_interaction_cost as a new candidate coefficient but does not append it to the deployed CAMP atom vector",
        "finite and nonnegative checks pass for every candidate coefficient",
        "unit tests prove closed-loop outcomes are not read by the payload builder",
        "no replay, schema promotion, CAMP retraining, or online selector change is performed by the implementation gate",
    ]


def _reject_criteria() -> list[str]:
    return [
        "source preflight is missing, rejected, or no longer blocks training/promotion",
        "any proposed new atom candidate is an exact existing v10 schema field",
        "the implementation appends fields to atoms or selection scores",
        "the payload reads candidate_closed_loop_outcomes or any future outcome label",
        "finite/nonnegative checks fail or candidate counts mismatch",
    ]


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Non-Turn-Logit Interaction Payload Design Plan",
        "",
        "This is a plan-only gate. It does not run replay, train CAMP, promote "
        "a schema, or change the online selector.",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- payload implementation authorized: `{decision['payload_implementation_authorized']}`",
        f"- schema promotion authorized: `{decision['schema_promotion_authorized']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Overlap Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["overlap_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Design Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["design_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Payload Fields", "", "```json"])
    lines.append(json.dumps(report["selected_payload_fields"], indent=2, sort_keys=True))
    lines.extend(["```", "", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
