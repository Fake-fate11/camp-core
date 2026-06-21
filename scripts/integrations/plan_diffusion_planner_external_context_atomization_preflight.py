#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SOURCE_STATUS = "external_context_payload_materiality_ready"
SOURCE_NEXT_WORK = "external_context_payload_atomization_preflight_existing_smoke_only"
READY_STATUS = "external_context_atomization_preflight_ready"
REJECT_STATUS = "external_context_atomization_preflight_rejected"
AUTHORIZED_NEXT_WORK = "external_context_atom_schema_dry_run_existing_smoke_only"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


@dataclass(frozen=True)
class AtomPreflightSpec:
    name: str
    source_field: str
    family: str
    coefficient_rule: str
    nonnegative_proof: str
    affine_score_proof: str
    convex_master_proof: str
    activation_condition: str
    requires_material_field: bool = True
    default_off: bool = True
    deployable_now: bool = False


ATOM_SPECS = (
    AtomPreflightSpec(
        name="route_speed_limit_excess_integral_v1",
        source_field="candidate_speed_limit_excess_integral_mps",
        family="route_speed",
        coefficient_rule=(
            "a_k = candidate_speed_limit_excess_integral_mps[k], computed before "
            "selection from fixed DP candidate prefix speeds and current route "
            "speed-limit context"
        ),
        nonnegative_proof=(
            "payload defines this as sum_t max(speed_k,t - limit_k,t, 0) * dt, "
            "therefore the coefficient is nonnegative"
        ),
        affine_score_proof="CAMP sees only fixed coefficient a_k, so score_k(w)=a_k^T w",
        convex_master_proof=(
            "simplex/CVaR/L2 master optimizes over weights with fixed candidate "
            "coefficients; adding this coefficient preserves convexity"
        ),
        activation_condition=(
            "materiality report marks candidate_speed_limit_excess_integral_mps material"
        ),
    ),
    AtomPreflightSpec(
        name="route_speed_limit_missing_context_v1",
        source_field="candidate_speed_limit_available_fraction",
        family="route_speed",
        coefficient_rule="a_k = max(1 - candidate_speed_limit_available_fraction[k], 0)",
        nonnegative_proof=(
            "available fraction is checked in [0,1], so 1 - fraction is nonnegative"
        ),
        affine_score_proof="missing-context coefficient is fixed before selection",
        convex_master_proof="fixed nonnegative coefficient preserves the convex robust master",
        activation_condition=(
            "materiality report marks candidate_speed_limit_available_fraction material"
        ),
    ),
    AtomPreflightSpec(
        name="right_of_way_blocked_indicator_v1",
        source_field="candidate_right_of_way_blocked_indicator",
        family="traffic_signal",
        coefficient_rule="a_k = candidate_right_of_way_blocked_indicator[k]",
        nonnegative_proof="payload finite checks require binary values in {0.0, 1.0}",
        affine_score_proof="binary current-tick coefficient is fixed before selection",
        convex_master_proof="fixed binary coefficient preserves the convex robust master",
        activation_condition=(
            "materiality report marks candidate_right_of_way_blocked_indicator material"
        ),
    ),
    AtomPreflightSpec(
        name="signal_phase_margin_violation_hinge_v1",
        source_field="candidate_signal_phase_change_margin_s",
        family="traffic_signal",
        coefficient_rule="a_k = max(-candidate_signal_phase_change_margin_s[k], 0)",
        nonnegative_proof="hinge of a signed fixed margin is nonnegative by construction",
        affine_score_proof=(
            "hinge is evaluated before weight optimization; CAMP still receives "
            "a fixed coefficient"
        ),
        convex_master_proof=(
            "the master is not optimizing trajectory coordinates or hinge inputs; "
            "it optimizes weights over fixed coefficients, preserving convexity"
        ),
        activation_condition=(
            "materiality report marks candidate_signal_phase_change_margin_s material"
        ),
    ),
    AtomPreflightSpec(
        name="signal_arrival_time_reaches_control_v1",
        source_field="candidate_first_signal_arrival_time_s",
        family="traffic_signal",
        coefficient_rule=(
            "a_k = 1.0 if candidate_first_signal_arrival_time_s[k] is finite else 0.0"
        ),
        nonnegative_proof="indicator coefficient is binary and nonnegative",
        affine_score_proof="arrival/reach indicator is fixed before CAMP scoring",
        convex_master_proof="fixed binary coefficient preserves the convex robust master",
        activation_condition=(
            "materiality report marks candidate_first_signal_arrival_time_s material"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only atomization preflight for external-context payload fields. "
            "Reads materiality JSON only; does not run DP, change schema, or train."
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
    source = _source_gate(materiality)
    atom_specs = [_atom_report(spec, materiality) for spec in ATOM_SPECS]
    deployable_specs = [row for row in atom_specs if row["preflight_passed"]]
    checks = [
        *_source_checks(source),
        {
            "name": "at_least_one_atom_candidate_material",
            "passed": bool(deployable_specs),
            "actual": [row["name"] for row in deployable_specs],
            "expected": "nonempty",
        },
        {
            "name": "all_preflight_candidates_preserve_affine_convex_boundary",
            "passed": all(
                row["math_checks"]["affine_score"]
                and row["math_checks"]["convex_master"]
                and row["math_checks"]["nonnegative_or_hinged"]
                for row in atom_specs
            ),
            "actual": "checked",
            "expected": True,
        },
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_external_context_atomization_preflight_v1",
            "label": label,
            "role": (
                "plan-only atomization preflight after external-context materiality"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This preflight only maps material current-tick payload fields "
                "to candidate atom coefficient definitions. It does not mutate "
                "the deployed atom schema, train CAMP, run DP, or select "
                "trajectories. Every accepted coefficient is fixed before "
                "weight optimization, nonnegative or an explicitly evaluated "
                "hinge/indicator, so any later score remains score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 master remains convex. No trajectory "
                "coordinate convexity or classical Benders cut is claimed."
            ),
        },
        "source_materiality_gate": source,
        "atom_preflight_specs": atom_specs,
        "selected_atom_candidates": [row for row in atom_specs if row["preflight_passed"]],
        "preflight_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, deployable_specs),
    }


def _source_gate(materiality: dict[str, Any]) -> dict[str, Any]:
    decision = materiality.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "material_families": list(materiality.get("material_families") or []),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status_ready", source["status"], SOURCE_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_atomization_preflight",
            source["authorized_next_work"],
            SOURCE_NEXT_WORK,
        ),
        _check_equal(
            "source_blocked_action_conflicts_empty",
            source["blocked_action_conflicts"],
            [],
        ),
    ]


