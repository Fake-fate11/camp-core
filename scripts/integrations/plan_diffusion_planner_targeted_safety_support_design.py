#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.integrations.analyze_diffusion_planner_alternative_safety_source_materiality import (
    READY_STATUS as SOURCE_READY_STATUS,
    TARGETED_SUPPORT_NEXT_WORK as SOURCE_READY_NEXT_WORK,
)


READY_STATUS = "targeted_safety_support_scenario_or_source_design_ready"
REJECT_STATUS = "targeted_safety_support_scenario_or_source_design_rejected"
AUTHORIZED_NEXT_WORK = "targeted_safety_support_tiny_runbook_preflight_only"

FORMAL_SEEDS = {11, 12, 13}
BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_replay_authorized",
    "closed_loop_smoke_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only targeted safety support gate after existing smoke "
            "safety sources are material but not actionable. It does not run DP, "
            "train CAMP, or change online selection."
        )
    )
    parser.add_argument("--materiality_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        materiality_report=_load_json(args.materiality_json),
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
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def build_report(
    *,
    materiality_report: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(materiality_report)
    design = _design_contract(source)
    checks = [
        *_source_checks(source),
        *_design_checks(design),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_targeted_safety_support_design_v1",
            "label": label,
            "role": (
                "design-only predeclaration of targeted nonformal safety support "
                "and candidate-level no-leak source families"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "selection_effect": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box finite-candidate generator. This "
                "gate only predeclares where to seek safety intervention support "
                "and which current-tick candidate source families would be legal "
                "if later evidence shows opportunity. Each proposed atom source "
                "is a fixed finite candidate coefficient before CAMP scoring and "
                "is nonnegative by construction through a hinge or gap-to-best "
                "definition. If later atomized, score_k(w)=a_k^T w remains affine "
                "and the simplex/CVaR/L2 robust master remains convex. Outcome "
                "labels may be collected later only for offline proof gates, never "
                "as online features. No DP-side classical Benders decomposition, "
                "dual, or valid cut is introduced."
            ),
        },
        "source_materiality": source,
        "design_contract": design,
        "design_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, design),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    summary = _dict(report.get("materiality_summary"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "has_actionable_existing_safety_source": bool(
            final.get("has_actionable_existing_safety_source")
        ),
        "has_material_safety_source": bool(final.get("has_material_safety_source")),
        "actionable_existing_safety_sources": _string_list(
            final.get("actionable_existing_safety_sources")
        ),
        "material_but_current_selection_already_best": _string_list(
            final.get("material_but_current_selection_already_best")
        ),
        "by_source": list(summary.get("by_source") or []),
        "blocked_action_conflicts": conflicts,
    }


