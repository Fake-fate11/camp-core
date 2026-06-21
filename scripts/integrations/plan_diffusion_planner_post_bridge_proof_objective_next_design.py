#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "current_observable_separability_bridge_duplicate_rejected"
SOURCE_NEXT_WORK = "proof_objective_or_new_descriptor_family_design_only"

READY_STATUS = "post_bridge_proof_objective_next_design_plan_ready"
BLOCKED_STATUS = "post_bridge_proof_objective_next_design_plan_blocked"
AUTHORIZED_NEXT_WORK = (
    "predeclare_targeted_safety_intervention_proof_objective_only"
)

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only next-design gate after the current observable "
            "separability bridge closes the missing candidate-state descriptor "
            "route."
        )
    )
    parser.add_argument("--bridge_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        bridge_report=_load_json(args.bridge_json),
        label=args.label,
        paths={"bridge_json": str(args.bridge_json)},
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
    bridge_report: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(bridge_report)
    checks = _plan_checks(source)
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_post_bridge_proof_objective_next_design_v1",
            "label": label,
            "role": (
                "design-only gate after the missing candidate-state observable "
                "route is closed as a duplicate of the rejected matched "
                "observable descriptor family"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. This plan "
                "does not add atoms, train CAMP, run replay, modify DP, or "
                "claim a performance win. It only authorizes a proof-objective "
                "predeclaration after the current descriptor route is closed. "
                "Any future runtime atom must still be a fixed current-tick "
                "finite-candidate coefficient a_k, nonnegative or represented "
                "by nonnegative signed parts, so score_k(w)=a_k^T w remains "
                "affine and the simplex/CVaR/L2 master remains convex. This "
                "is not a classical Benders decomposition."
            ),
        },
        "source_bridge_gate": source,
        "plan_checks": checks,
        "closed_routes": _closed_routes(),
        "proof_objective_design_contract": _proof_objective_design_contract(),
        "candidate_next_objectives": _candidate_next_objectives(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    equivalence = _dict(report.get("equivalence"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and bool(final.get("closure_gate_passed"))
            and bool(equivalence.get("duplicate_route_evidence"))
            and not bool(equivalence.get("materially_new_route"))
            and not conflicts
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "primary_gap": final.get("primary_gap"),
        "closure_gate_passed": bool(final.get("closure_gate_passed")),
        "duplicate_route_evidence": bool(equivalence.get("duplicate_route_evidence")),
        "materially_new_route": bool(equivalence.get("materially_new_route")),
        "current_records": equivalence.get("current_records"),
        "current_candidate_rows": equivalence.get("current_candidate_rows"),
        "uncovered_current_material_fields": list(
            equivalence.get("uncovered_current_material_fields") or []
        ),
        "blocked_action_conflicts": conflicts,
    }


def _plan_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "bridge_duplicate_rejected",
            "passed": source["status"] == SOURCE_STATUS,
            "actual": source["status"],
            "expected": SOURCE_STATUS,
        },
        {
            "name": "bridge_authorizes_proof_or_new_descriptor_design_only",
            "passed": source["authorized_next_work"] == SOURCE_NEXT_WORK,
            "actual": source["authorized_next_work"],
            "expected": SOURCE_NEXT_WORK,
        },
        {
            "name": "bridge_has_closure_evidence",
            "passed": source["closure_gate_passed"]
            and source["duplicate_route_evidence"]
            and not source["materially_new_route"],
            "closure_gate_passed": source["closure_gate_passed"],
            "duplicate_route_evidence": source["duplicate_route_evidence"],
            "materially_new_route": source["materially_new_route"],
        },
        {
            "name": "no_uncovered_material_fields",
            "passed": not source["uncovered_current_material_fields"],
            "uncovered_current_material_fields": source[
                "uncovered_current_material_fields"
            ],
        },
        {
            "name": "no_blocked_action_conflicts",
            "passed": not source["blocked_action_conflicts"],
            "conflicts": source["blocked_action_conflicts"],
        },
    ]


