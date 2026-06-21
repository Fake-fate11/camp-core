#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


READY_STATUS = "red_route_vector_logging_plan_ready"
REJECT_STATUS = "red_route_vector_logging_plan_rejected"
SOURCE_STATUS = "red_alignment_sign_semantics_underdetermined"
AUTHORIZED_NEXT_WORK = "implement_default_off_red_route_vector_logging_unit_tests_only"


BLOCKED_ACTIONS = (
    "run_replay_now",
    "offline_separability",
    "full36",
    "formal_seeds",
    "online_selector_promotion",
    "camp_retraining",
    "dp_modification",
    "classic_benders_claim",
)


@dataclass(frozen=True)
class RedVectorFieldSpec:
    name: str
    shape: str
    dtype: str
    source: str
    purpose: str
    required_for_sign_proof: bool = True
    default_off: bool = True
    selection_effect: bool = False
    future_outcome_leakage: bool = False
    atom_candidate: bool = False


FIELD_SPECS: tuple[RedVectorFieldSpec, ...] = (
    RedVectorFieldSpec(
        name="red_route_points_ego_xy_dir",
        shape="[R,4]",
        dtype="float32",
        source="red_route_points_from_scene(scene, ego_id)",
        purpose=(
            "records current red route point xy and direction vectors in ego "
            "frame so sign semantics can be recomputed offline"
        ),
    ),
    RedVectorFieldSpec(
        name="candidate_red_selected_route_point_index",
        shape="[K,H_tl]",
        dtype="int32",
        source="_candidate_red_light_relation nearest-red-point selection",
        purpose=(
            "records which red route point each candidate step used for "
            "distance/alignment; -1 when no red point exists"
        ),
    ),
    RedVectorFieldSpec(
        name="candidate_red_heading_vector_xy",
        shape="[K,H_tl,2]",
        dtype="float32",
        source="_candidate_headings(candidates, H_tl)",
        purpose=(
            "records the candidate heading unit vector used in the dot product"
        ),
    ),
    RedVectorFieldSpec(
        name="candidate_red_vector_to_selected_point_xy",
        shape="[K,H_tl,2]",
        dtype="float32",
        source="selected red_route_points_ego_xy_dir[:,:2] - candidate xy",
        purpose=(
            "records the relative vector used to decide whether the red point "
            "is ahead of the candidate"
        ),
    ),
    RedVectorFieldSpec(
        name="candidate_red_alignment_recomputed_current",
        shape="[K,H_tl]",
        dtype="float32",
        source="dot(candidate_red_heading_vector_xy, selected red direction)",
        purpose=(
            "records an exact recompute check for the current sign convention"
        ),
        atom_candidate=False,
    ),
    RedVectorFieldSpec(
        name="candidate_red_alignment_recomputed_reverse",
        shape="[K,H_tl]",
        dtype="float32",
        source="-candidate_red_alignment_recomputed_current",
        purpose=(
            "records the reverse-sign diagnostic needed to explain the "
            "underdetermined support gap"
        ),
        atom_candidate=False,
    ),
)


