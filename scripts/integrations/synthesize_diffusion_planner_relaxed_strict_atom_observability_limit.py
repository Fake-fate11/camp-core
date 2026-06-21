#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_relaxed_strict_label_atom_component_overlap import (  # noqa: E402
    NEXT_WORK_LIMITATION as COMPONENT_NEXT_WORK_LIMITATION,
    NEXT_WORK_REDESIGN as COMPONENT_NEXT_WORK_REDESIGN,
    READY_STATUS as COMPONENT_READY_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_relaxed_strict_label_atom_separability import (  # noqa: E402
    BLOCKED_ACTIONS,
    _load_json,
)


READY_STATUS = "relaxed_strict_atom_observability_limit_recorded"
SOURCE_BLOCKED_STATUS = "relaxed_strict_atom_observability_limit_source_not_ready"
SOURCE_REDESIGN_STATUS = "relaxed_strict_atom_observability_limit_not_applicable"

PRIMARY_GAP = "current_relaxed_strict_atom_family_lacks_observable_separation"
NEXT_WORK = (
    "predeclare_new_current_tick_no_leak_descriptor_family_or_return_to_"
    "observable_state_inventory_design_only"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Record the observability limit implied by the rejected relaxed "
            "strict-label atom component-overlap diagnosis. This is a "
            "read-only synthesis gate: it consumes an existing artifact, does "
            "not run DP, does not train CAMP, and does not change selection."
        )
    )
    parser.add_argument("--component_overlap_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = synthesize(
        component_overlap_report=_load_json(args.component_overlap_json),
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


def synthesize(
    *,
    component_overlap_report: dict[str, Any],
    label: str | None = None,
) -> dict[str, Any]:
    source = _source_gate(component_overlap_report)
    evidence = _evidence(component_overlap_report)
    source_next_work = source["authorized_next_work"]
    source_ready = bool(
        source["passed"]
        and source["status"] == COMPONENT_READY_STATUS
        and source_next_work == COMPONENT_NEXT_WORK_LIMITATION
    )
    redesign_ready = bool(
        source["passed"]
        and source["status"] == COMPONENT_READY_STATUS
        and source_next_work == COMPONENT_NEXT_WORK_REDESIGN
    )
    if source_ready:
        status = READY_STATUS
        passed = True
        primary_gap = PRIMARY_GAP
        authorized_next_work = NEXT_WORK
    elif redesign_ready:
        status = SOURCE_REDESIGN_STATUS
        passed = False
        primary_gap = "component_overlap_found_a_promising_separator"
        authorized_next_work = COMPONENT_NEXT_WORK_REDESIGN
    else:
        status = SOURCE_BLOCKED_STATUS
        passed = False
        primary_gap = _blocked_primary_gap(source)
        authorized_next_work = "fix_component_overlap_source_before_limit_record"

    final = {
        "status": status,
        "passed": passed,
        "primary_gap": primary_gap,
        "authorized_next_work": authorized_next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_relaxed_strict_atom_observability_limit_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_limit_diagnosis": True,
            "selection_effect": False,
            "math_boundary": (
                "This synthesis records a negative offline result from fixed "
                "current-tick relaxed strict atom coefficients. The closed-loop "
                "outcomes in the source artifact define only offline beneficial "
                "and harmful groups; no future outcome value is made available "
                "to online scoring. The rejected atom values would still be "
                "finite nonnegative coefficients a_k in score_k(w)=a_k^T w, "
                "so CAMP's simplex/CVaR/L2 master remains convex. The result "
                "does not construct a DP-side classical Benders master, "
                "subproblem, dual, or valid cut."
            ),
        },
        "source_component_overlap_gate": source,
        "evidence": evidence,
        "rejected_routes": {
            "threshold_tuning_current_relaxed_strict_atoms": source_ready,
            "component_recombination_current_relaxed_strict_atoms": source_ready,
            "immediate_camp_retraining_from_current_atoms": source_ready,
            "online_selector_promotion": True,
            "new_replay_from_this_gate": True,
            "full36_from_this_gate": True,
            "formal_seeds_from_this_gate": True,
            "classic_benders_claim": True,
        },
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision")
    if not isinstance(decision, dict):
        return {
            "status": None,
            "passed": False,
            "primary_gap": "component_overlap_final_decision_missing",
            "authorized_next_work": None,
        }
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": decision.get("authorized_next_work"),
    }


def _evidence(report: dict[str, Any]) -> dict[str, Any]:
    group_counts = report.get("group_counts") or {}
    diagnosis = report.get("diagnosis") or {}
    best_component = report.get("best_component_screen") or {}
    relaxation = report.get("relaxation") or {}
    records = report.get("records") or {}
    return {
        "total_records": records.get("total_records"),
        "candidate_rows": records.get("candidate_rows"),
        "formal_seed_records": records.get("formal_seed_records"),
        "blocked_beneficial": group_counts.get("blocked_beneficial"),
        "newly_admitted_harmful": group_counts.get("newly_admitted_harmful"),
        "target_retain_rate": relaxation.get("target_retain_rate"),
        "relaxed_threshold": relaxation.get("threshold"),
        "best_component_descriptor": best_component.get("descriptor"),
        "best_component_good_retain_rate": best_component.get("good_retain_rate"),
        "best_component_harmful_block_rate": best_component.get("harmful_block_rate"),
        "best_component_allowed_harmful_rate": best_component.get(
            "allowed_harmful_rate"
        ),
        "promising_component_separator_found": diagnosis.get(
            "promising_component_separator_found"
        ),
    }


def _blocked_primary_gap(source: dict[str, Any]) -> str:
    if source["status"] != COMPONENT_READY_STATUS:
        return "component_overlap_gate_not_ready"
    if not source["passed"]:
        return "component_overlap_gate_failed"
    if source["authorized_next_work"] != COMPONENT_NEXT_WORK_LIMITATION:
        return "component_overlap_does_not_authorize_limit_record"
    return "component_overlap_source_not_ready"


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Relaxed Strict Atom Observability Limit",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Gate",
        "",
        "```json",
        json.dumps(report["source_component_overlap_gate"], indent=2, sort_keys=True),
        "```",
        "",
        "## Evidence",
        "",
        "```json",
        json.dumps(report["evidence"], indent=2, sort_keys=True),
        "```",
        "",
        "## Rejected Routes",
        "",
        "```json",
        json.dumps(report["rejected_routes"], indent=2, sort_keys=True),
        "```",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