def _closed_routes() -> list[dict[str, str]]:
    return [
        {
            "name": "current_observable_descriptor_separability_rerun",
            "reason": (
                "The bridge found identical 48-record/384-candidate scope and "
                "no current material fields outside the old rejected observable "
                "descriptor family."
            ),
        },
        {
            "name": "missing_candidate_state_logging_expansion_without_new_fields",
            "reason": (
                "The current missing-state payload is useful audit evidence but "
                "does not create a materially new separability family."
            ),
        },
        {
            "name": "camp_retraining_from_closed_descriptor_family",
            "reason": (
                "Training on a descriptor family already rejected by matched "
                "outcome and constrained affine evidence would not be a legal "
                "next gate."
            ),
        },
        {
            "name": "direct_replay_or_full36",
            "reason": "No deployable no-leak selector hypothesis exists after closure.",
        },
    ]


def _proof_objective_design_contract() -> dict[str, Any]:
    return {
        "must_predeclare": [
            "primary SafetyCost or successor score",
            "scenario buckets and normal-scene nondegradation gates",
            "DP Top-1, current logged CAMP, and hard-guarded oracle comparators",
            "paired mean and CI claim rules",
            "CVaR or tail-risk reporting",
            "latency, fallback, comfort, and hard-safety promotion gates",
        ],
        "may_use_offline_labels_for": [
            "candidate-branch opportunity analysis",
            "training labels after a separate authorization",
            "posterior evaluation of paired selector choices",
        ],
        "must_not_use_offline_labels_for": [
            "runtime selector inputs",
            "post hoc scenario filters",
            "renaming a failed descriptor family as new support",
        ],
    }


def _candidate_next_objectives() -> list[dict[str, Any]]:
    return [
        {
            "name": "targeted_safety_intervention_proof_objective",
            "priority": 1,
            "recommended_first": True,
            "status": "authorized_predeclaration_only",
            "claim_shape": (
                "improve SafetyCost in safety-critical buckets with normal "
                "bucket nondegradation and no hard-gate regression"
            ),
            "why_now": (
                "The missing-state descriptor route is closed; the next useful "
                "question is whether the proof objective should target "
                "safety-critical interventions rather than a single global "
                "mean claim."
            ),
        },
        {
            "name": "new_current_tick_descriptor_family",
            "priority": 2,
            "recommended_first": False,
            "status": "blocked_until_named_source_field_exists",
            "claim_shape": (
                "only admissible if a genuinely new current-tick candidate "
                "source is predeclared and is not covered by the closed family"
            ),
            "why_not_first": (
                "The bridge found no uncovered material fields in the current "
                "missing-state payload."
            ),
        },
        {
            "name": "global_safetycost_v1_only",
            "priority": 3,
            "recommended_first": False,
            "status": "retain_as_reporting_baseline_not_next_design",
            "claim_shape": (
                "single global SafetyCost improvement against DP Top-1 remains "
                "too coarse for the observed safety-critical bucket failures"
            ),
            "why_not_first": (
                "Prior evidence showed global variants and current atom families "
                "do not close the selector-oracle gap."
            ),
        },
    ]


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_first_action": (
            "predeclare_targeted_safety_intervention_proof_objective"
            if passed
            else "repair_or_rerun_current_observable_bridge_closure"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_bridge_gate"]
    lines = [
        "# Post-Bridge Proof Objective Next Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Recommended first action: `{decision['recommended_first_action']}`",
        "",
        "## Source Bridge",
        "",
        f"- Status: `{source['status']}`",
        f"- Duplicate route evidence: `{source['duplicate_route_evidence']}`",
        f"- Materially new route: `{source['materially_new_route']}`",
        f"- Current records: `{source['current_records']}`",
        f"- Current candidate rows: `{source['current_candidate_rows']}`",
        "",
        "## Plan Checks",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for check in report["plan_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(
        [
            "",
            "## Candidate Next Objectives",
            "",
        ]
    )
    for objective in report["candidate_next_objectives"]:
        lines.extend(
            [
                f"### {objective['name']}",
                "",
                f"- Priority: `{objective['priority']}`",
                f"- Recommended first: `{objective['recommended_first']}`",
                f"- Status: `{objective['status']}`",
                f"- Claim shape: {objective['claim_shape']}",
                f"- Reason: {objective['why_now'] if 'why_now' in objective else objective['why_not_first']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate does not run DP, train CAMP, promote an online selector, "
            "authorize Full36, or touch formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