REQUIRED_REPLAY_TOKENS = (
    "red_route_points_from_scene(scene, ego_id)",
    "def _candidate_red_light_relation",
    "candidate_red_stopline_distance_m",
    "candidate_red_heading_alignment",
    "def _observable_state_logging_payload",
    "OBSERVABLE_STATE_FIELDS",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only plan for default-off red route vector logging after "
            "red alignment sign semantics were found underdetermined."
        )
    )
    parser.add_argument("--red_semantics_json", type=Path, required=True)
    parser.add_argument(
        "--replay_script",
        type=Path,
        default=Path("scripts/integrations/run_diffusion_planner_camp_replay.py"),
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        red_semantics_report=_read_json(args.red_semantics_json),
        replay_script=args.replay_script,
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
    red_semantics_report: dict[str, Any],
    replay_script: Path,
    label: str | None = None,
    field_specs: tuple[RedVectorFieldSpec, ...] = FIELD_SPECS,
) -> dict[str, Any]:
    source_checks = _source_checks(red_semantics_report)
    field_checks = _field_checks(field_specs)
    hook_checks = _hook_checks(replay_script)
    passed = all(
        check["passed"] for check in [*source_checks, *field_checks, *hook_checks]
    )
    return {
        "analysis": {
            "name": "dp_camp_red_route_vector_logging_plan_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "closed_loop_outcome_labels_used": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "This is a design-only gate for default-off current-tick "
                "diagnostic logging. It creates no selector, no atom weight, "
                "no online threshold, and no Benders cut. If a later red "
                "descriptor is atomized, it must be a fixed pre-outcome "
                "nonnegative candidate coefficient a_k so score_k(w)=a_k^T w "
                "remains affine and the simplex/CVaR/L2 master remains convex."
            ),
        },
        "source_checks": source_checks,
        "field_checks": field_checks,
        "hook_checks": hook_checks,
        "field_specs": [asdict(spec) for spec in field_specs],
        "implementation_contract": _implementation_contract(),
        "selector_equivalence_contract": _selector_equivalence_contract(),
        "accept_criteria": _accept_criteria(),
        "reject_criteria": _reject_criteria(),
        "blocked_actions": {name: True for name in BLOCKED_ACTIONS},
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "implementation_authorized": bool(passed),
            "implementation_scope": (
                "default-off red route vector logging fields plus unit tests and "
                "selector-equivalence audit scaffolding only"
                if passed
                else None
            ),
            "new_replay_authorized": False,
            "offline_separability_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "classic_Benders_claim_authorized": False,
        },
    }


def _source_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    final = report.get("final_decision") if isinstance(report, dict) else None
    counts = report.get("counts") if isinstance(report, dict) else None
    geometry = report.get("geometry_fields") if isinstance(report, dict) else None
    final = final if isinstance(final, dict) else {}
    counts = counts if isinstance(counts, dict) else {}
    geometry = geometry if isinstance(geometry, dict) else {}
    return [
        {
            "name": "red_semantics_gate_authorizes_vector_plan",
            "passed": final.get("status") == SOURCE_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work")
            == "predeclare_red_route_point_vector_logging_plan_or_reject_red_descriptor",
            "final_decision": final,
        },
        {
            "name": "source_has_reverse_sign_materiality",
            "passed": int(counts.get("reverse_mean_supported_candidate_count", 0)) > 0
            and int(counts.get("within_budget_candidate_count", 0)) > 0
            and int(counts.get("current_mean_supported_candidate_count", -1)) == 0,
            "counts": {
                "within_budget_candidate_count": counts.get(
                    "within_budget_candidate_count"
                ),
                "current_mean_supported_candidate_count": counts.get(
                    "current_mean_supported_candidate_count"
                ),
                "reverse_mean_supported_candidate_count": counts.get(
                    "reverse_mean_supported_candidate_count"
                ),
            },
        },
        {
            "name": "source_geometry_missing_so_plan_is_needed",
            "passed": int(counts.get("records_with_logged_red_geometry", -1)) == 0
            and not geometry,
            "records_with_logged_red_geometry": counts.get(
                "records_with_logged_red_geometry"
            ),
            "geometry_fields": geometry,
        },
    ]


def _field_checks(field_specs: tuple[RedVectorFieldSpec, ...]) -> list[dict[str, Any]]:
    names = [spec.name for spec in field_specs]
    required = {
        "red_route_points_ego_xy_dir",
        "candidate_red_selected_route_point_index",
        "candidate_red_heading_vector_xy",
        "candidate_red_vector_to_selected_point_xy",
        "candidate_red_alignment_recomputed_current",
        "candidate_red_alignment_recomputed_reverse",
    }
    return [
        {
            "name": "required_fields_present",
            "passed": required.issubset(names),
            "missing": sorted(required.difference(names)),
        },
        {
            "name": "fields_are_default_off_and_selector_neutral",
            "passed": all(
                spec.default_off
                and not spec.selection_effect
                and not spec.future_outcome_leakage
                for spec in field_specs
            ),
        },
        {
            "name": "field_names_unique",
            "passed": len(names) == len(set(names)),
            "field_names": names,
        },
        {
            "name": "no_field_claims_atom_by_default",
            "passed": not any(spec.atom_candidate for spec in field_specs),
        },
    ]


