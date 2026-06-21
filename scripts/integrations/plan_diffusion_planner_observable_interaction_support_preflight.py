#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "observable_interaction_geometry_bottleneck_diagnosed"
SOURCE_NEXT_WORK = "reject_observable_interaction_route_or_predeclare_narrow_support_experiment"
READY_STATUS = "observable_interaction_support_preflight_current_route_rejected"
REJECT_STATUS = "observable_interaction_support_preflight_source_not_ready"
AUTHORIZED_NEXT_WORK = "predeclare_observable_interaction_route_support_discovery_only"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight after the observable-interaction geometry "
            "audit. It decides whether the current route/support evidence is "
            "strong enough to predeclare a narrow support smoke. It never runs "
            "Diffusion Planner."
        )
    )
    parser.add_argument("--geometry_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(geometry_report=_read_json(args.geometry_json), label=args.label)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(*, geometry_report: dict[str, Any], label: str | None = None) -> dict[str, Any]:
    source = _source_gate(geometry_report)
    route_rejection = _route_rejection(geometry_report)
    discovery_contract = _discovery_contract()
    passed = bool(source["passed"] and route_rejection["reject_current_route"])
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_support_preflight_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "closed_loop_outcome_labels_used": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "This is a design-only preflight. It rejects the current "
                "observable-interaction route/support evidence and predeclares "
                "only a smaller read-only discovery step. It creates no atom, "
                "no selector, no learned weight, no outcome label, and no "
                "Benders cut. Future atomization must use fixed current-tick "
                "finite-candidate coefficients preserving affine score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 convex master."
            ),
        },
        "source_gate": source,
        "route_rejection": route_rejection,
        "route_support_discovery_contract": discovery_contract,
        "blocked_actions": {
            "run_replay_now": True,
            "new_replay": True,
            "offline_separability": True,
            "Full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "CAMP_retraining": True,
            "DP_modification": True,
            "classic_Benders_claim": True,
        },
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "current_observable_interaction_route_rejected": passed,
            "support_smoke_predeclared": False,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
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


def render_markdown(report: dict[str, Any]) -> str:
    final = report["final_decision"]
    reject = report["route_rejection"]
    contract = report["route_support_discovery_contract"]
    lines = [
        "# Observable Interaction Support Preflight",
        "",
        f"- status: `{final['status']}`",
        f"- passed: `{final['passed']}`",
        f"- authorized next work: `{final['authorized_next_work']}`",
        f"- current route rejected: `{final['current_observable_interaction_route_rejected']}`",
        f"- support smoke predeclared: `{final['support_smoke_predeclared']}`",
        "",
        "## Rejection",
        "",
        f"- red reason: `{reject['red_reason']}`",
        f"- clearance reason: `{reject['clearance_reason']}`",
        f"- rationale: {reject['rationale']}",
        "",
        "## Discovery Contract",
        "",
        f"- next artifact: `{contract['next_artifact']}`",
        f"- permitted inputs: `{', '.join(contract['permitted_inputs'])}`",
        f"- forbidden inputs: `{', '.join(contract['forbidden_inputs'])}`",
        "",
        "### Accept Criteria",
        "",
    ]
    lines.extend(f"- {item}" for item in contract["accept_criteria"])
    lines.extend(["", "### Reject Criteria", ""])
    lines.extend(f"- {item}" for item in contract["reject_criteria"])
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") if isinstance(report, dict) else {}
    final = final if isinstance(final, dict) else {}
    return {
        "expected_status": SOURCE_STATUS,
        "actual_status": final.get("status"),
        "expected_authorized_next_work": SOURCE_NEXT_WORK,
        "actual_authorized_next_work": final.get("authorized_next_work"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and final.get("current_observable_interaction_route_rejected") is True
            and final.get("new_replay_authorized") is False
            and final.get("offline_separability_authorized") is False
            and final.get("CAMP_retraining_authorized") is False
        ),
    }


def _route_rejection(report: dict[str, Any]) -> dict[str, Any]:
    bottlenecks = report.get("bottlenecks") if isinstance(report, dict) else {}
    bottlenecks = bottlenecks if isinstance(bottlenecks, dict) else {}
    geometry = report.get("geometry") if isinstance(report, dict) else {}
    geometry = geometry if isinstance(geometry, dict) else {}
    red = geometry.get("red") if isinstance(geometry.get("red"), dict) else {}
    clearance = (
        geometry.get("clearance") if isinstance(geometry.get("clearance"), dict) else {}
    )
    red_reason = str(bottlenecks.get("red_bottleneck") or "")
    clearance_reason = str(bottlenecks.get("clearance_bottleneck") or "")
    reject_current = (
        red_reason == "reduced_red_alignment_nonpositive"
        and clearance_reason == "clearance_budget_never_active"
        and int(red.get("reduced_positive_alignment_candidates") or 0) == 0
        and int(clearance.get("inside_budget_candidates") or 0) == 0
    )
    return {
        "reject_current_route": reject_current,
        "red_reason": red_reason,
        "clearance_reason": clearance_reason,
        "red_reduced_near_budget_candidates": int(
            red.get("reduced_near_budget_candidates") or 0
        ),
        "red_reduced_positive_alignment_candidates": int(
            red.get("reduced_positive_alignment_candidates") or 0
        ),
        "clearance_positive_obstacle_slot_candidates": int(
            clearance.get("positive_obstacle_slot_candidates") or 0
        ),
        "clearance_inside_budget_candidates": int(
            clearance.get("inside_budget_candidates") or 0
        ),
        "rationale": (
            "The current route/support has stopline proximity without positive "
            "reduced red alignment and obstacle slots without near-clearance "
            "deficit. This is insufficient evidence for a support smoke, so "
            "only a read-only discovery step is allowed."
        ),
    }


def _discovery_contract() -> dict[str, Any]:
    return {
        "next_artifact": "observable_interaction_route_support_discovery_plan",
        "permitted_inputs": [
            "existing route pickles",
            "lanelet2 map metadata",
            "existing observable payload logs",
            "documented simulator/NPC spawn configuration",
        ],
        "forbidden_inputs": [
            "closed-loop outcome labels",
            "new Diffusion Planner replay",
            "formal seeds 11/12/13",
            "DP code changes or retraining",
            "online selector changes",
        ],
        "accept_criteria": [
            "predeclare at least one route/support candidate with a geometry reason "
            "for positive reduced red alignment near a red stopline",
            "predeclare at least one route/support candidate with a geometry reason "
            "for obstacle clearance entering the fixed 2m budget",
            "include baseline versus default-off observable logging variants",
            "include selector-equivalence checks and payload materiality checks",
            "bound the nonformal scope before any replay and exclude formal seeds",
            "keep support descriptors current-tick and no-leak",
        ],
        "reject_criteria": [
            "no route/support candidate can be justified without new replay",
            "positive red alignment requires flipping semantic direction without a "
            "documented map/traffic-light convention",
            "near-clearance support requires changing DP, vehicle dynamics, or "
            "formal seeds",
            "the proposed plan cannot preserve selector neutrality",
        ],
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