def _design_contract(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "TargetedSafetySupportScenarioOrSourceDesign_v1",
        "why_existing_source_is_not_enough": [
            "temporal_consistency_changed_candidates_but_did_not_improve_safety_proxy",
            "existing_red_sources_have_material_range_but_current_selection_is_already_best",
            "existing_clearance_sources_have_no_nonzero_range_in_current_smoke",
        ],
        "tiny_support_discovery": {
            "purpose": (
                "Find nonformal current-tick candidate sets where DP Top-1 or "
                "current CAMP selection is not already best under a legal safety "
                "proxy, before designing or training any selector."
            ),
            "allowed_execution_after_next_gate": "runbook_preflight_only",
            "default_off": True,
            "paired": True,
            "nonformal_only": True,
            "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
            "variants": ["static"],
            "max_steps_per_run": 10,
            "rows": [
                {
                    "name": "sample_tl_turn_seed1_npc4_tlon",
                    "route_name": "sample_map_tl_route_59_to_86",
                    "route_asset": "/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
                    "seed": 1,
                    "max_npcs": 4,
                    "spawn_probability": 0.3,
                    "traffic_lights": True,
                    "buckets": [
                        "traffic_light",
                        "red_light_turn",
                        "sharp_turn",
                        "npc_interaction",
                    ],
                    "support_hypothesis": (
                        "red-turn with NPC pressure may expose candidate branches "
                        "where progress and red-light safety conflict."
                    ),
                },
                {
                    "name": "sample_tl_turn_seed1_npc4_tloff",
                    "route_name": "sample_map_tl_route_59_to_86",
                    "route_asset": "/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
                    "seed": 1,
                    "max_npcs": 4,
                    "spawn_probability": 0.3,
                    "traffic_lights": False,
                    "buckets": ["sharp_turn", "npc_interaction"],
                    "support_hypothesis": (
                        "same route without active traffic lights is the paired "
                        "guard for red-light-specific support."
                    ),
                },
                {
                    "name": "nishi_lanechange_seed3_npc8_tloff",
                    "route_name": "nishishinjuku_lane_change",
                    "route_asset": "/root/autodl-tmp/camp_dp_assets/nishishinjuku_lane_change_route_7_via_8_to_1.pkl",
                    "seed": 3,
                    "max_npcs": 8,
                    "spawn_probability": 0.3,
                    "traffic_lights": False,
                    "buckets": [
                        "lane_change_or_merge",
                        "npc_interaction",
                        "dense_scene",
                    ],
                    "support_hypothesis": (
                        "dense lane-change support previously showed safety-cost "
                        "pressure and can test obstacle/lane interaction sources."
                    ),
                },
                {
                    "name": "nishi_lanechange_seed3_npc8_tlon",
                    "route_name": "nishishinjuku_lane_change",
                    "route_asset": "/root/autodl-tmp/camp_dp_assets/nishishinjuku_lane_change_route_7_via_8_to_1.pkl",
                    "seed": 3,
                    "max_npcs": 8,
                    "spawn_probability": 0.3,
                    "traffic_lights": True,
                    "buckets": [
                        "traffic_light",
                        "lane_change_or_merge",
                        "npc_interaction",
                        "dense_scene",
                    ],
                    "support_hypothesis": (
                        "traffic-light-on paired dense lane-change guard checks "
                        "whether candidate support is robust to signal context."
                    ),
                },
                {
                    "name": "sample_normal_seed1_npc0_tloff",
                    "route_name": "sample_map_route_2_to_104",
                    "route_asset": "/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl",
                    "seed": 1,
                    "max_npcs": 0,
                    "spawn_probability": 0.0,
                    "traffic_lights": False,
                    "buckets": ["normal"],
                    "support_hypothesis": (
                        "normal guard run prevents a safety-source search from "
                        "silently becoming a special-case intervention only."
                    ),
                },
            ],
            "discovery_success_criteria": [
                "no formal seeds",
                "DP commit remains fixed",
                "default-off logs prove selection_effect=false",
                "at least one target row has selected_not_best_records > 0 for a legal current-tick safety source",
                "normal guard has no new hard-safety regression signal",
                "no online selector, retraining, Full36, or formal evaluation is authorized",
            ],
        },
        "candidate_source_families": [
            {
                "name": "red_light_gap_to_best_current_tick",
                "definition": (
                    "a_k = max(red_cost_k - min_j red_cost_j, 0), evaluated "
                    "separately for h30 union red, h80 full red, and red stopping margin"
                ),
                "source_fields": [
                    "candidate_horizon_union_planned_red_light_cost",
                    "candidate_full_horizon_planned_red_light_cost",
                    "candidate_red_stopping_margin_cost",
                ],
                "nonnegative": True,
                "fixed_before_scoring": True,
                "requires_new_support": True,
            },
            {
                "name": "clearance_violation_gap_to_best_current_tick",
                "definition": (
                    "a_k = max(clearance_violation_k - min_j clearance_violation_j, 0), "
                    "evaluated for soft-clearance and near-miss violation costs"
                ),
                "source_fields": [
                    "candidate_obstacle_clearance.soft_clearance_violation_cost",
                    "candidate_obstacle_clearance.near_miss_violation_cost",
                ],
                "nonnegative": True,
                "fixed_before_scoring": True,
                "requires_new_support": True,
            },
            {
                "name": "joint_safety_gap_current_tick",
                "definition": (
                    "a_k = max(max(red_gap_k, clearance_gap_k) - min_j max(red_gap_j, clearance_gap_j), 0)"
                ),
                "source_fields": [
                    "red_light_gap_to_best_current_tick",
                    "clearance_violation_gap_to_best_current_tick",
                ],
                "nonnegative": True,
                "fixed_before_scoring": True,
                "requires_new_support": True,
            },
        ],
        "blocked_routes": [
            "temporal_consistency_as_safety_source",
            "direct_existing_red_atom_from_current_smoke",
            "direct_existing_clearance_atom_from_current_smoke",
            "outcome_or_safetycost_as_online_feature",
        ],
        "source_materiality_snapshot": {
            "has_material_safety_source": source["has_material_safety_source"],
            "has_actionable_existing_safety_source": source[
                "has_actionable_existing_safety_source"
            ],
            "material_but_current_selection_already_best": source[
                "material_but_current_selection_already_best"
            ],
            "actionable_existing_safety_sources": source[
                "actionable_existing_safety_sources"
            ],
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_targeted_support_design",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_has_no_actionable_existing_safety_source",
            source["has_actionable_existing_safety_source"],
            False,
        ),
        _check_equal(
            "source_has_material_safety_source",
            source["has_material_safety_source"],
            True,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _design_checks(design: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(design["tiny_support_discovery"]["rows"])
    seeds = [int(row["seed"]) for row in rows]
    formal = sorted(seed for seed in seeds if seed in FORMAL_SEEDS)
    source_families = list(design["candidate_source_families"])
    return [
        _check_equal("tiny_support_has_rows", bool(rows), True),
        _check_equal("tiny_support_uses_no_formal_seeds", formal, []),
        _check_equal(
            "tiny_support_has_normal_guard",
            any("normal" in row["buckets"] for row in rows),
            True,
        ),
        _check_equal(
            "tiny_support_has_target_bucket",
            any(
                any(
                    bucket in row["buckets"]
                    for bucket in (
                        "traffic_light",
                        "red_light_turn",
                        "npc_interaction",
                        "dense_scene",
                        "lane_change_or_merge",
                    )
                )
                for row in rows
            ),
            True,
        ),
        _check_equal(
            "source_families_nonempty",
            bool(source_families),
            True,
        ),
        _check_equal(
            "source_families_all_nonnegative",
            all(bool(item.get("nonnegative")) for item in source_families),
            True,
        ),
        _check_equal(
            "source_families_fixed_before_scoring",
            all(bool(item.get("fixed_before_scoring")) for item in source_families),
            True,
        ),
        _check_equal(
            "source_families_require_new_support",
            all(bool(item.get("requires_new_support")) for item in source_families),
            True,
        ),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    design: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "recommended_first_action": (
            "build_targeted_safety_support_tiny_runbook_preflight"
            if passed
            else "repair_targeted_safety_support_design_source_or_contract"
        ),
        "tiny_support_row_count": len(design["tiny_support_discovery"]["rows"]),
        "candidate_source_family_count": len(design["candidate_source_families"]),
        "existing_source_atomization_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Create a runbook preflight for the tiny targeted support discovery. "
            "It may plan, but not execute, default-off nonformal paired runs."
            if passed
            else "Reject this design until source and contract checks pass."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    design = report["design_contract"]
    lines = [
        "# Targeted Safety Support Design",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Tiny support rows: `{decision['tiny_support_row_count']}`",
        f"- Candidate source families: `{decision['candidate_source_family_count']}`",
        "",
        "## Tiny Support Discovery Rows",
        "",
        "| Row | Route | Seed | NPCs | TL | Buckets |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in design["tiny_support_discovery"]["rows"]:
        lines.append(
            f"| `{row['name']}` | `{row['route_name']}` | `{row['seed']}` | "
            f"`{row['max_npcs']}` | `{row['traffic_lights']}` | "
            f"`{', '.join(row['buckets'])}` |"
        )
    lines.extend(["", "## Candidate Source Families", ""])
    lines.extend(["| Source | Definition | Fields |", "| --- | --- | --- |"])
    for item in design["candidate_source_families"]:
        lines.append(
            f"| `{item['name']}` | `{item['definition']}` | "
            f"`{', '.join(item['source_fields'])}` |"
        )
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    lines.extend(["## Checks", "", "| Check | Passed | Observed | Expected |", "| --- | ---: | --- | --- |"])
    for check in report["design_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