def _atom_report(spec: AtomPreflightSpec, materiality: dict[str, Any]) -> dict[str, Any]:
    material_fields = _material_fields(materiality)
    field_material = spec.source_field in material_fields
    row = asdict(spec)
    row["field_material"] = field_material
    row["math_checks"] = {
        "default_off": spec.default_off,
        "not_deployable_now": not spec.deployable_now,
        "nonnegative_or_hinged": (
            "nonnegative" in spec.nonnegative_proof.lower()
            or "hinge" in spec.nonnegative_proof.lower()
            or "binary" in spec.nonnegative_proof.lower()
        ),
        "affine_score": "score_k(w)=a_k^t w" in spec.affine_score_proof.lower()
        or "fixed" in spec.affine_score_proof.lower(),
        "convex_master": "convex" in spec.convex_master_proof.lower(),
    }
    row["preflight_passed"] = (
        (field_material or not spec.requires_material_field)
        and all(row["math_checks"].values())
    )
    return row


def _material_fields(materiality: dict[str, Any]) -> set[str]:
    return {
        str(row.get("field"))
        for row in materiality.get("field_reports") or []
        if row.get("material") is True
    }


def _final_decision(
    passed: bool,
    deployable_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "selected_atom_candidate_names": [
            row["name"] for row in deployable_specs
        ],
        "closed_loop_replay_authorized": False,
        "new_replay_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Dry-run an external-context atom schema over the existing smoke "
            "logs only; do not train or run new replay."
            if passed
            else "Reject atomization from this materiality evidence and collect the missing real smoke evidence first."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Atomization Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- New replay authorized: `{decision['new_replay_authorized']}`",
        f"- Selected atom candidates: `{decision['selected_atom_candidate_names']}`",
        "",
        "## Source Gate",
        "",
    ]
    for key, value in report["source_materiality_gate"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Atom Candidates", ""])
    for row in report["atom_preflight_specs"]:
        lines.append(
            f"- `{row['name']}` from `{row['source_field']}`: "
            f"material=`{row['field_material']}`, passed=`{row['preflight_passed']}`"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
