#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCORE_INVENTORY_REQUIRED_STATUS = "no_leak_score_family_inventory_requires_new_design"
PAYLOAD_COVERAGE_READY_STATUS = (
    "observable_state_payload_coverage_ready_for_offline_separability_design"
)

REQUIRED_CLOSED_SCORE_FAMILIES = frozenset(
    {
        "non_turn_interaction_family",
        "observable_interaction_family",
        "progress_lane_hard_context",
        "relaxed_strict_atom_family",
        "revised_context_atom_family",
    }
)

FIELD_FAMILIES = {
    "candidate_route_segment_index": "candidate_lane_topology",
    "candidate_route_projection_s_m": "candidate_lane_topology",
    "candidate_route_lateral_error_m": "candidate_lane_topology",
    "candidate_red_stopline_distance_m": "candidate_traffic_light_path_relation",
    "candidate_red_heading_alignment": "candidate_traffic_light_path_relation",
    "candidate_route_heading_change_rad": "route_curvature_turn_context",
    "candidate_min_obstacle_clearance_lower_bound_m": "neighbor_interaction_clearance",
    "candidate_obstacle_slot_count": "neighbor_interaction_clearance",
}

SCORE_FAMILY_FIELD_COVERAGE = {
    "observable_interaction_family": frozenset(FIELD_FAMILIES),
    "progress_lane_hard_context": frozenset(
        {
            "candidate_route_projection_s_m",
            "candidate_route_lateral_error_m",
            "candidate_route_heading_change_rad",
        }
    ),
    "revised_context_atom_family": frozenset(
        {
            "candidate_route_projection_s_m",
            "candidate_route_lateral_error_m",
            "candidate_route_heading_change_rad",
        }
    ),
    "relaxed_strict_atom_family": frozenset(
        {
            "candidate_route_projection_s_m",
            "candidate_route_lateral_error_m",
            "candidate_route_heading_change_rad",
        }
    ),
}

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only post-closure state remainder gate for CAMP-on-DP. It "
            "checks whether already logged current-tick observable-state fields "
            "still contain unclosed material descriptor support after the "
            "no-leak score-family inventory closed the prior routes."
        )
    )
    parser.add_argument("--score_family_inventory_json", type=Path, required=True)
    parser.add_argument("--observable_payload_coverage_json", type=Path, required=True)
    parser.add_argument("--observable_state_inventory_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        score_inventory=_load_json(args.score_family_inventory_json),
        payload_coverage=_load_json(args.observable_payload_coverage_json),
        state_inventory=_load_json(args.observable_state_inventory_json),
        label=args.label,
        paths={
            "score_family_inventory_json": str(args.score_family_inventory_json),
            "observable_payload_coverage_json": str(args.observable_payload_coverage_json),
            "observable_state_inventory_json": str(args.observable_state_inventory_json),
        },
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
    score_inventory: dict[str, Any],
    payload_coverage: dict[str, Any],
    state_inventory: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    score_source = _source_score_inventory(score_inventory)
    coverage_source = _source_payload_coverage(payload_coverage)
    state_source = _source_state_inventory(state_inventory)
    material_fields = _material_candidate_fields(payload_coverage)
    closed_families = _closed_score_families(score_inventory)
    missing_closed_families = sorted(REQUIRED_CLOSED_SCORE_FAMILIES - set(closed_families))
    consumed_fields = _consumed_fields(closed_families)
    field_rows = _field_rows(material_fields, consumed_fields)
    unconsumed_fields = [
        row["field"] for row in field_rows if row["closure_status"] == "unconsumed"
    ]
    final = _decision(
        score_source=score_source,
        coverage_source=coverage_source,
        state_source=state_source,
        missing_closed_families=missing_closed_families,
        unconsumed_fields=unconsumed_fields,
    )
    return {
        "analysis": {
            "name": "dp_camp_post_closure_state_remainder_v1",
            "label": label,
            "role": (
                "read-only post-closure gate that decides whether already "
                "logged current-tick observable-state descriptors still justify "
                "a new no-leak score-family design"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "This gate reads only prior audit artifacts. It does not create "
                "atoms, train weights, run replay, use outcomes as runtime "
                "features, or construct a Benders master/subproblem. Any later "
                "descriptor must be a current-tick finite-candidate coefficient "
                "a_k so score_k(w)=a_k^T w remains affine and the "
                "simplex/CVaR/L2 robust master remains convex."
            ),
        },
        "source_gates": {
            "score_family_inventory": score_source,
            "observable_payload_coverage": coverage_source,
            "observable_state_inventory": state_source,
        },
        "closed_score_families": closed_families,
        "required_closed_score_families": sorted(REQUIRED_CLOSED_SCORE_FAMILIES),
        "missing_closed_score_families": missing_closed_families,
        "material_candidate_fields": material_fields,
        "consumed_fields": sorted(consumed_fields),
        "field_remainder": field_rows,
        "unconsumed_material_candidate_fields": unconsumed_fields,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_score_inventory(report: dict[str, Any]) -> dict[str, Any]:
    status = _decision_status(report)
    return {
        "status": status,
        "passed": status == SCORE_INVENTORY_REQUIRED_STATUS,
        "required_status": SCORE_INVENTORY_REQUIRED_STATUS,
    }


def _source_payload_coverage(report: dict[str, Any]) -> dict[str, Any]:
    status = _decision_status(report)
    decision = report.get("final_decision") or {}
    return {
        "status": status,
        "passed": status == PAYLOAD_COVERAGE_READY_STATUS,
        "required_status": PAYLOAD_COVERAGE_READY_STATUS,
        "material_candidate_fields": list(decision.get("material_candidate_fields") or []),
        "records_total": decision.get("records_total"),
        "payload_records": decision.get("payload_records"),
    }


def _source_state_inventory(report: dict[str, Any]) -> dict[str, Any]:
    status = _decision_status(report)
    decision = report.get("final_decision") or {}
    return {
        "status": status,
        "passed": bool(status),
        "primary_bottleneck": decision.get("primary_bottleneck"),
        "available_new_candidate_state_families": list(
            decision.get("available_new_candidate_state_families") or []
        ),
        "available_existing_proxy_families": list(
            decision.get("available_existing_proxy_families") or []
        ),
    }


def _material_candidate_fields(report: dict[str, Any]) -> list[str]:
    decision = report.get("final_decision") or {}
    fields = decision.get("material_candidate_fields")
    if isinstance(fields, list):
        return [str(field) for field in fields]
    fields = report.get("material_candidate_fields")
    if isinstance(fields, list):
        return [str(field) for field in fields]
    return []


def _closed_score_families(report: dict[str, Any]) -> list[str]:
    families = report.get("score_families")
    closed: list[str] = []
    if isinstance(families, list):
        for row in families:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "")
            status = str(row.get("status") or "")
            if name and status == "rejected_or_limited":
                closed.append(name)
    return sorted(set(closed))


def _consumed_fields(closed_families: list[str]) -> set[str]:
    consumed: set[str] = set()
    for family in closed_families:
        consumed.update(SCORE_FAMILY_FIELD_COVERAGE.get(family, ()))
    return consumed


def _field_rows(
    material_fields: list[str],
    consumed_fields: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in sorted(set(material_fields)):
        family = FIELD_FAMILIES.get(field, "unmapped_current_tick_candidate_state")
        consumed = field in consumed_fields
        rows.append(
            {
                "field": field,
                "field_family": family,
                "closure_status": "consumed_by_closed_family" if consumed else "unconsumed",
                "candidate_level": True,
                "current_tick": True,
                "future_outcome_leakage": False,
            }
        )
    return rows


def _decision(
    *,
    score_source: dict[str, Any],
    coverage_source: dict[str, Any],
    state_source: dict[str, Any],
    missing_closed_families: list[str],
    unconsumed_fields: list[str],
) -> dict[str, Any]:
    if not score_source["passed"]:
        status = "post_closure_state_remainder_score_inventory_not_ready"
        primary_gap = "score_family_inventory_source_not_closed"
        authorized_next_work = "fix_score_family_inventory_before_state_remainder"
    elif missing_closed_families:
        status = "post_closure_state_remainder_score_inventory_stale"
        primary_gap = "score_family_inventory_missing_required_closed_families"
        authorized_next_work = "refresh_score_family_inventory_before_state_remainder"
    elif not coverage_source["passed"]:
        status = "post_closure_state_remainder_payload_coverage_not_ready"
        primary_gap = "observable_payload_coverage_not_material"
        authorized_next_work = "restore_observable_payload_coverage_before_state_remainder"
    elif not state_source["passed"]:
        status = "post_closure_state_remainder_state_inventory_missing"
        primary_gap = "observable_state_inventory_source_missing"
        authorized_next_work = "provide_observable_state_inventory_before_state_remainder"
    elif unconsumed_fields:
        status = "post_closure_state_remainder_has_untried_logged_fields"
        primary_gap = "unconsumed_material_current_tick_fields_present"
        authorized_next_work = "predeclare_new_descriptor_family_from_unconsumed_logged_fields_design_only"
    else:
        status = "post_closure_state_remainder_requires_source_visibility_inventory"
        primary_gap = "all_material_logged_fields_consumed_by_rejected_score_families"
        authorized_next_work = "read_only_current_tick_tensor_visibility_inventory_only"
    return {
        "status": status,
        "passed": status
        == "post_closure_state_remainder_requires_source_visibility_inventory",
        "primary_gap": primary_gap,
        "authorized_next_work": authorized_next_work,
        "missing_closed_score_families": missing_closed_families,
        "unconsumed_material_candidate_fields": unconsumed_fields,
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": _next_step(status),
    }


def _next_step(status: str) -> str:
    if status == "post_closure_state_remainder_score_inventory_stale":
        return (
            "Regenerate the score-family inventory from the latest accepted "
            "rejection evidence before using this post-closure remainder gate."
        )
    if status == "post_closure_state_remainder_has_untried_logged_fields":
        return (
            "Write a design-only descriptor preflight using only the listed "
            "unconsumed current-tick fields before any replay or training."
        )
    if status == "post_closure_state_remainder_requires_source_visibility_inventory":
        return (
            "Do not tune the already logged observable fields. Run only a "
            "read-only source/tensor visibility inventory to identify genuinely "
            "new current-tick finite-candidate inputs before another descriptor "
            "family is proposed."
        )
    return "Repair the named source gate before using this post-closure remainder."


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP-CAMP Post-Closure State Remainder",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Gates",
        "",
        "| Gate | Status | Passed |",
        "| --- | --- | ---: |",
    ]
    for name, source in report["source_gates"].items():
        lines.append(
            f"| `{name}` | `{source.get('status')}` | `{source.get('passed')}` |"
        )
    lines.extend(
        [
            "",
            "## Required Closed Score Families",
            "",
            "| Family | Present As Closed |",
            "| --- | ---: |",
        ]
    )
    closed = set(report["closed_score_families"])
    for family in report["required_closed_score_families"]:
        lines.append(f"| `{family}` | `{family in closed}` |")
    lines.extend(
        [
            "",
            "## Field Remainder",
            "",
            "| Field | Family | Closure |",
            "| --- | --- | --- |",
        ]
    )
    for row in report["field_remainder"]:
        lines.append(
            f"| `{row['field']}` | `{row['field_family']}` | "
            f"`{row['closure_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate is not replay, not training, not a selector, and not a "
            "classical Benders decomposition.",
            "",
        ]
    )
    return "\n".join(lines)


def _decision_status(report: dict[str, Any]) -> str:
    decision = report.get("final_decision")
    if isinstance(decision, dict) and decision.get("status") is not None:
        return str(decision["status"])
    if report.get("status") is not None:
        return str(report["status"])
    return ""


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
