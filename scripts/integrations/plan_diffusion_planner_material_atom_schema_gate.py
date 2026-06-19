#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BOUNDARY_READY = "next_design_boundary_requires_new_offline_design"
READY_STATUS = "material_atom_schema_gate_ready"
BLOCKED_STATUS = "material_atom_schema_gate_blocked"
CONFLICT_STATUS = "material_atom_schema_gate_source_conflict"

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only gate for a materially new no-leak CAMP atom-schema "
            "direction after DP-CAMP selector/generator route families were "
            "rejected."
        )
    )
    parser.add_argument("--next_design_boundary_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        next_design_boundary=_load_json(args.next_design_boundary_json),
        label=args.label,
        paths={"next_design_boundary_json": str(args.next_design_boundary_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def build_report(
    *,
    next_design_boundary: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    boundary = _boundary_summary(next_design_boundary)
    conflicts = _authorization_conflicts(next_design_boundary)
    preconditions = _preconditions(boundary, conflicts)
    decision = _decision(conflicts, preconditions)
    return {
        "analysis": {
            "name": "dp_camp_material_atom_schema_gate_v1",
            "label": label,
            "role": (
                "read-only mathematical and engineering gate for a new CAMP "
                "atom schema; it does not train weights or change runtime "
                "selection"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "Candidate-generation and DP internals remain frozen. The "
                "proposed atoms are fixed current-tick finite-candidate scalars "
                "computed after DP candidate generation and replay-equivalent "
                "postprocessing. For each candidate k, score_k(w)=a_k^T w stays "
                "affine in w. Training with simplex constraints, CVaR, and L2 "
                "regularization remains convex because losses are pointwise "
                "maxima/weighted sums of affine functions over fixed atoms. No "
                "trajectory-coordinate convexity or classical Benders "
                "decomposition is claimed."
            ),
        },
        "source_summary": boundary,
        "preconditions": preconditions,
        "proposed_schema": _proposed_schema(),
        "offline_availability_gate": _offline_availability_gate(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "source_authorization_conflicts": conflicts,
        "final_decision": decision,
    }


def _boundary_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    families = {
        row.get("name"): row.get("status")
        for row in report.get("route_families", [])
        if isinstance(row, dict)
    }
    return {
        "status": decision.get("status"),
        "missing_or_inconclusive_families": decision.get(
            "missing_or_inconclusive_families",
            [],
        ),
        "support_present_families": decision.get("support_present_families", []),
        "source_authorization_conflicts": decision.get(
            "source_authorization_conflicts",
            [],
        ),
        "route_families": families,
        "authorized_next_work": _deep_get(
            report,
            ("next_design_boundary", "authorized_next_work"),
        ),
    }


def _preconditions(
    boundary: dict[str, Any],
    conflicts: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "name": "boundary_requires_new_offline_design",
            "passed": boundary["status"] == BOUNDARY_READY,
            "evidence": boundary["status"],
        },
        {
            "name": "no_boundary_authorization_conflicts",
            "passed": not conflicts and not boundary["source_authorization_conflicts"],
            "evidence": {
                "ledger_conflicts": boundary["source_authorization_conflicts"],
                "direct_conflicts": conflicts,
            },
        },
        {
            "name": "no_missing_or_unresolved_route_family",
            "passed": not boundary["missing_or_inconclusive_families"]
            and not boundary["support_present_families"],
            "evidence": {
                "missing": boundary["missing_or_inconclusive_families"],
                "support_present": boundary["support_present_families"],
            },
        },
        {
            "name": "all_rejected_families_are_not_repeated",
            "passed": _rejected_families_present(boundary),
            "evidence": boundary["route_families"],
        },
        {
            "name": "authorized_scope_is_offline_design_gate_only",
            "passed": boundary["authorized_next_work"]
            == "new_predeclared_offline_no_leak_design_gate_only",
            "evidence": boundary["authorized_next_work"],
        },
    ]


def _rejected_families_present(boundary: dict[str, Any]) -> bool:
    required = {
        "dp_candidate_native_selector",
        "mode_seeking_candidate_generation",
        "source_donor_or_graft_transform",
        "lane_projected_stop_target",
    }
    families = boundary["route_families"]
    return all(families.get(name) == "rejected_or_blocked" for name in required)


def _proposed_schema() -> dict[str, Any]:
    return {
        "schema_name": "material_support_certificate_atoms_v1",
        "purpose": (
            "capture why a DP candidate is safe enough to select without "
            "repeating threshold-only selectors or geometry transforms"
        ),
        "atom_families": [
            {
                "name": "hard_feasibility_deficit",
                "definition": (
                    "nonnegative DP-reward hard-feasibility deficit or reason "
                    "indicator after replay-equivalent postprocess_reference"
                ),
                "current_tick_only": True,
                "nonnegative": True,
                "rationale": (
                    "latest-safe and donor routes failed because lower-red "
                    "candidates were hard-infeasible; the atom exposes that "
                    "failure to the convex master instead of hiding it in an "
                    "external threshold"
                ),
            },
            {
                "name": "support_preservation_deficit",
                "definition": (
                    "nonnegative loss of route progress, target speed, first-step "
                    "reach, or short-horizon rollout distance versus the selected "
                    "or Top-1 baseline"
                ),
                "current_tick_only": True,
                "nonnegative": True,
                "rationale": (
                    "dense lane-change and red-light screens repeatedly exposed "
                    "safety/progress tradeoffs that were not free Pareto gains"
                ),
            },
            {
                "name": "comfort_envelope_excess",
                "definition": (
                    "nonnegative max of command jerk, rollout jerk, lateral "
                    "acceleration, and absolute lateral guard excess"
                ),
                "current_tick_only": True,
                "nonnegative": True,
                "rationale": (
                    "candidate-support quality audits found safety support that "
                    "regressed comfort; this atom makes that tradeoff explicit"
                ),
            },
            {
                "name": "top1_shape_deviation",
                "definition": (
                    "nonnegative deviation from DP Top-1 in endpoint, prefix, "
                    "heading, and DP-prior comfort coordinates"
                ),
                "current_tick_only": True,
                "nonnegative": True,
                "rationale": (
                    "industrial fail-closed behavior needs the convex selector "
                    "to know when it is moving far from the high-quality DP prior"
                ),
            },
            {
                "name": "traffic_rule_exposure",
                "definition": (
                    "nonnegative near-horizon/full-horizon red-light and stopping "
                    "margin exposure, computed without closed-loop future labels"
                ),
                "current_tick_only": True,
                "nonnegative": True,
                "rationale": (
                    "red-light improvements remain the main useful opportunity, "
                    "but prior stop-target transforms damaged hard feasibility"
                ),
            },
        ],
        "not_a_repeated_route_family": [
            "not a selector threshold grid; atoms feed the existing convex CAMP master",
            "not a lane-projected stop target or donor/graft transform; no new trajectory is created",
            "not mode-seeking candidate generation; DP candidates and weights remain fixed",
            "not CAMP retraining yet; this only authorizes an availability and convexity audit",
        ],
    }


def _offline_availability_gate() -> dict[str, Any]:
    return {
        "authorized_next_artifact": "material_atom_schema_availability_audit",
        "implementation_allowed_now": False,
        "audit_requirements_before_training": [
            "100% finite/nonnegative coverage for every proposed atom on nonformal logs",
            "explicit scenario bucket coverage for normal, traffic_light, red_light_turn, sharp_turn, dense_scene, and lane_change_or_merge",
            "no formal seeds 11/12/13",
            "no DP source or weight changes",
            "no closed-loop future outcome labels in runtime atom computation",
            "latency projection for each atom family with p95 margin before replay",
            "paired comparison against current CAMP and DP Top-1 only after atom availability passes",
        ],
        "convexity_checks": [
            "atom vectors are fixed before optimizing w",
            "all atom entries are nonnegative or split into nonnegative signed parts",
            "score remains affine a_k^T w",
            "simplex/CVaR/L2 master is solved over w only",
            "no DP-side dual/cut claim is made",
        ],
        "blocked_until_audit_passes": list(BLOCKED_ACTIONS),
    }


def _decision(conflicts: list[str], preconditions: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [item["name"] for item in preconditions if not item["passed"]]
    if conflicts:
        status = CONFLICT_STATUS
        next_step = "Resolve source authorization conflicts before designing new atoms."
    elif failed:
        status = BLOCKED_STATUS
        next_step = "Do not proceed to atom-schema audit until failed preconditions pass."
    else:
        status = READY_STATUS
        next_step = (
            "Implement only the offline material-atom availability/convexity "
            "audit; do not train CAMP or run replay."
        )
    return {
        "status": status,
        "failed_preconditions": failed,
        "source_authorization_conflicts": conflicts,
        "authorized_implementation": (
            "offline_material_atom_schema_availability_audit"
            if status == READY_STATUS
            else None
        ),
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    schema = report["proposed_schema"]
    lines = [
        "# Material CAMP Atom-Schema Gate",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Authorized implementation: `{decision['authorized_implementation']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Preconditions",
        "",
        "| Precondition | Passed | Evidence |",
        "| --- | --- | --- |",
    ]
    for item in report["preconditions"]:
        lines.append(
            f"| `{item['name']}` | `{item['passed']}` | `{_short_json(item['evidence'])}` |"
        )
    lines.extend(
        [
            "",
            "## Proposed Atom Families",
            "",
            "| Atom | Nonnegative | Runtime Source | Rationale |",
            "| --- | --- | --- | --- |",
        ]
    )
    for atom in schema["atom_families"]:
        lines.append(
            f"| `{atom['name']}` | `{atom['nonnegative']}` | "
            f"{atom['definition']} | {atom['rationale']} |"
        )
    lines.extend(
        [
            "",
            "## Offline Gate",
            "",
            f"- Authorized next artifact: `{report['offline_availability_gate']['authorized_next_artifact']}`",
            f"- Implementation allowed now: `{report['offline_availability_gate']['implementation_allowed_now']}`",
            "- CAMP training remains blocked until the availability and convexity audit passes.",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _authorization_conflicts(report: dict[str, Any]) -> list[str]:
    conflicts = list(report.get("source_authorization_conflicts") or [])
    decision = report.get("final_decision") or {}
    for key in BLOCKED_ACTIONS:
        if decision.get(key):
            conflicts.append(f"next_design_boundary:{key}")
    return conflicts


def _deep_get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _short_json(value: Any) -> str:
    text = json.dumps(value, sort_keys=True)
    if len(text) > 120:
        text = text[:117] + "..."
    return text.replace("|", "\\|")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