def _hook_checks(replay_script: Path) -> list[dict[str, Any]]:
    path = Path(replay_script)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return [
        {
            "name": "replay_script_exists",
            "passed": path.is_file(),
            "path": str(path),
        },
        {
            "name": "existing_red_relation_hooks_available",
            "passed": all(token in text for token in REQUIRED_REPLAY_TOKENS),
            "missing_tokens": [token for token in REQUIRED_REPLAY_TOKENS if token not in text],
        },
        {
            "name": "existing_observable_logging_is_default_off",
            "passed": '"default_off": True' in text
            and '"selection_effect": False' in text
            and '"future_outcome_leakage": False' in text,
        },
    ]


def _implementation_contract() -> dict[str, Any]:
    return {
        "schema_version": "dp_camp_red_route_vector_logging_v1",
        "cli_flag": "--camp_red_route_vector_logging",
        "default": "off",
        "record_field": "red_route_vector_logging",
        "summary_field": "camp_red_route_vector_logging",
        "latency_field": "latency_ms_red_route_vector_logging",
        "placement": (
            "after red_route_points_from_scene(scene, ego_id) and before "
            "compute_candidate_closed_loop_outcomes(...)"
        ),
        "allowed_inputs": (
            "fixed DP candidates, current ego pose transformed red route points, "
            "candidate heading prefix, and current observable traffic-light state"
        ),
        "forbidden_inputs": (
            "candidate_closed_loop_outcomes, closed-loop labels, future tracker "
            "states, learned outcome labels, or any DP model internals"
        ),
    }


def _selector_equivalence_contract() -> list[str]:
    return [
        "baseline run does not include --camp_red_route_vector_logging",
        "logging-enabled run includes --camp_red_route_vector_logging only",
        "selected index is unchanged between paired logs",
        "feasible mask, atoms, normalized atoms, scores, and weights are unchanged",
        "PerfectTracker command inputs and selected trajectory are unchanged",
        "red_route_vector_logging reports default_off=true, selection_effect=false, future_outcome_leakage=false",
    ]


def _accept_criteria() -> list[str]:
    return [
        "source red semantics artifact is underdetermined specifically because geometry is unlogged",
        "all planned fields are current-tick, default-off, selector-neutral diagnostics",
        "implementation gate adds unit tests and no replay execution",
        "later paired smoke, if separately authorized, proves selector equivalence before using payloads",
        "no formal seeds, Full36, online selector promotion, CAMP retraining, DP modification, or classic Benders claim",
    ]


def _reject_criteria() -> list[str]:
    return [
        "source red semantics artifact is missing, not underdetermined, or does not authorize this plan",
        "reverse-sign materiality is absent, making red vector logging unjustified",
        "planned fields cannot prove sign semantics from current-tick data alone",
        "implementation would change candidate generation, scoring, feasibility, selection, or PerfectTracker execution",
        "any field requires closed-loop outcome labels or future state",
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Red Route Vector Logging Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- implementation authorized: `{decision['implementation_authorized']}`",
        f"- new replay authorized: `{decision['new_replay_authorized']}`",
        "",
        "## Planned Fields",
        "",
        "| Field | Shape | Source | Purpose |",
        "| --- | --- | --- | --- |",
    ]
    for spec in report["field_specs"]:
        lines.append(
            f"| `{spec['name']}` | `{spec['shape']}` | "
            f"`{spec['source']}` | {spec['purpose']} |"
        )
    lines.extend(["", "## Source Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["source_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Field Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["field_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Hook Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["hook_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(
        [
            "",
            "## Implementation Contract",
            "",
            "```json",
            json.dumps(report["implementation_contract"], indent=2, sort_keys=True),
            "```",
            "",
            "## Selector Equivalence Contract",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["selector_equivalence_contract"])
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"]])
    lines.extend(["", "## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.append("")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


if __name__ == "__main__":
    main()
